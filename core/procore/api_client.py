"""
core/procore/api_client.py — Minimal Procore REST API client for Phase 1B.

Bounded to:
- fetching one submittal attachment (PDF)
- posting one comment on a submittal log

Uses OAuth2 client_credentials or service account token.
All configuration via environment variables.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────────

PROCORE_BASE_URL = os.getenv("PROCORE_BASE_URL", "https://sandbox.procore.com")
PROCORE_API_URL = os.getenv("PROCORE_API_URL", "https://sandbox.procore.com/rest/v1.1")
PROCORE_CLIENT_ID = os.getenv("PROCORE_CLIENT_ID", "")
PROCORE_CLIENT_SECRET = os.getenv("PROCORE_CLIENT_SECRET", "")
PROCORE_ACCESS_TOKEN = os.getenv("PROCORE_ACCESS_TOKEN", "")
PROCORE_COMPANY_ID = os.getenv("PROCORE_COMPANY_ID", "")

# Timeout for API calls
_TIMEOUT = 30.0


def _get_headers() -> dict[str, str]:
    """Build authorization headers for Procore API calls."""
    token = PROCORE_ACCESS_TOKEN
    if not token:
        raise ValueError(
            "PROCORE_ACCESS_TOKEN not configured. "
            "Set it in .env or environment variables."
        )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if PROCORE_COMPANY_ID:
        headers["Procore-Company-Id"] = PROCORE_COMPANY_ID
    return headers


def is_live_configured() -> bool:
    """Check whether live Procore API credentials are configured."""
    return bool(PROCORE_ACCESS_TOKEN and PROCORE_CLIENT_ID)


def fetch_attachment(
    project_id: int,
    attachment_url: str,
) -> bytes:
    """Fetch a submittal attachment (PDF) from Procore.

    Returns the raw file bytes.
    Raises on network or auth errors.
    """
    headers = _get_headers()

    log.info(f"Fetching Procore attachment: project={project_id}, url={attachment_url[:80]}...")

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        response = client.get(attachment_url, headers=headers)
        response.raise_for_status()

    log.info(f"Fetched {len(response.content)} bytes from Procore")
    return response.content


def post_submittal_comment(
    project_id: int,
    submittal_log_id: int,
    comment_body: str,
) -> dict:
    """Post a comment on a Procore submittal log.

    This is the Phase 1B return path — posts review summary as a comment.
    The comment is advisory only and does not change submittal status.
    """
    headers = _get_headers()
    url = f"{PROCORE_API_URL}/projects/{project_id}/submittal_logs/{submittal_log_id}/comments"

    payload = {
        "comment": {
            "body": comment_body,
        }
    }

    log.info(f"Posting comment to submittal {submittal_log_id} in project {project_id}")

    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    log.info(f"Comment posted successfully: {response.status_code}")
    return response.json()


def format_review_as_comment(review_artifact: dict, attachment_filename: str = "") -> str:
    """Format a review artifact as a human-readable Procore comment.

    Keeps it short, structured, and advisory. Never implies approval.
    """
    lines = [
        "--- Safe Method Pre-Screen Review ---",
        "",
        f"Status: {review_artifact.get('status_recommendation', 'Unknown')}",
        f"Confidence: {review_artifact.get('review_confidence', 'Unknown')}",
        "",
    ]

    if attachment_filename:
        lines.append(f"Document: {attachment_filename}")
        lines.append("")

    amendments = review_artifact.get("required_amendments", [])
    if amendments:
        lines.append(f"Required Amendments ({len(amendments)}):")
        for i, a in enumerate(amendments, 1):
            sev = a.get("severity", "advisory").upper()
            lines.append(f"  {i}. [{sev}] {a.get('title', '')}")
            lines.append(f"     Reason: {a.get('reason', '')}")
        lines.append("")

    findings = review_artifact.get("structural_findings", {})
    issues = [k for k, v in findings.items() if v == "ISSUES FOUND"]
    if issues:
        lines.append(f"Structural issues: {', '.join(issues)}")
        lines.append("")

    lines.append(review_artifact.get("review_disclaimer", ""))
    lines.append("")
    lines.append("This is an automated pre-screen. Human review is required.")

    return "\n".join(lines)
