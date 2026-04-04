"""
core/procore_review.py — Run Sonnet review on extracted SWMS text.

Model: claude-sonnet-4-20250514 with prompt caching.
Output: structured JSON only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "procore_review_system.md"
_SYSTEM_PROMPT: str | None = None

MODEL = "claude-sonnet-4-20250514"


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _SYSTEM_PROMPT


@dataclass
class Finding:
    code: str = ""
    description: str = ""
    severity: str = "observation"  # hard_fail | amendment | observation
    hrcw_relevant: bool = False
    source: str = "pypdf"  # pypdf | vision_ocr


@dataclass
class ReviewResult:
    findings: list[Finding] = field(default_factory=list)
    hrcw_flags: list[str] = field(default_factory=list)
    hard_fails: list[str] = field(default_factory=list)
    amendments_required: list[str] = field(default_factory=list)
    overall_result: str = "REVIEW"  # PASS | FAIL | REVIEW
    confidence: str = "medium"  # high | medium | low
    extraction_source: str = "pypdf"  # pypdf | vision_ocr


async def run_procore_review(
    swms_text: str,
    correlation_id: str,
    extraction_source: str = "pypdf",
) -> ReviewResult:
    """Run Sonnet review on extracted SWMS text. Returns ReviewResult."""
    import anthropic

    system_prompt = _load_system_prompt()
    client = anthropic.Anthropic()

    log.info("Procore review start: correlation_id=%s source=%s", correlation_id, extraction_source)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{
                "role": "user",
                "content": f"Review this SWMS document:\n\n{swms_text[:15000]}",
            }],
        )

        raw_text = message.content[0].text.strip()

        # Parse JSON — strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        data = json.loads(raw_text)

    except (json.JSONDecodeError, Exception) as e:
        log.error("Procore review parse failed: %s correlation_id=%s", e, correlation_id)
        return ReviewResult(
            overall_result="REVIEW",
            confidence="low",
            extraction_source=extraction_source,
            findings=[Finding(
                code="PARSE_ERROR",
                description=f"Review engine returned unparseable output: {type(e).__name__}",
                severity="observation",
                source=extraction_source,
            )],
        )

    # Build result
    findings = []
    for f in data.get("findings", []):
        findings.append(Finding(
            code=f.get("code", ""),
            description=f.get("description", ""),
            severity=f.get("severity", "observation"),
            hrcw_relevant=f.get("hrcw_relevant", False),
            source=extraction_source,
        ))

    result = ReviewResult(
        findings=findings,
        hrcw_flags=data.get("hrcw_flags", []),
        hard_fails=data.get("hard_fails", []),
        amendments_required=data.get("amendments_required", []),
        overall_result=data.get("overall_result", "REVIEW"),
        confidence=data.get("confidence", "medium"),
        extraction_source=extraction_source,
    )

    log.info(
        "Procore review complete: correlation_id=%s result=%s findings=%d",
        correlation_id, result.overall_result, len(result.findings),
    )
    return result
