import time

import httpx
import jwt

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_jwt() -> str:
    """Creates a short-lived JWT signed with the App's RSA private key."""
    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued at (60s in the past to account for clock drift)
        "exp": now + 600,  # expires in 10 minutes
        "iss": settings.GITHUB_APP_ID,
    }
    return jwt.encode(payload, settings.GITHUB_PRIVATE_KEY, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Exchanges a JWT for a repo-scoped installation access token."""
    jwt_token = create_jwt()

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )
        r.raise_for_status()
        token = r.json()["token"]
        logger.info(
            "Installation token obtained",
            extra={"installation_id": installation_id},
        )
        return token
