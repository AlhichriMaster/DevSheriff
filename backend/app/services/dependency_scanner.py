import json
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def scan_dependencies(files) -> list[dict]:
    """Extract dependency files from the PR and run vulnerability scans."""
    findings: list[dict] = []

    for file in files:
        filename = file.filename.lower()

        if filename in ("requirements.txt", "requirements-dev.txt"):
            findings.extend(await scan_python_deps(file))
        elif filename == "package.json":
            findings.extend(await scan_npm_deps(file))

    return findings


async def scan_python_deps(file) -> list[dict]:
    """Run pip-audit against a requirements.txt file from the PR."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(file.raw_url, timeout=15.0)
            content = r.text
    except Exception as e:
        logger.error("Failed to fetch requirements file", extra={"error": str(e)})
        return []

    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = Path(tmpdir) / "requirements.txt"
        req_file.write_text(content)

        result = subprocess.run(
            ["pip-audit", "-r", str(req_file), "--format", "json", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        findings: list[dict] = []

        try:
            data = json.loads(result.stdout)
            for dep in data.get("dependencies", []):
                vulns = dep.get("vulns", [])
                if not vulns:
                    continue

                cve_ids = [v["id"] for v in vulns]

                # Enrich with OSV if possible
                from app.services.osv_service import lookup_osv
                osv_vulns = await lookup_osv(dep["name"], dep["version"], "PyPI")
                if osv_vulns:
                    cve_ids.extend(v["id"] for v in osv_vulns)

                findings.append({
                    "file": file.filename,
                    "line": 1,
                    "severity": "high",
                    "category": "security",
                    "title": f"Vulnerable dependency: {dep['name']}=={dep['version']}",
                    "body": (
                        f"Known vulnerabilities found in {dep['name']} version {dep['version']}. "
                        f"CVEs: {', '.join(cve_ids[:5])}"
                    ),
                    "suggestion": f"Upgrade {dep['name']} to a non-vulnerable version. Check https://pypi.org/project/{dep['name']}/ for the latest safe release.",
                    "diff_position": 1,
                    "cve_ids": cve_ids[:5],
                })

        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse pip-audit output", extra={"error": str(e)})

        return findings


async def scan_npm_deps(file) -> list[dict]:
    """Scan package.json for vulnerable npm dependencies via OSV."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(file.raw_url, timeout=15.0)
            pkg_data = r.json()
    except Exception as e:
        logger.error("Failed to fetch package.json", extra={"error": str(e)})
        return []

    findings: list[dict] = []
    all_deps = {
        **pkg_data.get("dependencies", {}),
        **pkg_data.get("devDependencies", {}),
    }

    from app.services.osv_service import lookup_osv

    for pkg_name, version_spec in all_deps.items():
        # Strip common version prefixes (^, ~, >=)
        version = version_spec.lstrip("^~>=<")
        vulns = await lookup_osv(pkg_name, version, "npm")

        if vulns:
            cve_ids = [v["id"] for v in vulns]
            findings.append({
                "file": file.filename,
                "line": 1,
                "severity": "high",
                "category": "security",
                "title": f"Vulnerable npm package: {pkg_name}@{version}",
                "body": f"Known vulnerabilities: {', '.join(cve_ids[:3])}",
                "suggestion": f"Run `npm audit fix` or upgrade {pkg_name} to a patched version.",
                "diff_position": 1,
                "cve_ids": cve_ids[:5],
            })

    return findings
