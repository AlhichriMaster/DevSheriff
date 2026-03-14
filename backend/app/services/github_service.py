from github import Github

from app.services.auth_service import get_installation_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


async def handle_pull_request_event(payload: dict):
    """Main entry point: orchestrates fetching, reviewing, and commenting on a PR."""
    repo_full_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]

    logger.info(
        "Processing PR event",
        extra={"repo": repo_full_name, "pr_number": pr_number},
    )

    try:
        installation_id = payload["installation"]["id"]
        token = await get_installation_token(installation_id)

        g = Github(token)
        repo = g.get_repo(repo_full_name)
        pull = repo.get_pull(pr_number)

        files = list(pull.get_files())
        logger.info(
            "Fetched PR files",
            extra={"repo": repo_full_name, "pr_number": pr_number, "file_count": len(files)},
        )

        from app.config.repo_config import load_repo_config
        config = load_repo_config(repo, pull.head.sha)

        from app.services.review_engine import run_review
        findings = await run_review(files, config)

        if config.security.scan_dependencies:
            from app.services.dependency_scanner import scan_dependencies
            dep_findings = await scan_dependencies(files)
            findings.extend(dep_findings)

        logger.info(
            "Review complete",
            extra={
                "repo": repo_full_name,
                "pr_number": pr_number,
                "finding_count": len(findings),
            },
        )

        review_comments = []
        for finding in findings:
            if finding.get("diff_position"):
                review_comments.append({
                    "path": finding["file"],
                    "position": finding["diff_position"],
                    "body": _format_comment(finding),
                })

        commit = repo.get_commit(pull.head.sha)

        if review_comments:
            summary = _generate_summary(findings)
            pull.create_review(
                commit=commit,
                body=summary,
                event="COMMENT",
                comments=review_comments,
            )
        elif findings:
            # Post as regular comment if no positionable comments
            pull.create_issue_comment(_generate_summary(findings))

        worst = _get_worst_severity(findings)
        block_on = set(config.security.block_merge_on)
        state = "failure" if worst in block_on else "success"

        commit.create_status(
            state=state,
            description=f"DevSheriff: {len(findings)} finding(s)",
            context="devsheriff/review",
            target_url="https://devsheriff.run.app",
        )

        from app.services.firestore_service import save_review
        await save_review(payload, findings)

    except Exception as e:
        logger.error(
            "Error processing PR event",
            extra={"repo": repo_full_name, "pr_number": pr_number, "error": str(e)},
        )
        raise


def _format_comment(finding: dict) -> str:
    severity = finding.get("severity", "info")
    emoji = SEVERITY_EMOJI.get(severity, "⚪")
    title = finding.get("title", "")
    category = finding.get("category", "").capitalize()
    owasp = finding.get("owasp_category", "")
    body = finding.get("body", "")
    suggestion = finding.get("suggestion", "")
    cve_ids = finding.get("cve_ids", [])

    owasp_line = f" | **OWASP:** {owasp}" if owasp else ""
    cve_line = f"\n\n**CVEs:** {', '.join(cve_ids)}" if cve_ids else ""

    comment = f"""## {emoji} [{severity.capitalize()}] {title}

**Category:** {category}{owasp_line}{cve_line}

{body}
"""

    if suggestion:
        comment += f"\n**Suggested fix:**\n```\n{suggestion}\n```\n"

    comment += "\n---\n*[DevSheriff](https://devsheriff.run.app) — AI-powered code review*"
    return comment


def _generate_summary(findings: list[dict]) -> str:
    if not findings:
        return "## ✅ DevSheriff Review\n\nNo issues found. Looking good!"

    counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1

    lines = ["## 🔍 DevSheriff Review Summary\n"]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in counts:
            emoji = SEVERITY_EMOJI.get(sev, "⚪")
            lines.append(f"- {emoji} **{sev.capitalize()}**: {counts[sev]}")

    lines.append(f"\n**Total findings:** {len(findings)}")
    lines.append("\n---\n*[DevSheriff](https://devsheriff.run.app) — AI-powered code review*")
    return "\n".join(lines)


def _get_worst_severity(findings: list[dict]) -> str:
    order = ["critical", "high", "medium", "low", "info"]
    found_severities = {f.get("severity", "info") for f in findings}
    for sev in order:
        if sev in found_severities:
            return sev
    return "info"
