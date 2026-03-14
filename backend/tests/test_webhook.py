import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)

WEBHOOK_SECRET = "test-webhook-secret-32chars-long!!"


def make_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def set_test_config(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GITHUB_APP_ID", "123456")
    monkeypatch.setattr(settings, "GITHUB_PRIVATE_KEY", "")


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_rejects_missing_signature():
    payload = json.dumps({"action": "opened"}).encode()
    response = client.post(
        "/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "X-GitHub-Event": "pull_request"},
    )
    assert response.status_code == 401


def test_webhook_rejects_invalid_signature():
    payload = json.dumps({"action": "opened"}).encode()
    response = client.post(
        "/webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalidsignature",
        },
    )
    assert response.status_code == 401


def test_webhook_accepts_valid_signature():
    payload_data = {"action": "ping"}
    payload = json.dumps(payload_data).encode()
    sig = make_signature(payload, WEBHOOK_SECRET)

    response = client.post(
        "/webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_webhook_ignores_non_pr_events():
    payload_data = {"action": "created", "issue": {"number": 1}}
    payload = json.dumps(payload_data).encode()
    sig = make_signature(payload, WEBHOOK_SECRET)

    response = client.post(
        "/webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": sig,
        },
    )
    assert response.status_code == 200
