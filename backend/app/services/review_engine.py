import asyncio
import json
import re

import anthropic

from app.config import settings
from app.services.diff_parser import parse_diff_with_positions
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEMANTIC_SYSTEM_PROMPT = """You are DevSheriff, an expert code reviewer. You will be given a unified diff of code changes.
Your job is to identify:
- Logic errors and bugs
- Performance anti-patterns (N+1 queries, unnecessary recomputation, blocking I/O)
- Missing error handling and edge cases
- Poor naming and readability issues
- Maintainability concerns (functions too long, missing docstrings, magic numbers)

Rules:
- Only comment on ADDED lines (lines starting with '+' in the diff)
- Be specific and actionable — always include a concrete suggestion
- Skip purely stylistic issues that a linter would catch (formatting, quotes)
- Return ONLY valid JSON array. No preamble, no markdown fences.
- If there are no issues, return an empty array: []

Output schema: array of { file, line, severity, category, title, body, suggestion }
Severity levels: high | medium | low | info
Category: logic | performance | maintainability"""

SECURITY_SYSTEM_PROMPT = """You are DevSheriff Security, an expert application security auditor. You will be given a unified diff.
Your job is to identify:
- Injection vulnerabilities (SQL, command, LDAP, XPath)
- Hardcoded secrets, API keys, passwords
- Insecure cryptography (MD5, SHA1 for passwords, ECB mode)
- Path traversal and file inclusion vulnerabilities
- Insecure deserialization
- Missing authentication or authorization checks
- SSRF, open redirects, XSS vectors
- Regex denial of service (ReDoS)

Rules:
- Only comment on ADDED lines (lines starting with '+' in the diff)
- For each finding, reference the specific OWASP Top 10 category if applicable
- Return ONLY valid JSON array. No preamble, no markdown fences.
- If there are no security issues, return an empty array: []

Output schema: array of { file, line, severity, category, title, body, suggestion, owasp_category? }
Severity levels: critical | high | medium | low
Category: security"""

LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".tf": "Terraform",
    ".sh": "Shell",
    ".sql": "SQL",
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".pdf", ".zip", ".tar", ".gz", ".lock",
}


def detect_language(filename: str) -> str:
    import os
    ext = os.path.splitext(filename)[1].lower()
    return LANGUAGE_MAP.get(ext, "Unknown")


def should_skip_file(file, config) -> bool:
    import fnmatch
    import os

    ext = os.path.splitext(file.filename)[1].lower()
    if ext in IGNORE_EXTENSIONS:
        return True

    for pattern in config.review.ignore_paths:
        if fnmatch.fnmatch(file.filename, pattern):
            return True

    if not file.patch:
        return True

    return False


async def run_review(files, config) -> list[dict]:
    """Run the full AI review pipeline across all eligible files."""
    all_findings: list[dict] = []
    eligible_files = [f for f in files if not should_skip_file(f, config)]

    if len(eligible_files) > config.review.max_files_per_pr:
        logger.info(
            "Truncating files for review",
            extra={
                "total": len(eligible_files),
                "max": config.review.max_files_per_pr,
            },
        )
        eligible_files = eligible_files[: config.review.max_files_per_pr]

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    tasks = []
    for file in eligible_files:
        positions = parse_diff_with_positions(file.patch)
        if config.review.enabled:
            tasks.append(_review_file(client, file, positions, SEMANTIC_SYSTEM_PROMPT, "semantic"))
        if config.security.enabled:
            tasks.append(_review_file(client, file, positions, SECURITY_SYSTEM_PROMPT, "security"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error("Review task failed", extra={"error": str(result)})
        elif isinstance(result, list):
            all_findings.extend(result)

    return all_findings


async def _review_file(
    client: anthropic.AsyncAnthropic,
    file,
    positions: dict[int, int],
    system_prompt: str,
    pass_name: str,
) -> list[dict]:
    language = detect_language(file.filename)

    # Chunk large diffs to stay within token limits
    patch = file.patch or ""
    if len(patch) > 8000:
        patch = patch[:8000] + "\n... [diff truncated for length]"

    prompt = f"""File: {file.filename}
Language: {language}

Diff:
{patch}

Review the above diff and return your findings as a JSON array."""

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        findings = _parse_json_response(response_text)

        # Enrich with file name and diff positions
        for finding in findings:
            finding["file"] = file.filename
            finding["pass"] = pass_name
            line = finding.get("line", 1)
            finding["diff_position"] = positions.get(line, 1)

        logger.info(
            "File reviewed",
            extra={
                "file": file.filename,
                "pass": pass_name,
                "findings": len(findings),
            },
        )
        return findings

    except Exception as e:
        logger.error(
            "Claude API call failed",
            extra={"file": file.filename, "pass": pass_name, "error": str(e)},
        )
        return []


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON from Claude's response, with fallback extraction."""
    text = text.strip()

    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting JSON array from response
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse Claude response as JSON", extra={"response_preview": text[:200]})
    return []
