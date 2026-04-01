#!/usr/bin/env python3
"""
scripts/run_batch_harness.py — Run multiple job briefs through the SWMS pipeline
and produce a structured comparison report.

Usage:
    python scripts/run_batch_harness.py --all
    python scripts/run_batch_harness.py job_briefs/c01_unitas_roofing.json job_briefs/c08_podium_slab.json
    python scripts/run_batch_harness.py --all --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BRIEFS_DIR = ROOT / "job_briefs"
OUTPUTS_DIR = ROOT / "src" / "outputs"


@dataclass
class JobResult:
    brief_id: str = ""
    customer: str = ""
    project: str = ""
    job_type: str = ""
    task_count: int = 0
    validator_status: str = ""
    validator_fail_count: int = 0
    validator_review_count: int = 0
    gate_classification: str = ""
    gate_pass: int = 0
    gate_fail: int = 0
    gate_review: int = 0
    gate_fail_checks: list[str] = field(default_factory=list)
    gate_review_checks: list[str] = field(default_factory=list)
    escalated: bool = False
    elapsed_seconds: float = 0.0
    error: str = ""


@dataclass
class BatchReport:
    timestamp: str = ""
    total_jobs: int = 0
    completed: int = 0
    failed: int = 0
    results: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def discover_briefs() -> list[Path]:
    """Find all .json briefs in job_briefs/."""
    return sorted(BRIEFS_DIR.glob("*.json"))


def load_brief(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def run_single_job(brief_path: Path) -> JobResult:
    """Run one job brief through generate → validate → gate."""
    brief = load_brief(brief_path)
    result = JobResult(
        brief_id=brief_path.stem,
        customer=brief.get("customer", ""),
        project=brief.get("project", "")[:80],
        job_type=brief.get("job_type", ""),
    )

    t0 = time.monotonic()
    try:
        from core.orchestrator import generate_swms
        from core.validator_runner import StreamConfig, run_internal_validator
        from src.issue_gate import Stage, run_issue_gate

        description = brief.get("scope_of_works", brief.get("project", ""))
        project_meta = {
            "project_name": brief.get("project", ""),
            "site_address": "",
            "principal_contractor": brief.get("customer", ""),
            "work_activity": description,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "version": "V1",
        }
        scope_context = {
            "job_type": brief.get("job_type", ""),
            "scope_modifiers": brief.get("scope_modifiers", []),
        }

        gen = await generate_swms(
            description=description,
            project_meta=project_meta,
            force_full=True,
            scope_context=scope_context,
        )

        tasks = gen.get("tasks", [])
        result.task_count = len(tasks)

        task_dicts = [t if isinstance(t, dict) else t.__dict__ for t in tasks]

        # Validator
        vr = run_internal_validator(
            tasks=task_dicts,
            stream_config=StreamConfig(job_type=brief.get("job_type", "")),
        )
        result.validator_status = vr.status.value
        result.validator_fail_count = len(vr.failing_checks)
        result.validator_review_count = len(vr.review_checks)
        result.escalated = vr.status.value == "ESCALATE_EXTERNAL"

        # Issue gate (JSON only — no docx render needed for comparison)
        gate = run_issue_gate(tasks=task_dicts, stage=Stage.BENCHMARK)
        result.gate_classification = gate.classification.value
        result.gate_pass = gate.passed
        result.gate_fail = gate.failed
        result.gate_review = gate.review
        result.gate_fail_checks = [
            f"{c.name}: {c.detail[:60]}"
            for c in gate.checks if c.result.value == "FAIL"
        ]
        result.gate_review_checks = [
            f"{c.name}: {c.detail[:60]}"
            for c in gate.checks if c.result.value == "REVIEW"
        ]

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    result.elapsed_seconds = round(time.monotonic() - t0, 1)
    return result


def build_summary(results: list[JobResult]) -> dict:
    """Compute top-level summary stats."""
    completed = [r for r in results if not r.error]
    return {
        "total_jobs": len(results),
        "completed": len(completed),
        "errored": len(results) - len(completed),
        "validator_pass_internal": sum(1 for r in completed if r.validator_status == "PASS_INTERNAL"),
        "validator_retry_internal": sum(1 for r in completed if r.validator_status == "RETRY_INTERNAL"),
        "validator_escalate_external": sum(1 for r in completed if r.validator_status == "ESCALATE_EXTERNAL"),
        "total_gate_fails": sum(r.gate_fail for r in completed),
        "total_gate_reviews": sum(r.gate_review for r in completed),
        "zero_fail_jobs": sum(1 for r in completed if r.gate_fail == 0),
        "avg_gate_fails": round(sum(r.gate_fail for r in completed) / max(len(completed), 1), 1),
        "avg_gate_reviews": round(sum(r.gate_review for r in completed) / max(len(completed), 1), 1),
        "avg_elapsed_seconds": round(sum(r.elapsed_seconds for r in completed) / max(len(completed), 1), 1),
        "most_fails_job": max(completed, key=lambda r: r.gate_fail).brief_id if completed else "",
    }


def format_markdown(report: BatchReport) -> str:
    """Render the report as human-readable markdown."""
    lines = [
        f"# Batch Comparison Report — {report.timestamp}",
        "",
        f"**Jobs:** {report.summary.get('completed', 0)}/{report.summary.get('total_jobs', 0)} completed"
        f" | **Zero-FAIL:** {report.summary.get('zero_fail_jobs', 0)}"
        f" | **Avg gate FAIL:** {report.summary.get('avg_gate_fails', 0)}"
        f" | **Avg gate REVIEW:** {report.summary.get('avg_gate_reviews', 0)}",
        "",
        "| # | Brief | Customer | Type | Tasks | Validator | Gate F | Gate R | Time | Notable |",
        "|---|-------|----------|------|-------|-----------|--------|--------|------|---------|",
    ]
    for i, r in enumerate(report.results, 1):
        notable = r.get("error", "") or "; ".join(r.get("gate_fail_checks", [])[:2]) or "clean"
        if len(notable) > 50:
            notable = notable[:47] + "..."
        lines.append(
            f"| {i} | {r['brief_id'][:25]} | {r['customer'][:15]} | {r['job_type']} "
            f"| {r['task_count']} | {r['validator_status']} | {r['gate_fail']} "
            f"| {r['gate_review']} | {r['elapsed_seconds']}s | {notable} |"
        )

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Validator PASS_INTERNAL: {report.summary.get('validator_pass_internal', 0)}",
        f"- Validator RETRY_INTERNAL: {report.summary.get('validator_retry_internal', 0)}",
        f"- Validator ESCALATE_EXTERNAL: {report.summary.get('validator_escalate_external', 0)}",
        f"- Total gate FAILs across all jobs: {report.summary.get('total_gate_fails', 0)}",
        f"- Total gate REVIEWs across all jobs: {report.summary.get('total_gate_reviews', 0)}",
        f"- Most FAILs: {report.summary.get('most_fails_job', 'n/a')}",
        f"- Average time per job: {report.summary.get('avg_elapsed_seconds', 0)}s",
    ])
    return "\n".join(lines)


async def run_batch(brief_paths: list[Path], dry_run: bool = False) -> BatchReport:
    """Run all briefs sequentially and build the report."""
    report = BatchReport(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_jobs=len(brief_paths),
    )

    if dry_run:
        for bp in brief_paths:
            brief = load_brief(bp)
            print(f"  {bp.stem}: {brief.get('customer', '?')} / {brief.get('job_type', '?')}")
        print(f"\n{len(brief_paths)} job(s) would be run.")
        return report

    for i, bp in enumerate(brief_paths, 1):
        print(f"[{i}/{len(brief_paths)}] Running {bp.stem}...", flush=True)
        result = await run_single_job(bp)
        report.results.append(asdict(result))
        status = result.error if result.error else f"{result.validator_status} | gate {result.gate_fail}F {result.gate_review}R"
        print(f"  -> {status} ({result.elapsed_seconds}s)")
        if result.error:
            report.failed += 1
        else:
            report.completed += 1

    report.summary = build_summary(
        [JobResult(**r) for r in report.results]
    )

    # Write outputs
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUTS_DIR / "batch_comparison_latest.json"
    md_path = OUTPUTS_DIR / "batch_comparison_latest.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, default=str)
        f.write("\n")
    print(f"\nJSON report: {json_path}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(format_markdown(report))
        f.write("\n")
    print(f"Markdown report: {md_path}")

    return report


def main():
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run job briefs through the SWMS pipeline and compare results."
    )
    parser.add_argument("briefs", nargs="*", help="Paths to job brief JSON files")
    parser.add_argument("--all", "-a", action="store_true", help="Run all briefs in job_briefs/")
    parser.add_argument("--dry-run", "-d", action="store_true", help="List jobs without running")
    args = parser.parse_args()

    if args.all:
        paths = discover_briefs()
    elif args.briefs:
        paths = [Path(b) if Path(b).is_absolute() else ROOT / b for b in args.briefs]
    else:
        parser.error("Provide brief paths or use --all")

    if not paths:
        print("No briefs found.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_batch(paths, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
