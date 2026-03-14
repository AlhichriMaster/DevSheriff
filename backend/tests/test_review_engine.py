import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.review_engine import (
    _parse_json_response,
    detect_language,
    should_skip_file,
)
from app.config.repo_config import RepoConfig, ReviewConfig, SecurityConfig


def test_detect_language():
    assert detect_language("auth.py") == "Python"
    assert detect_language("app.ts") == "TypeScript"
    assert detect_language("main.go") == "Go"
    assert detect_language("lib.rs") == "Rust"
    assert detect_language("unknown.xyz") == "Unknown"


def test_parse_json_response_valid():
    text = '[{"file": "auth.py", "line": 1, "severity": "critical", "title": "SQL Injection"}]'
    result = _parse_json_response(text)
    assert len(result) == 1
    assert result[0]["severity"] == "critical"


def test_parse_json_response_with_preamble():
    text = 'Here are the findings:\n[{"file": "auth.py", "line": 1, "severity": "high", "title": "XSS"}]'
    result = _parse_json_response(text)
    assert len(result) == 1
    assert result[0]["severity"] == "high"


def test_parse_json_response_empty_array():
    result = _parse_json_response("[]")
    assert result == []


def test_parse_json_response_invalid():
    result = _parse_json_response("Not valid JSON")
    assert result == []


def test_should_skip_binary_files():
    config = RepoConfig()
    mock_file = MagicMock()
    mock_file.filename = "image.png"
    mock_file.patch = None
    assert should_skip_file(mock_file, config) is True


def test_should_skip_no_patch():
    config = RepoConfig()
    mock_file = MagicMock()
    mock_file.filename = "main.py"
    mock_file.patch = None
    assert should_skip_file(mock_file, config) is True


def test_should_skip_ignored_path():
    config = RepoConfig(review=ReviewConfig(ignore_paths=["**/*.test.ts"]))
    mock_file = MagicMock()
    mock_file.filename = "src/auth.test.ts"
    mock_file.patch = "@@ -0,0 +1 @@\n+test"
    assert should_skip_file(mock_file, config) is True


def test_should_not_skip_normal_file():
    config = RepoConfig()
    mock_file = MagicMock()
    mock_file.filename = "src/auth.py"
    mock_file.patch = "@@ -0,0 +1 @@\n+code"
    assert should_skip_file(mock_file, config) is False


@pytest.mark.asyncio
async def test_sql_injection_detected():
    mock_file = MagicMock()
    mock_file.filename = "auth.py"
    mock_file.patch = '+    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps([{
        "file": "auth.py",
        "line": 1,
        "severity": "critical",
        "category": "security",
        "title": "SQL Injection via f-string interpolation",
        "body": "Direct interpolation allows attacker to manipulate query.",
        "suggestion": "Use parameterized queries.",
        "owasp_category": "A03:2021 – Injection",
    }])

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.services.review_engine.anthropic.AsyncAnthropic", return_value=mock_client):
        from app.services.review_engine import run_review
        config = RepoConfig()
        findings = await run_review([mock_file], config)

    assert len(findings) >= 1
    sql_finding = next((f for f in findings if "sql" in f["title"].lower()), None)
    assert sql_finding is not None
    assert sql_finding["severity"] == "critical"
