"""
core/rule_promoter.py — Human-approved promotion proposals.

V1 CONSTRAINT: approve_candidate() does NOT mutate source files or prompts.
It generates a structured implementation proposal only.
That proposal is fed into a normal bounded Claude Code implementation phase.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from core.pattern_detector import (
    RuleCandidate,
    load_candidates,
    _update_candidate_status,
)

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "src" / "data"
_PROMOTION_LOG = _DATA_DIR / "promotion_log.jsonl"

# Maps suggested_target to the files that would need changing
_TARGET_FILE_MAP: dict[str, list[str]] = {
    "issue_gate": ["src/issue_gate.py"],
    "job_type_rules": ["core/job_type_rules.py"],
    "control_writer_prompt": ["agents/control_writer.py"],
    "decomposer_prompt": ["agents/decomposer.py"],
}


@dataclass
class PromotionProposal:
    candidate_id: str = ""
    target: str = ""
    files_to_change: list[str] = field(default_factory=list)
    proposal_text: str = ""
    implementation_notes: list[str] = field(default_factory=list)
    generated_patch_stub: str = ""
    status: str = "approved_for_implementation"


def list_candidates(status: str = "pending") -> list[RuleCandidate]:
    """Load candidates from rule_candidates.jsonl filtered by status."""
    return load_candidates(status=status)


def _build_proposal(candidate: RuleCandidate) -> PromotionProposal:
    """Build a structured implementation proposal from a candidate."""
    target = candidate.suggested_target
    files = _TARGET_FILE_MAP.get(target, [target])

    # Build implementation notes
    notes = [
        f"1. Open {', '.join(files)}",
        f"2. Add check for defect_family='{candidate.defect_family}', "
        f"check_name='{candidate.check_name}', job_type='{candidate.job_type}'",
        f"3. Rule text: {candidate.suggested_rule_text}",
        "4. Run pytest to confirm no regressions",
        "5. Run regression runner on affected streams",
    ]

    # Build patch stub based on target
    if target == "issue_gate":
        patch = _build_issue_gate_stub(candidate)
    elif target == "job_type_rules":
        patch = _build_job_type_rules_stub(candidate)
    elif target in ("control_writer_prompt", "decomposer_prompt"):
        patch = _build_prompt_stub(candidate)
    else:
        patch = f"# Add rule for {candidate.defect_family} / {candidate.check_name}\n# {candidate.suggested_rule_text}"

    proposal_text = (
        f"Implement a new rule to detect '{candidate.defect_family}' defects "
        f"via check '{candidate.check_name}' for job_type='{candidate.job_type}'. "
        f"This pattern occurred {candidate.occurrences} times with severity score "
        f"{candidate.severity_score:.1f}. "
        f"Target: {target}. "
        f"Examples: {'; '.join(candidate.example_findings[:2]) if candidate.example_findings else 'none recorded'}."
    )

    return PromotionProposal(
        candidate_id=candidate.candidate_id,
        target=target,
        files_to_change=files,
        proposal_text=proposal_text,
        implementation_notes=notes,
        generated_patch_stub=patch,
    )


def _build_issue_gate_stub(c: RuleCandidate) -> str:
    """Generate a concrete issue-gate check stub."""
    func_name = f"_check_{c.check_name or c.defect_family}".replace("-", "_").replace(" ", "_")
    return (
        f"def {func_name}(tasks: list[dict], job_type: str = \"\") -> list[str]:\n"
        f"    \"\"\"Check for {c.defect_family} — {c.suggested_rule_text}\"\"\"\n"
        f"    issues = []\n"
        f"    for t in tasks:\n"
        f"        # TODO: implement detection logic for {c.check_name}\n"
        f"        # Pattern: {c.example_findings[0][:80] if c.example_findings else 'see findings log'}\n"
        f"        pass\n"
        f"    return issues\n"
    )


def _build_job_type_rules_stub(c: RuleCandidate) -> str:
    """Generate a job-type rule pack addition stub."""
    return (
        f"# Add to {c.job_type or 'all'} rule pack:\n"
        f"# Rule: {c.suggested_rule_text}\n"
        f"# Defect family: {c.defect_family}\n"
        f"# Check: {c.check_name}\n"
        f"# Example: {c.example_findings[0][:80] if c.example_findings else 'see findings log'}\n"
    )


def _build_prompt_stub(c: RuleCandidate) -> str:
    """Generate a prompt addition stub."""
    return (
        f"# Add to NON-NEGOTIABLES section:\n"
        f"# - {c.suggested_rule_text}\n"
        f"# Defect family: {c.defect_family}\n"
        f"# Check: {c.check_name}\n"
        f"# Example: {c.example_findings[0][:80] if c.example_findings else 'see findings log'}\n"
    )


def _write_promotion_log(entry: dict) -> None:
    """Append a decision to promotion_log.jsonl."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_PROMOTION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        log.warning(f"rule_promoter: log write failed — {e}")


def approve_candidate(candidate_id: str) -> PromotionProposal:
    """Generate a structured implementation proposal for the candidate.
    Update candidate status to approved_for_implementation in rule_candidates.jsonl.
    Write proposal decision to promotion_log.jsonl.
    Do NOT mark findings as resolved.
    Do NOT mutate any source file or prompt."""
    # Find the candidate
    all_candidates = load_candidates()
    candidate = None
    for c in all_candidates:
        if c.candidate_id == candidate_id:
            candidate = c
            break

    if candidate is None:
        raise ValueError(f"Candidate {candidate_id} not found in rule_candidates.jsonl")

    # Build proposal
    proposal = _build_proposal(candidate)

    # Update candidate status
    _update_candidate_status(candidate_id, "approved_for_implementation")

    # Write to promotion log
    _write_promotion_log({
        "action": "approve",
        "candidate_id": candidate_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "proposal": asdict(proposal),
    })

    return proposal


def reject_candidate(candidate_id: str, reason: str) -> None:
    """Update candidate status to rejected in rule_candidates.jsonl.
    Write rejection decision with reason to promotion_log.jsonl.
    Do not mark findings as resolved."""
    # Verify candidate exists
    all_candidates = load_candidates()
    found = any(c.candidate_id == candidate_id for c in all_candidates)
    if not found:
        raise ValueError(f"Candidate {candidate_id} not found in rule_candidates.jsonl")

    _update_candidate_status(candidate_id, "rejected")

    _write_promotion_log({
        "action": "reject",
        "candidate_id": candidate_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
