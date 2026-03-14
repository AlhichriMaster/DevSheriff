from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_secrets, settings
from app.middleware.signature_middleware import verify_signature
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_secrets()
    logger.info("DevSheriff backend started", extra={"environment": settings.ENVIRONMENT})
    yield
    logger.info("DevSheriff backend shutting down")


app = FastAPI(title="DevSheriff", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    print(f"[WEBHOOK] event_type={event_type!r} action={payload.get('action')!r}", flush=True)
    logger.info(
        "Webhook received",
        extra={"event_type": event_type, "action": payload.get("action")},
    )

    if event_type == "pull_request":
        action = payload.get("action")
        logger.info(f"PR action: {action}")
        if action in ("opened", "synchronize", "reopened"):
            from app.services.github_service import handle_pull_request_event

            async def _run_review(p=payload):
                try:
                    await handle_pull_request_event(p)
                except Exception as exc:
                    import traceback
                    print(f"[REVIEW ERROR] {exc}\n{traceback.format_exc()}", flush=True)

            asyncio.create_task(_run_review())

    elif event_type == "check_suite":
        # Fallback: check_suite fires on every push; find and review the associated PR
        action = payload.get("action")
        if action == "requested":
            from app.services.github_service import handle_check_suite_event

            async def _run_check_review(p=payload):
                try:
                    await handle_check_suite_event(p)
                except Exception as exc:
                    import traceback
                    print(f"[CHECK_SUITE ERROR] {exc}\n{traceback.format_exc()}", flush=True)

            asyncio.create_task(_run_check_review())

    return {"status": "accepted"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "devsheriff-backend"}


@app.get("/api/reviews")
async def list_reviews(limit: int = 50):
    from app.services.firestore_service import get_recent_reviews
    reviews = await get_recent_reviews(limit=limit)
    return {"reviews": reviews}


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: str):
    from app.services.firestore_service import get_review_with_findings
    review = await get_review_with_findings(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.get("/api/repos/{repo_full_name}/stats")
async def get_repo_stats(repo_full_name: str):
    from app.services.firestore_service import get_repo_stats
    repo_id = repo_full_name.replace("/", "_")
    stats = await get_repo_stats(repo_id)
    return stats
