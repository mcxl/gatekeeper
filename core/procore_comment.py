"""
core/procore_comment.py — Post comments to Procore submittals.

Two tiers: SM (Safety Manager) and PM (Project Manager).
Never update existing comments. Always create new threads.
If PROCORE_ACCESS_TOKEN not set: log only, do not error.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

PROCORE_API_URL = os.getenv("PROCORE_API_URL", "https://sandbox.procore.com/rest/v1.1")
PROCORE_COMPANY_ID = os.getenv("PROCORE_COMPANY_ID", "")


def _get_token(access_token: str | None) -> str:
    return access_token or os.getenv("PROCORE_ACCESS_TOKEN", "")


def _reason_summary(review_result) -> str:
    """Generate PM-safe reason summary from highest severity finding."""
    if review_result.hard_fails:
        hf = review_result.hard_fails[0]
        if "hrcw" in hf.lower():
            return "missing HRCW controls"
        if "excavat" in hf.lower():
            return "excavation controls incomplete"
        if "fall" in hf.lower():
            return "fall prevention gap identified"
        return "missing mandatory controls"
    if review_result.amendments_required:
        return "amendments required"
    if review_result.overall_result == "REVIEW":
        return "amendments required"
    return "no issues found"


def _format_sm_review(review_result, correlation_id: str) -> str:
    """Format SM review comment with full detail."""
    lines = [f"Safe Method Review — {review_result.overall_result}"]
    lines.append("")

    if review_result.hard_fails:
        lines.append("HARD FAILS:")
        for hf in review_result.hard_fails:
            lines.append(f"  - {hf}")
        lines.append("")

    if review_result.hrcw_flags:
        lines.append(f"HRCW: {', '.join(review_result.hrcw_flags)}")
        lines.append("")

    if review_result.amendments_required:
        lines.append("AMENDMENTS REQUIRED:")
        for a in review_result.amendments_required:
            lines.append(f"  - {a}")
        lines.append("")

    for f in review_result.findings:
        vision_tag = ""
        if f.source == "vision_ocr":
            vision_tag = "[VISION-DERIVED — manual verification required] "
        lines.append(f"  [{f.severity.upper()}] {vision_tag}{f.code}: {f.description}")

    lines.append("")
    lines.append(f"Confidence: {review_result.confidence}")
    lines.append(f"Source: {review_result.extraction_source}")
    lines.append(f"Correlation ID: {correlation_id}")

    return "\n".join(lines)


def _format_pm_message(state: str, reason_summary: str = "") -> str:
    """Format PM-safe comment. No technical detail."""
    if state == "received":
        return "Safe Method: Review received — approximately 60 seconds."
    if state == "complete":
        return f"Safe Method: Review complete — {reason_summary}. See your Safety Manager for detail."
    if state == "aborted":
        return "Safe Method: Unable to process this document. Your Safety Manager has been notified."
    if state == "failed":
        return "Safe Method: Review could not be completed. Your Safety Manager has been notified."
    if state == "processing":
        return "Safe Method: Review in progress."
    return f"Safe Method: {state}"


async def _post_comment(
    submittal_id: str,
    body: str,
    correlation_id: str,
    access_token: str | None = None,
) -> None:
    """Post a comment to Procore. Log-only if no token."""
    token = _get_token(access_token)
    if not token:
        log.info(
            "Procore comment (log-only, no token): submittal=%s correlation_id=%s body=%s",
            submittal_id, correlation_id, body[:200],
        )
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if PROCORE_COMPANY_ID:
        headers["Procore-Company-Id"] = PROCORE_COMPANY_ID

    # Note: actual Procore API URL/path depends on surface. Using placeholder.
    url = f"{PROCORE_API_URL}/submittals/{submittal_id}/comments"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json={"comment": {"body": body}})
        log.info(
            "Procore comment posted: submittal=%s status=%d correlation_id=%s",
            submittal_id, response.status_code, correlation_id,
        )
    except Exception as e:
        log.warning("Procore comment failed: %s correlation_id=%s", e, correlation_id)


async def post_heartbeat_comment(
    submittal_id: str,
    state: str,
    correlation_id: str,
    tier: str = "pm",
    access_token: str | None = None,
    reason_summary: str = "",
) -> None:
    """Post a heartbeat comment. tier='sm' or 'pm'."""
    if tier == "pm":
        body = _format_pm_message(state, reason_summary)
    else:
        body = f"Safe Method: {state}. Correlation ID: {correlation_id}"
    await _post_comment(submittal_id, body, correlation_id, access_token)


async def post_review_comment(
    submittal_id: str,
    review_result,
    correlation_id: str,
    access_token: str | None = None,
) -> None:
    """Post SM review comment with full findings."""
    body = _format_sm_review(review_result, correlation_id)
    await _post_comment(submittal_id, body, correlation_id, access_token)
