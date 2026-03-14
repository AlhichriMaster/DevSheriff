import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


async def lookup_cve(package_name: str, version: str) -> list[dict]:
    """Fetch CVE records from NVD for a specific package."""
    if not settings.NVD_API_KEY:
        return []

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                NVD_API_URL,
                params={
                    "keywordSearch": f"{package_name} {version}",
                    "cvssV3Severity": "HIGH",
                },
                headers={"apiKey": settings.NVD_API_KEY},
                timeout=10.0,
            )

            if r.status_code != 200:
                logger.warning(
                    "NVD API returned non-200",
                    extra={"status": r.status_code, "package": package_name},
                )
                return []

            vulnerabilities = r.json().get("vulnerabilities", [])
            return [
                {
                    "cve_id": v["cve"]["id"],
                    "description": v["cve"]["descriptions"][0]["value"][:200],
                    "cvss_score": (
                        v["cve"]
                        .get("metrics", {})
                        .get("cvssMetricV31", [{}])[0]
                        .get("cvssData", {})
                        .get("baseScore", "N/A")
                    ),
                }
                for v in vulnerabilities[:3]  # Cap at 3 CVEs per package
            ]

    except Exception as e:
        logger.error(
            "NVD lookup failed",
            extra={"package": package_name, "version": version, "error": str(e)},
        )
        return []
