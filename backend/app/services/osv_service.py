import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)

OSV_API_URL = "https://api.osv.dev/v1/query"

ECOSYSTEM_MAP = {
    "requirements.txt": "PyPI",
    "requirements-dev.txt": "PyPI",
    "pyproject.toml": "PyPI",
    "package.json": "npm",
    "go.mod": "Go",
    "Cargo.toml": "crates.io",
}


async def lookup_osv(package_name: str, version: str, ecosystem: str) -> list[dict]:
    """Query OSV for known vulnerabilities in a package version."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                OSV_API_URL,
                json={
                    "version": version,
                    "package": {
                        "name": package_name,
                        "ecosystem": ecosystem,
                    },
                },
                timeout=10.0,
            )

            if r.status_code != 200:
                return []

            vulns = r.json().get("vulns", [])
            return [
                {
                    "id": v.get("id", ""),
                    "summary": v.get("summary", "")[:200],
                    "severity": v.get("database_specific", {}).get("severity", "UNKNOWN"),
                }
                for v in vulns[:3]
            ]

    except Exception as e:
        logger.error(
            "OSV lookup failed",
            extra={"package": package_name, "version": version, "error": str(e)},
        )
        return []
