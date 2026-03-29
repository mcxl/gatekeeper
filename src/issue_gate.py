#!/usr/bin/env python3
"""
src/issue_gate.py — Deterministic SWMS issue-gate checker.

Takes a rendered .docx and/or task JSON and returns structured pass/fail/review
results for benchmark-stage review.

No API calls. No LLM dependency. Runs in < 2 seconds.

Usage:
    # As a library
    from src.issue_gate import run_issue_gate
    result = run_issue_gate(docx_path="output.docx", json_path="output.json")
    print(result.classification)  # FAIL_INTERNAL / REVIEW_INTERNAL / READY_FOR_EXPERT_REVIEW

    # As CLI
    python src/issue_gate.py output.docx --json output.json --stage benchmark
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ── Stage definitions ────────────────────────────────────────────────────────

class Stage(Enum):
    BENCHMARK = "benchmark"      # Draft/benchmark: placeholders acceptable
    ISSUE_READY = "issue_ready"  # Issue-ready: placeholders fail


class CheckResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"  # Not a hard fail but needs human attention


class Classification(Enum):
    FAIL_INTERNAL = "FAIL_INTERNAL"
    REVIEW_INTERNAL = "REVIEW_INTERNAL"
    READY_FOR_EXPERT_REVIEW = "READY_FOR_EXPERT_REVIEW"


@dataclass
class GateCheck:
    name: str
    result: CheckResult
    detail: str = ""


@dataclass
class GateResult:
    checks: list[GateCheck] = field(default_factory=list)
    classification: Classification = Classification.FAIL_INTERNAL
    stage: Stage = Stage.BENCHMARK
    task_count: int = 0

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.result == CheckResult.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.result == CheckResult.FAIL)

    @property
    def review(self) -> int:
        return sum(1 for c in self.checks if c.result == CheckResult.REVIEW)

    def summary(self) -> str:
        lines = [f"Issue Gate: {self.classification.value} "
                 f"({self.passed}/{len(self.checks)} pass, "
                 f"{self.failed} fail, {self.review} review) "
                 f"[stage={self.stage.value}, tasks={self.task_count}]"]
        for c in self.checks:
            marker = {"PASS": "OK", "FAIL": "FAIL", "REVIEW": "REV"}[c.result.value]
            detail = f" — {c.detail}" if c.detail else ""
            lines.append(f"  [{marker}] {c.name}{detail}")
        return "\n".join(lines)


# ── Keyword constants ────────────────────────────────────────────────────────

_ACCESS_KEYWORDS = ("scaffold", "ewp", "erect", "access equipment",
                    "elevated work platform")

_DEPENDENT_KEYWORDS = ("repair", "crack", "paint", "seal", "repoint", "treat",
                       "spalling", "coat", "stain", "primer", "reconstruct")

_COATING_KEYWORDS = ("paint", "seal", "treat", "stain", "coat", "primer",
                     "timber")

_PRESTART_KEYWORDS = ("resident", "neighbour", "vegetation", "parking",
                      "pre-commencement", "interface control")

_DEMOB_KEYWORDS = ("demob", "dismantle", "remove scaffold")

_UNSUPPORTED_KEYWORDS = (
    "utility isolation", "service isolation", "electrical isolation",
    "structural engineer", "traffic controller", "traffic control plan",
    "commissioning", "membrane", "biocide", "waterproof", "demolit",
    "council consent", "shoring plan", "propping plan", "propping design",
    "disconnection certificate", "provider certification",
)

_PLACEHOLDER_PATTERNS = (
    "[insert", "[to be confirmed", "[tbc", "[tbd",
    "[insert supervisor", "[insert manager",
)


# ── Check implementations ────────────────────────────────────────────────────

def _check_access_before_dependents(tasks: list[dict]) -> GateCheck:
    """C1: Access/setup appears before any dependent scaffold/EWP tasks."""
    access_pos = None
    dependent_first = None
    for i, t in enumerate(tasks):
        tn = t.get("task", "").lower()
        if access_pos is None and any(k in tn for k in _ACCESS_KEYWORDS):
            access_pos = i
        if dependent_first is None and any(k in tn for k in _DEPENDENT_KEYWORDS):
            dependent_first = i

    if access_pos is None:
        return GateCheck("access_before_dependents", CheckResult.REVIEW,
                         "No access/scaffold task found")
    if dependent_first is None:
        return GateCheck("access_before_dependents", CheckResult.PASS,
                         "No dependent tasks found")
    if access_pos <= dependent_first:
        return GateCheck("access_before_dependents", CheckResult.PASS,
                         f"Access at pos {access_pos}, first dependent at {dependent_first}")
    return GateCheck("access_before_dependents", CheckResult.FAIL,
                     f"Access at pos {access_pos}, but dependent task at {dependent_first}")


def _check_no_coat_reinstate_merge(tasks: list[dict]) -> GateCheck:
    """C2: Finish/coating tasks not merged with reinstatement tasks."""
    for t in tasks:
        tn = t.get("task", "").lower()
        has_coat = any(k in tn for k in _COATING_KEYWORDS)
        has_reinst = "reinstate" in tn or "reinstall" in tn
        if has_coat and has_reinst:
            return GateCheck("no_coat_reinstate_merge", CheckResult.FAIL,
                             f"Merged: {t.get('task', '?')}")
    return GateCheck("no_coat_reinstate_merge", CheckResult.PASS)


def _check_no_prestart_in_demob(tasks: list[dict]) -> GateCheck:
    """C3: Pre-start/interface controls do not appear in demob tasks."""
    for t in tasks:
        tn = t.get("task", "").lower()
        if not any(k in tn for k in _DEMOB_KEYWORDS):
            continue
        admin_text = " ".join(t.get("admin", [])).lower()
        controls_text = " ".join(t.get("controls", [])).lower()
        all_text = admin_text + " " + controls_text
        for kw in _PRESTART_KEYWORDS:
            if kw in all_text:
                return GateCheck("no_prestart_in_demob", CheckResult.FAIL,
                                 f"'{kw}' found in demob task")
    return GateCheck("no_prestart_in_demob", CheckResult.PASS)


def _check_ccvs_coverage(tasks: list[dict]) -> GateCheck:
    """C4: Every task that needs monitoring has a monitoring entry."""
    missing = []
    for t in tasks:
        mon = t.get("monitoring")
        has_mon = (isinstance(mon, dict)
                   and bool(mon.get("critical_control")))
        if not has_mon:
            missing.append(t.get("step", "?"))
    if missing:
        return GateCheck("ccvs_coverage", CheckResult.FAIL,
                         f"Tasks without monitoring: {missing}")
    return GateCheck("ccvs_coverage", CheckResult.PASS,
                     f"All {len(tasks)} tasks have monitoring")


def _check_ccvs_alignment(tasks: list[dict]) -> GateCheck:
    """C5: Monitoring evidence matches the CCVS code's dominant hazard."""
    mismatches = []
    for t in tasks:
        ccvs = t.get("ccvs_code", "N/A")
        mon = t.get("monitoring", {})
        cc = mon.get("critical_control", "").lower() if isinstance(mon, dict) else ""
        if not cc:
            continue
        if ccvs.startswith("SIL") and not any(k in cc for k in
                ("dust", "p2", "extraction", "respiratory", "silica")):
            mismatches.append(f"{t.get('step','?')}[{ccvs}]: no dust evidence")
        elif ccvs.startswith("CHM") and not any(k in cc for k in
                ("sds", "chemical", "ventilation", "respirat")):
            mismatches.append(f"{t.get('step','?')}[{ccvs}]: no chemical evidence")
        elif ccvs.startswith("SYS") and any(k in cc for k in
                ("harness", "dust extraction")):
            mismatches.append(f"{t.get('step','?')}[{ccvs}]: SYS has harness/dust evidence")
    if mismatches:
        return GateCheck("ccvs_alignment", CheckResult.FAIL,
                         "; ".join(mismatches[:3]))
    return GateCheck("ccvs_alignment", CheckResult.PASS)


def _check_wah_percentage(tasks: list[dict],
                          wah_threshold: int = 50) -> GateCheck:
    """C6: WAH codes are below threshold percentage.

    Default threshold: 50% for general SWMS.
    For WAH-dominant streams (EWP, rope access), pass a higher threshold.
    """
    if not tasks:
        return GateCheck("wah_percentage", CheckResult.PASS, "No tasks")
    wah = sum(1 for t in tasks if t.get("ccvs_code", "").startswith("WAH"))
    pct = wah * 100 // len(tasks)
    if pct >= wah_threshold:
        return GateCheck("wah_percentage", CheckResult.FAIL,
                         f"WAH: {wah}/{len(tasks)} ({pct}%) — threshold {wah_threshold}%")
    return GateCheck("wah_percentage", CheckResult.PASS,
                     f"WAH: {wah}/{len(tasks)} ({pct}%)")


def _check_unsupported_controls_docx(doc) -> GateCheck:
    """C7: No unsupported controls in rendered document."""
    from docx import Document
    found = []
    t2 = doc.tables[2] if len(doc.tables) > 2 else None
    if not t2:
        return GateCheck("unsupported_controls", CheckResult.REVIEW,
                         "Task table not found")
    for r in range(1, len(t2.rows)):
        row_text = " ".join(t2.rows[r].cells[c].text for c in range(
            min(8, len(t2.rows[r].cells)))).lower()
        step = t2.rows[r].cells[0].text.strip() if t2.rows[r].cells else "?"
        # Skip irrigation in green wall tasks (legitimate)
        task_text = t2.rows[r].cells[1].text.lower() if len(t2.rows[r].cells) > 1 else ""
        for kw in _UNSUPPORTED_KEYWORDS:
            if kw in row_text:
                # Exceptions: "propping" in hazard column is legitimate for brickwork
                if kw == "propping plan" or kw == "propping design":
                    continue
                found.append(f"{step}:{kw}")
        if "irrigation" in row_text and "green wall" not in task_text:
            found.append(f"{step}:irrigation")
    if found:
        return GateCheck("unsupported_controls", CheckResult.FAIL,
                         "; ".join(found[:5]))
    return GateCheck("unsupported_controls", CheckResult.PASS)


def _check_responsibility_field(doc, stage: Stage) -> GateCheck:
    """C8: Supervisor/responsible-person field — stage-aware.

    Benchmark/draft: visible placeholder is acceptable (REVIEW, not FAIL).
    Issue-ready: any placeholder is a FAIL.
    """
    t0 = doc.tables[0] if doc.tables else None
    if not t0 or len(t0.rows) < 5:
        return GateCheck("responsibility_field", CheckResult.FAIL,
                         "Cover table not found or too short")
    resp_text = t0.rows[4].cells[1].text.strip().lower() if len(t0.rows[4].cells) > 1 else ""
    is_placeholder = any(p in resp_text for p in _PLACEHOLDER_PATTERNS)
    is_blank = not resp_text

    if is_blank:
        return GateCheck("responsibility_field", CheckResult.FAIL,
                         "Responsible person field is blank")
    if is_placeholder:
        if stage == Stage.ISSUE_READY:
            return GateCheck("responsibility_field", CheckResult.FAIL,
                             f"Placeholder at issue-ready stage: '{resp_text}'")
        return GateCheck("responsibility_field", CheckResult.REVIEW,
                         f"Placeholder acceptable at {stage.value} stage: '{resp_text}'")
    return GateCheck("responsibility_field", CheckResult.PASS,
                     f"Populated: '{resp_text}'")


def _check_footer(doc) -> GateCheck:
    """C9: Footer filename and version populated and internally consistent."""
    section = doc.sections[0] if doc.sections else None
    if not section:
        return GateCheck("footer_version", CheckResult.FAIL, "No sections")
    footer = section.footer
    if not footer.tables:
        return GateCheck("footer_version", CheckResult.FAIL, "No footer table")
    ft = footer.tables[0]
    filename = ft.cell(0, 0).text.strip() if len(ft.rows) > 0 and len(ft.rows[0].cells) > 0 else ""
    version = ft.cell(0, 1).text.strip() if len(ft.rows) > 0 and len(ft.rows[0].cells) > 1 else ""

    issues = []
    if not filename or "SWMS" not in filename:
        issues.append("filename missing or invalid")
    if "[DOCUMENT_FILENAME]" in filename:
        issues.append("filename placeholder not replaced")
    if "[DOCUMENT_VERSION]" in version:
        issues.append("version placeholder not replaced")
    if not version:
        issues.append("version field empty")

    if issues:
        return GateCheck("footer_version", CheckResult.FAIL,
                         "; ".join(issues))
    return GateCheck("footer_version", CheckResult.PASS,
                     f"filename='{filename}', version='{version}'")


# ── Main runner ──────────────────────────────────────────────────────────────

def run_issue_gate(
    docx_path: Optional[str] = None,
    json_path: Optional[str] = None,
    tasks: Optional[list[dict]] = None,
    stage: Stage = Stage.BENCHMARK,
    wah_threshold: int = 50,
) -> GateResult:
    """Run all issue-gate checks and return structured results.

    Provide either:
    - docx_path + json_path (loads from files)
    - docx_path + tasks (tasks already in memory)
    - json_path only (loads tasks, skips docx-only checks)

    Returns GateResult with per-check results and overall classification.
    """
    from docx import Document

    result = GateResult(stage=stage)
    doc = None
    task_list = tasks

    # Load inputs
    if docx_path:
        doc = Document(docx_path)
    if json_path and not task_list:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        task_list = data.get("tasks", [])
    if not task_list:
        task_list = []

    result.task_count = len(task_list)

    # Run task-based checks (C1-C6)
    if task_list:
        result.checks.append(_check_access_before_dependents(task_list))
        result.checks.append(_check_no_coat_reinstate_merge(task_list))
        result.checks.append(_check_no_prestart_in_demob(task_list))
        result.checks.append(_check_ccvs_coverage(task_list))
        result.checks.append(_check_ccvs_alignment(task_list))
        result.checks.append(_check_wah_percentage(task_list, wah_threshold))

    # Run docx-based checks (C7-C9)
    if doc:
        result.checks.append(_check_unsupported_controls_docx(doc))
        result.checks.append(_check_responsibility_field(doc, stage))
        result.checks.append(_check_footer(doc))

    # Classify overall result
    if result.failed > 0:
        result.classification = Classification.FAIL_INTERNAL
    elif result.review > 0:
        result.classification = Classification.REVIEW_INTERNAL
    else:
        result.classification = Classification.READY_FOR_EXPERT_REVIEW

    return result


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SWMS Issue-Gate Checker")
    parser.add_argument("docx", nargs="?", help="Path to rendered .docx")
    parser.add_argument("--json", dest="json_path", help="Path to task JSON")
    parser.add_argument("--stage", choices=["benchmark", "issue_ready"],
                        default="benchmark", help="Stage (default: benchmark)")
    parser.add_argument("--wah-threshold", type=int, default=50,
                        help="WAH percentage threshold (default: 50, use 90 for EWP streams)")
    args = parser.parse_args()

    if not args.docx and not args.json_path:
        parser.error("Provide at least one of: docx path or --json path")

    stage = Stage.BENCHMARK if args.stage == "benchmark" else Stage.ISSUE_READY
    result = run_issue_gate(
        docx_path=args.docx,
        json_path=args.json_path,
        stage=stage,
        wah_threshold=args.wah_threshold,
    )
    print(result.summary())
    sys.exit(0 if result.failed == 0 else 1)


if __name__ == "__main__":
    main()
