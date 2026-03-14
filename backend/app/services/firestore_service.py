import uuid
from datetime import datetime, timezone

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_db():
    from google.cloud import firestore
    return firestore.AsyncClient(project=settings.FIRESTORE_PROJECT_ID)


async def save_review(payload: dict, findings: list[dict]) -> str:
    """Persist a PR review and its findings to Firestore."""
    review_id = str(uuid.uuid4())
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    review_doc = {
        "review_id": review_id,
        "repo": repo.get("full_name", ""),
        "repo_id": repo.get("full_name", "").replace("/", "_"),
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title", ""),
        "pr_url": pr.get("html_url", ""),
        "sha": pr.get("head", {}).get("sha", ""),
        "author": payload.get("sender", {}).get("login", ""),
        "status": "completed",
        "finding_count": len(findings),
        "critical_count": sum(1 for f in findings if f.get("severity") == "critical"),
        "high_count": sum(1 for f in findings if f.get("severity") == "high"),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        db = _get_db()
        review_ref = db.collection("reviews").document(review_id)
        await review_ref.set(review_doc)

        findings_ref = review_ref.collection("findings")
        for i, finding in enumerate(findings):
            await findings_ref.document(str(i)).set(finding)

        # Update repo aggregate stats
        repo_id = review_doc["repo_id"]
        repo_ref = db.collection("repos").document(repo_id)
        from google.cloud.firestore import AsyncClient, Increment
        await repo_ref.set(
            {
                "repo": review_doc["repo"],
                "total_reviews": Increment(1),
                "total_findings": Increment(len(findings)),
                "critical_findings": Increment(review_doc["critical_count"]),
                "last_reviewed_at": datetime.now(timezone.utc),
            },
            merge=True,
        )

        logger.info(
            "Review saved to Firestore",
            extra={"review_id": review_id, "finding_count": len(findings)},
        )
    except Exception as e:
        logger.error("Failed to save review to Firestore", extra={"error": str(e)})

    return review_id


async def get_recent_reviews(limit: int = 50) -> list[dict]:
    """Fetch the most recent reviews."""
    try:
        db = _get_db()
        from google.cloud.firestore import Query
        query = (
            db.collection("reviews")
            .order_by("created_at", direction=Query.DESCENDING)
            .limit(limit)
        )
        docs = await query.get()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        logger.error("Failed to fetch reviews", extra={"error": str(e)})
        return []


async def get_review_with_findings(review_id: str) -> dict | None:
    """Fetch a single review and all its findings."""
    try:
        db = _get_db()
        review_ref = db.collection("reviews").document(review_id)
        review_doc = await review_ref.get()

        if not review_doc.exists:
            return None

        findings_docs = await review_ref.collection("findings").get()
        findings = [doc.to_dict() for doc in findings_docs]

        return {
            "id": review_doc.id,
            **review_doc.to_dict(),
            "findings": findings,
        }
    except Exception as e:
        logger.error(
            "Failed to fetch review", extra={"review_id": review_id, "error": str(e)}
        )
        return None


async def get_repo_stats(repo_id: str) -> dict:
    """Fetch aggregate stats for a repository."""
    try:
        db = _get_db()
        doc = await db.collection("repos").document(repo_id).get()
        if doc.exists:
            return {"repo_id": repo_id, **doc.to_dict()}
        return {"repo_id": repo_id, "total_reviews": 0, "total_findings": 0}
    except Exception as e:
        logger.error("Failed to fetch repo stats", extra={"error": str(e)})
        return {"repo_id": repo_id, "total_reviews": 0, "total_findings": 0}
