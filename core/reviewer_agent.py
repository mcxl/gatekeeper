"""
core/reviewer_agent.py — Parallel Critic specialisation for SWMS review.

Runs four specialist reviewer agents concurrently after the validator
returns ESCALATE_EXTERNAL. Does NOT replace the four-agent generation
pipeline. Does NOT parse docs/reviewer_rubric.md at runtime.

Usage:
    from core.reviewer_agent import run_parallel_review
    result = await run_parallel_review(swms_content, scope_content, job_type, stream_config)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import anthropic

log = logging.getLogger(__name__)


# ── Mirrored rubric constants (do NOT import from docs/) ─────────────────────

OVERALL_STATUS_BENCHMARK_CONFIRMED = "BENCHMARK_QUALITY_CONFIRMED"
OVERALL_STATUS_BENCHMARK_CAVEATS = "BENCHMARK_QUALITY_WITH_CAVEATS"
OVERALL_STATUS_STRONG_DRAFT = "STRONG_WORKING_DRAFT"
OVERALL_STATUS_BELOW_DRAFT = "BELOW_WORKING_DRAFT"

RECOMMENDED_ACTION_PASS = "PASS_TO_CLIENT"
RECOMMENDED_ACTION_TARGETED = "TARGETED_REWORK"
RECOMMENDED_ACTION_FULL = "FULL_REWORK"

HARD_FAIL_THRESHOLD_FULL_REWORK = 2

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1500


# ── Anthropic client (same lazy singleton pattern as other agents) ───────────

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class AgentFinding:
    status: str = "PASS"  # PASS | FAIL | REVIEW
    findings: list[str] = field(default_factory=list)
    automatable_defects: list[str] = field(default_factory=list)
    human_judgment_required: list[str] = field(default_factory=list)


@dataclass
class ReviewerResult:
    overall_status: str = OVERALL_STATUS_STRONG_DRAFT
    overall_summary: str = ""
    architecture_sequence: AgentFinding = field(default_factory=AgentFinding)
    hrcw_hazard: AgentFinding = field(default_factory=AgentFinding)
    ccvs_verification: AgentFinding = field(default_factory=AgentFinding)
    credibility_drift: AgentFinding = field(default_factory=AgentFinding)
    hard_fails: list[str] = field(default_factory=list)
    review_items: list[str] = field(default_factory=list)
    recommended_action: str = RECOMMENDED_ACTION_TARGETED

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status,
            "overall_summary": self.overall_summary,
            "architecture_sequence": {
                "status": self.architecture_sequence.status,
                "findings": self.architecture_sequence.findings,
                "automatable_defects": self.architecture_sequence.automatable_defects,
                "human_judgment_required": self.architecture_sequence.human_judgment_required,
            },
            "hrcw_hazard": {
                "status": self.hrcw_hazard.status,
                "findings": self.hrcw_hazard.findings,
                "automatable_defects": self.hrcw_hazard.automatable_defects,
                "human_judgment_required": self.hrcw_hazard.human_judgment_required,
            },
            "ccvs_verification": {
                "status": self.ccvs_verification.status,
                "findings": self.ccvs_verification.findings,
                "automatable_defects": self.ccvs_verification.automatable_defects,
                "human_judgment_required": self.ccvs_verification.human_judgment_required,
            },
            "credibility_drift": {
                "status": self.credibility_drift.status,
                "findings": self.credibility_drift.findings,
                "automatable_defects": self.credibility_drift.automatable_defects,
                "human_judgment_required": self.credibility_drift.human_judgment_required,
            },
            "hard_fails": self.hard_fails,
            "review_items": self.review_items,
            "recommended_action": self.recommended_action,
        }


# ── Specialist agent prompts ────────────────────────────────────────────────

_ARCH_PROMPT = """\
You are an Australian WHS consultant. Review task architecture and sequencing only.
Check: document control, task order against job-type mandatory sequence, framework vs
work-package misuse, latent condition packaging.
Return JSON with keys: status, findings, automatable_defects, human_judgment_required.
No narrative. status must be PASS, FAIL, or REVIEW."""

_HRCW_PROMPT = """\
You are an Australian WHS consultant. Review HRCW selection and dominant hazard logic only.
Check: HRCW selection vs actual task wording, dominant control family match per task type,
HRCW undercall and overcall, silica and hazmat adequacy.
Return JSON with keys: status, findings, automatable_defects, human_judgment_required.
No narrative. status must be PASS, FAIL, or REVIEW."""

_CCVS_PROMPT = """\
You are an Australian WHS consultant. Review CCVS evidence alignment only.
Check: evidence field matches dominant control family for each live task, WAH dominance,
missing CCVS rows for live tasks, N/A rows hiding real task risk.
Return JSON with keys: status, findings, automatable_defects, human_judgment_required.
No narrative. status must be PASS, FAIL, or REVIEW."""

_CRED_PROMPT = """\
You are an Australian WHS consultant. Review unsupported controls and professional
credibility only. Check: unsupported admin and governance controls, filler controls,
template contamination from another job family, whether the document reads like a
practitioner wrote it or a compliance collage.
Return JSON with keys: status, findings, automatable_defects, human_judgment_required.
No narrative. status must be PASS, FAIL, or REVIEW."""


# ── Agent call ───────────────────────────────────────────────────────────────

def _parse_agent_response(text: str) -> AgentFinding:
    """Parse agent JSON response into AgentFinding. Gracefully handle bad JSON."""
    try:
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return AgentFinding(
            status=data.get("status", "REVIEW"),
            findings=data.get("findings", []),
            automatable_defects=data.get("automatable_defects", []),
            human_judgment_required=data.get("human_judgment_required", []),
        )
    except (json.JSONDecodeError, AttributeError):
        return AgentFinding(
            status="REVIEW",
            findings=[f"Agent returned unparseable response: {text[:100]}"],
            human_judgment_required=["Response could not be parsed"],
        )


async def _call_specialist(system_prompt: str, user_content: str) -> AgentFinding:
    """Call a single specialist reviewer agent."""
    try:
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: _get_client().messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            ),
        )
        block = message.content[0]
        if hasattr(block, "text"):
            return _parse_agent_response(block.text)
        return AgentFinding(status="REVIEW", findings=["No text in response"])
    except Exception as e:
        log.warning(f"Reviewer agent call failed: {e}")
        return AgentFinding(
            status="REVIEW",
            findings=[f"Agent call failed: {type(e).__name__}: {e}"],
            human_judgment_required=["Agent unavailable — manual review required"],
        )


# ── Coordinator ──────────────────────────────────────────────────────────────

async def run_parallel_review(
    swms_content: str,
    scope_content: str,
    job_type: str = "",
    stream_config=None,
) -> ReviewerResult:
    """Run four specialist reviewer agents in parallel and assemble results.

    Args:
        swms_content: The full SWMS task JSON as a string
        scope_content: The original scope/description text
        job_type: The job_type from classify_swms_scope()
        stream_config: Optional StreamConfig for context

    Returns:
        ReviewerResult with assembled findings from all four agents.
    """
    user_content = (
        f"Job type: {job_type or 'unknown'}\n"
        f"Scope: {scope_content[:500]}\n\n"
        f"SWMS task data:\n{swms_content[:3000]}"
    )

    # Run all four agents concurrently
    arch, hrcw, ccvs, cred = await asyncio.gather(
        _call_specialist(_ARCH_PROMPT, user_content),
        _call_specialist(_HRCW_PROMPT, user_content),
        _call_specialist(_CCVS_PROMPT, user_content),
        _call_specialist(_CRED_PROMPT, user_content),
    )

    # Collect hard fails and review items
    hard_fails = []
    review_items = []
    for agent_name, finding in [
        ("architecture", arch), ("hrcw", hrcw),
        ("ccvs", ccvs), ("credibility", cred),
    ]:
        if finding.status == "FAIL":
            hard_fails.extend(f"[{agent_name}] {f}" for f in finding.findings)
        elif finding.status == "REVIEW":
            review_items.extend(f"[{agent_name}] {f}" for f in finding.findings)

    # Determine overall status using mirrored thresholds
    if len(hard_fails) >= HARD_FAIL_THRESHOLD_FULL_REWORK:
        overall_status = OVERALL_STATUS_BELOW_DRAFT
        recommended = RECOMMENDED_ACTION_FULL
    elif len(hard_fails) > 0:
        overall_status = OVERALL_STATUS_STRONG_DRAFT
        recommended = RECOMMENDED_ACTION_TARGETED
    elif len(review_items) > 0:
        overall_status = OVERALL_STATUS_BENCHMARK_CAVEATS
        recommended = RECOMMENDED_ACTION_PASS
    else:
        overall_status = OVERALL_STATUS_BENCHMARK_CONFIRMED
        recommended = RECOMMENDED_ACTION_PASS

    summary_parts = []
    if hard_fails:
        summary_parts.append(f"{len(hard_fails)} hard fail(s)")
    if review_items:
        summary_parts.append(f"{len(review_items)} review item(s)")
    if not summary_parts:
        summary_parts.append("All agents pass")

    return ReviewerResult(
        overall_status=overall_status,
        overall_summary="; ".join(summary_parts),
        architecture_sequence=arch,
        hrcw_hazard=hrcw,
        ccvs_verification=ccvs,
        credibility_drift=cred,
        hard_fails=hard_fails,
        review_items=review_items,
        recommended_action=recommended,
    )
