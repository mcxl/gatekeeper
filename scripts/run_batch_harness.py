#!/usr/bin/env python3
"""
scripts/run_batch_harness.py — Run multiple job briefs through the SWMS pipeline
and produce a structured comparison report.

Usage:
    python scripts/run_batch_harness.py --all
    python scripts/run_batch_harness.py --all --concurrency 3
    python scripts/run_batch_harness.py --all --with-reviewer --with-docx
    python scripts/run_batch_harness.py job_briefs/c01_unitas_roofing.json job_briefs/c08_podium_slab.json
    python scripts/run_batch_harness.py --all --dry-run
"""

import argparse
import asyncio
import json
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

# Haiku pricing per 1M tokens (as of 2026-04)
_HAIKU_INPUT_COST_PER_M = 0.80
_HAIKU_OUTPUT_COST_PER_M = 4.00


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
    # Optional richer fields
    reviewer_status: str = ""
    reviewer_hard_fails: int = 0
    reviewer_review_items: int = 0
    docx_rendered: bool = False
    edit_capture_available: bool = False
    edit_changed_task_count: int = 0
    edit_average_similarity: float = 0.0
    edit_changed_responsibilities: int = 0
    edit_major_rewrite: bool = False
    edit_categories: list[str] = field(default_factory=list)
    # Token/cost tracking
    control_writer_input_tokens: int = 0
    control_writer_output_tokens: int = 0
    control_writer_calls: int = 0
    control_writer_estimated_cost: float = 0.0


@dataclass
class BatchReport:
    timestamp: str = ""
    total_jobs: int = 0
    completed: int = 0
    failed: int = 0
    concurrency: int = 1
    with_reviewer: bool = False
    with_docx: bool = False
    with_edit_capture: bool = False
    results: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


@dataclass
class RunOptions:
    with_reviewer: bool = False
    with_docx: bool = False
    with_edit_capture: bool = False


def discover_briefs() -> list[Path]:
    """Find all .json briefs in job_briefs/."""
    return sorted(BRIEFS_DIR.glob("*.json"))


def load_brief(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate Haiku API cost from token counts."""
    return round(
        (input_tokens / 1_000_000) * _HAIKU_INPUT_COST_PER_M
        + (output_tokens / 1_000_000) * _HAIKU_OUTPUT_COST_PER_M,
        4,
    )


async def run_single_job(brief_path: Path, options: RunOptions | None = None) -> JobResult:
    """Run one job brief through generate -> validate -> gate (+ optional richer steps)."""
    options = options or RunOptions()
    brief = load_brief(brief_path)
    result = JobResult(
        brief_id=brief_path.stem,
        customer=brief.get("customer", ""),
        project=brief.get("project", "")[:80],
        job_type=brief.get("job_type", ""),
    )

    t0 = time.monotonic()
    try:
        from agents.control_writer import get_token_usage, reset_token_usage
        from core.orchestrator import generate_swms
        from core.validator_runner import StreamConfig, run_internal_validator
        from src.issue_gate import Stage, run_issue_gate

        reset_token_usage()

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
        inference = gen.get("inference", {})
        result.task_count = len(tasks)

        task_dicts = [t if isinstance(t, dict) else t.__dict__ for t in tasks]

        # Token usage from control writer
        usage = get_token_usage()
        result.control_writer_input_tokens = usage["input_tokens"]
        result.control_writer_output_tokens = usage["output_tokens"]
        result.control_writer_calls = usage["calls"]
        result.control_writer_estimated_cost = _estimate_cost(
            usage["input_tokens"], usage["output_tokens"]
        )

        # Validator
        vr = run_internal_validator(
            tasks=task_dicts,
            stream_config=StreamConfig(job_type=brief.get("job_type", "")),
        )
        result.validator_status = vr.status.value
        result.validator_fail_count = len(vr.failing_checks)
        result.validator_review_count = len(vr.review_checks)
        result.escalated = vr.status.value == "ESCALATE_EXTERNAL"

        # Issue gate
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

        # Optional: render docx
        if options.with_docx:
            try:
                from core.schema import TaskBlock
                from renderers.docx_renderer import render_swms_document
                task_blocks = [
                    t if isinstance(t, TaskBlock) else TaskBlock(**t)
                    for t in tasks
                ]
                render_swms_document(task_blocks, project_meta, inference)
                result.docx_rendered = True
            except Exception:
                result.docx_rendered = False

        # Optional: reviewer
        if options.with_reviewer and result.escalated:
            try:
                from core.reviewer_agent import run_parallel_review
                reviewer_result = await run_parallel_review(task_dicts)
                result.reviewer_status = reviewer_result.overall_status
                result.reviewer_hard_fails = len(reviewer_result.hard_fails)
                result.reviewer_review_items = len(reviewer_result.review_items)
            except Exception:
                result.reviewer_status = "ERROR"

        # Optional: edit capture (requires reviewed artifact in brief)
        if options.with_edit_capture:
            reviewed_path = brief.get("reviewed_docx_path", "")
            if reviewed_path and Path(reviewed_path).exists():
                try:
                    from core.edit_capture import (
                        compute_edit_delta,
                        extract_swms_table_text,
                    )
                    from core.schema import TaskBlock
                    from renderers.docx_renderer import render_swms_document
                    task_blocks = [
                        t if isinstance(t, TaskBlock) else TaskBlock(**t)
                        for t in tasks
                    ]
                    gen_bytes = render_swms_document(task_blocks, project_meta, inference)
                    with open(reviewed_path, "rb") as f:
                        rev_bytes = f.read()
                    gen_rows = extract_swms_table_text(gen_bytes)
                    rev_rows = extract_swms_table_text(rev_bytes)
                    delta = compute_edit_delta(gen_rows, rev_rows)
                    result.edit_capture_available = True
                    result.edit_changed_task_count = delta["changed_task_count"]
                    result.edit_average_similarity = delta["average_similarity_ratio"]
                    result.edit_changed_responsibilities = delta["changed_responsibilities_count"]
                    result.edit_major_rewrite = delta["major_rewrite_detected"]
                    result.edit_categories = brief.get("main_edit_categories", [])
                except Exception:
                    result.edit_capture_available = False

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    result.elapsed_seconds = round(time.monotonic() - t0, 1)
    return result


def build_summary(results: list[JobResult]) -> dict:
    """Compute top-level summary stats."""
    completed = [r for r in results if not r.error]
    with_cost = [r for r in completed if r.control_writer_calls > 0]
    with_edit = [r for r in completed if r.edit_capture_available]
    with_reviewer = [r for r in completed if r.reviewer_status]
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
        # Token/cost summary
        "total_cw_input_tokens": sum(r.control_writer_input_tokens for r in with_cost),
        "total_cw_output_tokens": sum(r.control_writer_output_tokens for r in with_cost),
        "total_cw_estimated_cost": round(sum(r.control_writer_estimated_cost for r in with_cost), 4),
        "avg_cw_cost_per_job": round(
            sum(r.control_writer_estimated_cost for r in with_cost) / max(len(with_cost), 1), 4
        ),
        "jobs_with_cw_cost_data": len(with_cost),
        # Optional richer summary
        "jobs_with_edit_capture": len(with_edit),
        "jobs_with_reviewer_runs": len(with_reviewer),
    }


def format_markdown(report: BatchReport) -> str:
    """Render the report as human-readable markdown."""
    lines = [
        f"# Batch Comparison Report -- {report.timestamp}",
        "",
        f"**Jobs:** {report.summary.get('completed', 0)}/{report.summary.get('total_jobs', 0)} completed"
        f" | **Zero-FAIL:** {report.summary.get('zero_fail_jobs', 0)}"
        f" | **Avg gate FAIL:** {report.summary.get('avg_gate_fails', 0)}"
        f" | **Avg gate REVIEW:** {report.summary.get('avg_gate_reviews', 0)}"
        f" | **Concurrency:** {report.concurrency}",
        "",
        "| # | Brief | Customer | Type | Tasks | Validator | Gate F | Gate R | CW Cost | Time | Notable |",
        "|---|-------|----------|------|-------|-----------|--------|--------|---------|------|---------|",
    ]
    for i, r in enumerate(report.results, 1):
        notable = r.get("error", "") or "; ".join(r.get("gate_fail_checks", [])[:2]) or "clean"
        if len(notable) > 40:
            notable = notable[:37] + "..."
        cw_cost = f"${r.get('control_writer_estimated_cost', 0):.3f}" if r.get("control_writer_calls", 0) else "n/a"
        lines.append(
            f"| {i} | {r['brief_id'][:22]} | {r['customer'][:12]} | {r['job_type']} "
            f"| {r['task_count']} | {r['validator_status']} | {r['gate_fail']} "
            f"| {r['gate_review']} | {cw_cost} | {r['elapsed_seconds']}s | {notable} |"
        )

    s = report.summary
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Validator PASS_INTERNAL: {s.get('validator_pass_internal', 0)}",
        f"- Validator RETRY_INTERNAL: {s.get('validator_retry_internal', 0)}",
        f"- Validator ESCALATE_EXTERNAL: {s.get('validator_escalate_external', 0)}",
        f"- Total gate FAILs across all jobs: {s.get('total_gate_fails', 0)}",
        f"- Total gate REVIEWs across all jobs: {s.get('total_gate_reviews', 0)}",
        f"- Most FAILs: {s.get('most_fails_job', 'n/a')}",
        f"- Average time per job: {s.get('avg_elapsed_seconds', 0)}s",
        "",
        "## Control Writer Cost",
        "",
        f"- Jobs with cost data: {s.get('jobs_with_cw_cost_data', 0)}",
        f"- Total input tokens: {s.get('total_cw_input_tokens', 0):,}",
        f"- Total output tokens: {s.get('total_cw_output_tokens', 0):,}",
        f"- Total estimated cost: ${s.get('total_cw_estimated_cost', 0):.4f}",
        f"- Avg cost per job: ${s.get('avg_cw_cost_per_job', 0):.4f}",
    ])

    if s.get("jobs_with_reviewer_runs", 0):
        lines.append(f"\n- Jobs with reviewer runs: {s['jobs_with_reviewer_runs']}")
    if s.get("jobs_with_edit_capture", 0):
        lines.append(f"- Jobs with edit capture: {s['jobs_with_edit_capture']}")

    return "\n".join(lines)


async def run_batch(
    brief_paths: list[Path],
    dry_run: bool = False,
    concurrency: int = 1,
    options: RunOptions | None = None,
) -> BatchReport:
    """Run briefs with bounded concurrency and build the report."""
    options = options or RunOptions()
    report = BatchReport(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_jobs=len(brief_paths),
        concurrency=concurrency,
        with_reviewer=options.with_reviewer,
        with_docx=options.with_docx,
        with_edit_capture=options.with_edit_capture,
    )

    if dry_run:
        for bp in brief_paths:
            brief = load_brief(bp)
            print(f"  {bp.stem}: {brief.get('customer', '?')} / {brief.get('job_type', '?')}")
        print(f"\n{len(brief_paths)} job(s) would be run (concurrency={concurrency}).")
        return report

    sem = asyncio.Semaphore(concurrency)
    results_lock = asyncio.Lock()
    counter = {"done": 0}

    async def run_with_sem(bp: Path) -> JobResult:
        async with sem:
            r = await run_single_job(bp, options)
            async with results_lock:
                counter["done"] += 1
                n = counter["done"]
            status = r.error if r.error else f"{r.validator_status} | gate {r.gate_fail}F {r.gate_review}R"
            cost_str = f" | CW ${r.control_writer_estimated_cost:.3f}" if r.control_writer_calls else ""
            print(f"[{n}/{len(brief_paths)}] {bp.stem} -> {status}{cost_str} ({r.elapsed_seconds}s)")
            return r

    job_results = await asyncio.gather(
        *(run_with_sem(bp) for bp in brief_paths),
        return_exceptions=True,
    )

    for i, jr in enumerate(job_results):
        if isinstance(jr, Exception):
            err_result = JobResult(
                brief_id=brief_paths[i].stem,
                error=f"{type(jr).__name__}: {jr}",
            )
            report.results.append(asdict(err_result))
            report.failed += 1
        else:
            report.results.append(asdict(jr))
            if jr.error:
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
    parser.add_argument("--concurrency", "-c", type=int, default=2,
                        help="Max concurrent jobs (default: 2)")
    parser.add_argument("--with-reviewer", action="store_true",
                        help="Run reviewer on escalated jobs")
    parser.add_argument("--with-docx", action="store_true",
                        help="Render docx for each job")
    parser.add_argument("--with-edit-capture", action="store_true",
                        help="Run edit capture if reviewed artifact exists")
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

    options = RunOptions(
        with_reviewer=args.with_reviewer,
        with_docx=args.with_docx,
        with_edit_capture=args.with_edit_capture,
    )

    asyncio.run(run_batch(paths, dry_run=args.dry_run, concurrency=args.concurrency, options=options))


if __name__ == "__main__":
    main()
