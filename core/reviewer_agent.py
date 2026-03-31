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
MAX_TOKENS = 4000


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
    tasks_reviewed: int = 0

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status,
            "overall_summary": self.overall_summary,
            "tasks_reviewed": self.tasks_reviewed,
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

COLUMN STRUCTURE: 8 columns — Step, Task, Hazard, Risk (Pre), Controls, Risk (Post), Responsibility, CCVS Code.
Column 8 contains CCVS code, HP, and SWT in that order.

AUTOMATIC ISSUE GATE FLAGS — flag these regardless of overall status:
- Access setup after access-dependent tasks
- Removal after application or installation
- Coatings before repairs
- Reinstatement before finishes without source support
- Pre-start controls inside demobilisation
- Merged unlike work packages: demolition+waterproofing in one row, removal+reinstatement in one row

QUALITY THRESHOLDS:
BENCHMARK_QUALITY_CONFIRMED: source-faithful task map, believable workflow, no material sequencing gaps.
STRONG_WORKING_DRAFT: broad sequence correct, main hazards identified, usable after consultant completion.
BELOW_STRONG_WORKING_DRAFT: wrong sequence affecting safety logic, needs substantive rewrite.

Return a single flat JSON object. Keys: status, findings, automatable_defects, human_judgment_required.
All values must be arrays of SHORT strings (under 80 chars each). No nested objects.
status must be one of: PASS, FAIL, REVIEW. Keep total response under 2000 chars."""

_HRCW_PROMPT = """\
You are an Australian WHS consultant. Review HRCW selection and dominant hazard logic only.
Check: HRCW selection vs actual task wording, dominant control family match per task type,
HRCW undercall and overcall, silica and hazmat adequacy.

COLUMN STRUCTURE: 8 columns — Step, Task, Hazard, Risk (Pre), Controls, Risk (Post), Responsibility, CCVS Code.
Column 8 contains CCVS code, HP, and SWT in that order.

When reviewing Column 8 CCVS, check:
- CCVS code present and correct for task hazard family
- HRCW coherent with actual task wording, not just keywords
- Dominant control family in Column 5 matches Column 8 CCVS family

SINGLE DEFECT THAT STOPS CONFIRMATION:
- False confidence in HRCW on high-risk work
- Systematic Column 8 CCVS dominant-control mismatch

Return a single flat JSON object. Keys: status, findings, automatable_defects, human_judgment_required.
All values must be arrays of SHORT strings (under 80 chars each). No nested objects.
status must be one of: PASS, FAIL, REVIEW. Keep total response under 2000 chars."""

_CCVS_PROMPT = """\
You are an Australian WHS consultant. Review CCVS evidence alignment only.
Check: evidence field matches dominant control family for each live task, WAH dominance,
missing CCVS rows for live tasks, N/A rows hiding real task risk.

COLUMN STRUCTURE: 8 columns — Step, Task, Hazard, Risk (Pre), Controls, Risk (Post), Responsibility, CCVS Code.
Column 8 contains CCVS code, HP, and SWT in that order.

When reviewing Column 8, check all three components:
- CCVS code present and correct for task hazard family
- HP present and names a real condition
- SWT present and tied to the dominant task failure mode
- Order is CCVS first, HP second, SWT third

AUTOMATIC ISSUE GATE FLAGS:
- Column 8 CCVS/HP/SWT not aligned with dominant control in Column 5
- Column 8 HP missing or generic across multiple tasks
- Column 8 SWT missing or uses generic wording: stop work if unsafe / concerned / needed
- Column 8 SWT checks the wrong failure mode for the task

QUALITY THRESHOLDS:
BENCHMARK_QUALITY_CONFIRMED: Column 8 CCVS verifies dominant controls every task, HP present and task-relevant, SWT tied to dominant failure mode every task.
STRONG_WORKING_DRAFT: Column 8 CCVS not systematically wrong, some granularity still needs tightening.
BELOW_STRONG_WORKING_DRAFT: Wrong control family in Column 8 CCVS across multiple tasks, Column 8 HP or SWT missing or generic across multiple tasks.

Return a single flat JSON object. Keys: status, findings, automatable_defects, human_judgment_required.
All values must be arrays of SHORT strings (under 80 chars each). No nested objects.
status must be one of: PASS, FAIL, REVIEW. Keep total response under 2000 chars."""

_CRED_PROMPT = """\
You are an Australian WHS consultant. Review unsupported controls and professional
credibility only. Check: unsupported admin and governance controls, filler controls,
template contamination from another job family, whether the document reads like a
practitioner wrote it or a compliance collage.

COLUMN STRUCTURE: 8 columns — Step, Task, Hazard, Risk (Pre), Controls, Risk (Post), Responsibility, CCVS Code.
Column 8 contains CCVS code, HP, and SWT in that order.

AUTOMATIC ISSUE GATE FLAGS:
- Unsupported keywords in Column 5 without source support: council permit, EPA, NATA, demolition supervisor, utility disconnection, asbestos clearance as active scope when source says latent only
- HRCW not matching task wording
- Placeholder present at issue stage
- Generic SWT wording across more than two tasks

Each finding must be classified as:
- automatable_defect: a rule could catch this
- human_judgment_required: consultant judgment needed

BELOW_STRONG_WORKING_DRAFT signals — return status FAIL if ANY of these are present:
- unsupported controls in live task steps: after-hours council permit, owners corporation
  special resolution, strata by-law compliance, NATA certificate, active asbestos
  clearance as live scope when source says latent only
- plant/equipment listed not supported by source method: EWP and mobile crane on a
  scaffold-led occupied remedial job
- HRCW set thinner than both task content and source scope
- CCVS evidence checking access/harness on non-WAH dominant tasks
- framework controls packaged as live work package tasks
- active asbestos presumption embedded in live tasks when source confirms latent only

STRONG_WORKING_DRAFT minimum bar — ALL must be true:
- broad sequence correct for job family
- dominant hazard controls present per task, not just listed
- HRCW coherent with actual task content, not just keywords
- no unsupported controls in live task steps
- CCVS evidence verifies the dominant control family

Return a single flat JSON object. Keys: status, findings, automatable_defects, human_judgment_required.
All values must be arrays of SHORT strings (under 80 chars each). No nested objects.
status must be one of: PASS, FAIL, REVIEW. Keep total response under 2000 chars."""


# ── Agent call ───────────────────────────────────────────────────────────────

def _flatten_findings(raw: list | dict | str) -> list[str]:
    """Flatten agent findings into a list of plain strings.

    Agents may return:
    - list[str]: ["finding1", "finding2"]
    - list[dict]: [{"category": "...", "detail": "..."}]
    - dict: {"key": "value", ...}
    - str: "single finding"
    """
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, dict):
        return [f"{k}: {v}" for k, v in raw.items() if v]
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Flatten dict values into one string
                parts = [str(v) for v in item.values() if v]
                result.append(" — ".join(parts) if parts else str(item))
            else:
                result.append(str(item))
        return result
    return [str(raw)]


def _parse_agent_response(text: str) -> AgentFinding:
    """Parse agent JSON response into AgentFinding. Gracefully handle bad JSON."""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        # Use extract_json for robust parsing (handles trailing text)
        from core.utils import extract_json
        data = extract_json(cleaned)

        status = data.get("status", "REVIEW") if isinstance(data, dict) else "REVIEW"
        # Normalise status to PASS/FAIL/REVIEW
        if isinstance(status, str):
            status = status.upper()
            if status not in ("PASS", "FAIL", "REVIEW"):
                status = "REVIEW"

        return AgentFinding(
            status=status,
            findings=_flatten_findings(data.get("findings", [])) if isinstance(data, dict) else [],
            automatable_defects=_flatten_findings(data.get("automatable_defects", [])) if isinstance(data, dict) else [],
            human_judgment_required=_flatten_findings(data.get("human_judgment_required", [])) if isinstance(data, dict) else [],
        )
    except Exception:
        return AgentFinding(
            status="REVIEW",
            findings=[f"Agent returned unparseable response: {text[:200]}"],
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
    # Count tasks for logging
    try:
        _parsed = json.loads(swms_content) if isinstance(swms_content, str) else swms_content
        _task_count = len(_parsed) if isinstance(_parsed, list) else 0
    except Exception:
        _task_count = 0
    log.info(f"Reviewer agent receiving {_task_count} tasks, {len(swms_content)} chars")

    user_content = (
        f"Job type: {job_type or 'unknown'}\n"
        f"Total tasks: {_task_count}\n"
        f"Scope: {scope_content[:500]}\n\n"
        f"SWMS task data (full):\n{swms_content}"
    )

    # Run all four agents concurrently
    arch, hrcw, ccvs, cred = await asyncio.gather(
        _call_specialist(_ARCH_PROMPT, user_content),
        _call_specialist(_HRCW_PROMPT, user_content),
        _call_specialist(_CCVS_PROMPT, user_content),
        _call_specialist(_CRED_PROMPT, user_content),
    )

    # Collect hard fails and review items.
    # Calibration: don't promote ALL findings from a FAIL agent into hard_fails.
    # Only findings containing severity keywords are hard fails; the rest are review items.
    _HARD_FAIL_KEYWORDS = (
        "critical", "uncontrolled", "false confidence", "structural stability",
        "live electrical", "no isolation", "no exclusion zone",
        "systematic mismatch", "missing mandatory", "immediate_fail",
    )
    _REVIEW_DEMOTE_KEYWORDS = (
        "sequence", "order", "preference", "duplicate", "redundant",
        "template", "filler", "formatting", "version control",
        "credential", "competency", "vague", "weak", "incomplete",
        "correctly classified", "correct", "appropriate", "no undercall",
        "no overcall", "philosophy",
    )

    hard_fails = []
    review_items = []
    for agent_name, finding in [
        ("architecture", arch), ("hrcw", hrcw),
        ("ccvs", ccvs), ("credibility", cred),
    ]:
        for f in finding.findings:
            tagged = f"[{agent_name}] {f}"
            f_lower = f.lower()
            if finding.status == "FAIL":
                # Promote to hard fail only if it contains severity keywords
                # and does NOT contain review-demote keywords
                is_hard = any(kw in f_lower for kw in _HARD_FAIL_KEYWORDS)
                is_demoted = any(kw in f_lower for kw in _REVIEW_DEMOTE_KEYWORDS)
                if is_hard and not is_demoted:
                    hard_fails.append(tagged)
                else:
                    review_items.append(tagged)
            elif finding.status == "REVIEW":
                review_items.append(tagged)

    # COORDINATOR ASSEMBLY RULE:
    # If any specialist agent returns FAIL on credibility or drift,
    # overall status cannot be STRONG_WORKING_DRAFT or above.
    # Floor at BELOW_STRONG_WORKING_DRAFT.
    # Unsupported controls in live task steps are trust-killers.
    cred_floor_active = cred.status == "FAIL"

    # Determine overall status using calibrated thresholds
    if cred_floor_active:
        overall_status = OVERALL_STATUS_BELOW_DRAFT
        recommended = RECOMMENDED_ACTION_TARGETED
    elif len(hard_fails) >= HARD_FAIL_THRESHOLD_FULL_REWORK:
        overall_status = OVERALL_STATUS_BELOW_DRAFT
        recommended = RECOMMENDED_ACTION_FULL
    elif len(hard_fails) > 0:
        overall_status = OVERALL_STATUS_STRONG_DRAFT
        recommended = RECOMMENDED_ACTION_TARGETED
    elif len(review_items) > 3:
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
        tasks_reviewed=_task_count,
    )
