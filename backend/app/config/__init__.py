import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY: str = ""
    GITHUB_PRIVATE_KEY_PATH: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    NVD_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    FIRESTORE_PROJECT_ID: str = "devsheriff-dev"
    GCP_PROJECT_ID: str = "devsheriff-prod"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


async def load_secrets():
    """Load secrets from Google Secret Manager in production, or from env/.env in development."""
    if settings.ENVIRONMENT == "production":
        await _load_from_secret_manager()
    else:
        await _load_from_env()


async def _load_from_secret_manager():
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    project = settings.GCP_PROJECT_ID

    secret_map = {
        "devsheriff-github-private-key": "GITHUB_PRIVATE_KEY",
        "devsheriff-github-webhook-secret": "GITHUB_WEBHOOK_SECRET",
        "devsheriff-anthropic-api-key": "ANTHROPIC_API_KEY",
        "devsheriff-nvd-api-key": "NVD_API_KEY",
    }

    for secret_name, attr in secret_map.items():
        name = f"projects/{project}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("utf-8")
        setattr(settings, attr, value)


async def _load_from_env():
    """In development, optionally load private key from file path."""
    if settings.GITHUB_PRIVATE_KEY_PATH and not settings.GITHUB_PRIVATE_KEY:
        key_path = Path(settings.GITHUB_PRIVATE_KEY_PATH)
        if key_path.exists():
            settings.GITHUB_PRIVATE_KEY = key_path.read_text()
