import hmac
import hashlib

from app.config import settings


def verify_signature(body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature.

    Uses hmac.compare_digest to prevent timing attacks.
    """
    if not signature_header.startswith("sha256="):
        return False

    if not settings.GITHUB_WEBHOOK_SECRET:
        return False

    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)
