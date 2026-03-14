from dataclasses import dataclass, field
from typing import Optional
import yaml
from github import Github, GithubException
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG = {
    "version": 1,
    "review": {
        "enabled": True,
        "languages": ["python", "typescript", "go", "javascript", "java", "rust"],
        "max_files_per_pr": 20,
        "ignore_paths": ["**/*.test.ts", "**/*.test.js", "migrations/**", "**/node_modules/**"],
    },
    "security": {
        "enabled": True,
        "block_merge_on": ["critical"],
        "scan_dependencies": True,
    },
    "notifications": {
        "post_summary_comment": True,
        "summary_position": "top",
    },
}


@dataclass
class ReviewConfig:
    enabled: bool = True
    languages: list = field(default_factory=lambda: ["python", "typescript", "go"])
    max_files_per_pr: int = 20
    ignore_paths: list = field(default_factory=list)


@dataclass
class SecurityConfig:
    enabled: bool = True
    block_merge_on: list = field(default_factory=lambda: ["critical"])
    scan_dependencies: bool = True


@dataclass
class NotificationsConfig:
    post_summary_comment: bool = True
    summary_position: str = "top"


@dataclass
class RepoConfig:
    version: int = 1
    review: ReviewConfig = field(default_factory=ReviewConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)


def load_repo_config(repo, sha: str) -> RepoConfig:
    """Fetch and parse .devsheriff.yml from the repo at the given commit SHA."""
    try:
        content = repo.get_contents(".devsheriff.yml", ref=sha)
        raw = content.decoded_content.decode("utf-8")
        data = yaml.safe_load(raw)
        return _parse_config(data)
    except GithubException:
        logger.info(
            "No .devsheriff.yml found, using defaults",
            extra={"repo": repo.full_name, "sha": sha},
        )
        return _parse_config(DEFAULT_CONFIG)
    except Exception as e:
        logger.warning(
            "Failed to parse .devsheriff.yml, using defaults",
            extra={"error": str(e)},
        )
        return _parse_config(DEFAULT_CONFIG)


def _parse_config(data: dict) -> RepoConfig:
    review_data = data.get("review", {})
    security_data = data.get("security", {})
    notifications_data = data.get("notifications", {})

    review = ReviewConfig(
        enabled=review_data.get("enabled", True),
        languages=review_data.get("languages", ["python", "typescript", "go"]),
        max_files_per_pr=review_data.get("max_files_per_pr", 20),
        ignore_paths=review_data.get("ignore_paths", []),
    )

    security = SecurityConfig(
        enabled=security_data.get("enabled", True),
        block_merge_on=security_data.get("block_merge_on", ["critical"]),
        scan_dependencies=security_data.get("scan_dependencies", True),
    )

    notifications = NotificationsConfig(
        post_summary_comment=notifications_data.get("post_summary_comment", True),
        summary_position=notifications_data.get("summary_position", "top"),
    )

    return RepoConfig(
        version=data.get("version", 1),
        review=review,
        security=security,
        notifications=notifications,
    )
