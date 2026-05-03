#!/usr/bin/env python3
"""
Overnight retro-audit analysis runner.

Inputs:
- data/batch_analysis.json (gap data from prior batch run)
- Original SWMS source files in data/swms_input/

Outputs:
- data/gap_severity.json
- data/sequence_analysis.json
- data/hrcw_analysis.json
- data/overnight_report.txt
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import anthropic

from core.document_extractor import extract_text
from core.utils import extract_json


GAP_SYSTEM_PROMPT = """You are a NSW WHS compliance expert.
Classify each gap as one of:
  hard_fail — legally required, missing = imminent risk or regulatory breach
  structural — operationally important, missing = significant safety gap
  administrative — documentation gap, missing = minor non-conformance

Return JSON array only:
[{
  "gap": "original gap text",
  "severity": "hard_fail|structural|administrative",
  "reason": "one sentence why"
}]"""


SEQUENCE_SYSTEM_PROMPT = (
    "You are a NSW WHS compliance expert reviewing a Safe Work Method "
    "Statement for task sequence quality."
)


SEQUENCE_USER_PROMPT_TEMPLATE = """Review this SWMS for task sequencing.
Answer these questions:

1. Does the document contain numbered or ordered task steps? YES/NO
2. Is there a pre-start briefing or induction step before work begins? YES/NO
3. Is there a permit or isolation gate before hazardous work? YES/NO
4. Is there a post-work inspection or sign-off gate? YES/NO
5. Are any steps truncated or incomplete? YES/NO
6. Sequence verdict: PASS/FAIL/PARTIAL
7. One sentence summary of the sequence quality.

Return JSON only:
{
  "has_task_sequence": true/false,
  "has_prestart": true/false,
  "has_permit_gate": true/false,
  "has_postwork_gate": true/false,
  "has_truncated_steps": true/false,
  "sequence_verdict": "PASS/FAIL/PARTIAL",
  "summary": "..."
}

SWMS TEXT:
<<SWMS_TEXT>>
"""


HRCW_SYSTEM_PROMPT = "You are a NSW WHS compliance expert."


HRCW_USER_PROMPT_TEMPLATE = """Based on this SWMS work scope, list:
1. HRCW categories that SHOULD be selected based on the work described
2. HRCW categories that ARE selected in the document
3. HRCW categories that are MISSING

Use exact WHS Reg 2017 Schedule 3 category names.

Return JSON only:
{
  "should_be_selected": ["..."],
  "are_selected": ["..."],
  "missing": ["..."],
  "hrcw_verdict": "COMPLETE/INCOMPLETE/UNKNOWN"
}

SWMS TEXT:
<<SWMS_TEXT>>
"""


RETRO_HEADLINE_SYSTEM_PROMPT = (
    "You are a NSW WHS compliance advisor writing a concise executive update."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run overnight SWMS retro-audit analyses.")
    parser.add_argument(
        "--batch-file",
        default="data/batch_analysis.json",
        help="Path to batch analysis JSON input.",
    )
    parser.add_argument(
        "--input-folder",
        default="data/swms_input",
        help="Folder containing original SWMS source files.",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for analysis results.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds delay between Anthropic API calls.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional document limit for smoke testing.",
    )
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_batch(batch_path: Path) -> list[dict[str, Any]]:
    data = json.loads(batch_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("batch_analysis.json must contain a JSON array.")
    return data


def get_client() -> anthropic.Anthropic:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set in environment/.env.")
    return anthropic.Anthropic(api_key=api_key)


def find_source_path(entry: dict[str, Any], input_folder: Path) -> Path | None:
    rel = entry.get("relative_path")
    if isinstance(rel, str) and rel:
        rel_path = Path(rel)
        if rel_path.exists():
            return rel_path

    filename = str(entry.get("filename", "")).strip()
    if not filename:
        return None

    direct = input_folder / filename
    if direct.exists():
        return direct

    for candidate in input_folder.rglob(filename):
        if candidate.is_file():
            return candidate
    return None


def call_model_json(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-haiku-4-5",
    max_tokens: int = 1800,
) -> Any:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text if response.content else ""
    return extract_json(text)


def classify_gap_severity(
    client: anthropic.Anthropic,
    filename: str,
    gaps: list[str],
) -> dict[str, Any]:
    if not gaps:
        return {
            "filename": filename,
            "gaps_classified": [],
            "hard_fail_count": 0,
            "structural_count": 0,
            "administrative_count": 0,
            "error": None,
            "processed_at": now_utc(),
        }

    payload = json.dumps(gaps, ensure_ascii=True)
    result = call_model_json(client, GAP_SYSTEM_PROMPT, payload, max_tokens=2400)
    if not isinstance(result, list):
        raise ValueError("Gap classification response was not a JSON array.")

    normalized: list[dict[str, str]] = []
    for row in result:
        if not isinstance(row, dict):
            continue
        gap = str(row.get("gap", "")).strip()
        severity = str(row.get("severity", "")).strip().lower()
        reason = str(row.get("reason", "")).strip()
        if severity not in {"hard_fail", "structural", "administrative"}:
            severity = "administrative"
        normalized.append({"gap": gap, "severity": severity, "reason": reason})

    counts = Counter(item["severity"] for item in normalized)
    return {
        "filename": filename,
        "gaps_classified": normalized,
        "hard_fail_count": counts.get("hard_fail", 0),
        "structural_count": counts.get("structural", 0),
        "administrative_count": counts.get("administrative", 0),
        "error": None,
        "processed_at": now_utc(),
    }


def analyse_sequence(
    client: anthropic.Anthropic,
    filename: str,
    text: str,
) -> dict[str, Any]:
    prompt = SEQUENCE_USER_PROMPT_TEMPLATE.replace("<<SWMS_TEXT>>", text[:30000])
    result = call_model_json(client, SEQUENCE_SYSTEM_PROMPT, prompt, max_tokens=1800)
    if not isinstance(result, dict):
        raise ValueError("Sequence analysis response was not a JSON object.")

    verdict = str(result.get("sequence_verdict", "UNKNOWN")).upper()
    if verdict not in {"PASS", "FAIL", "PARTIAL"}:
        verdict = "PARTIAL"

    return {
        "filename": filename,
        "has_task_sequence": bool(result.get("has_task_sequence", False)),
        "has_prestart": bool(result.get("has_prestart", False)),
        "has_permit_gate": bool(result.get("has_permit_gate", False)),
        "has_postwork_gate": bool(result.get("has_postwork_gate", False)),
        "has_truncated_steps": bool(result.get("has_truncated_steps", False)),
        "sequence_verdict": verdict,
        "summary": str(result.get("summary", "")).strip(),
        "error": None,
        "processed_at": now_utc(),
    }


def analyse_hrcw(
    client: anthropic.Anthropic,
    filename: str,
    text: str,
) -> dict[str, Any]:
    prompt = HRCW_USER_PROMPT_TEMPLATE.replace("<<SWMS_TEXT>>", text[:30000])
    result = call_model_json(client, HRCW_SYSTEM_PROMPT, prompt, max_tokens=2000)
    if not isinstance(result, dict):
        raise ValueError("HRCW analysis response was not a JSON object.")

    verdict = str(result.get("hrcw_verdict", "UNKNOWN")).upper()
    if verdict not in {"COMPLETE", "INCOMPLETE", "UNKNOWN"}:
        verdict = "UNKNOWN"

    return {
        "filename": filename,
        "should_be_selected": result.get("should_be_selected", []),
        "are_selected": result.get("are_selected", []),
        "missing": result.get("missing", []),
        "hrcw_verdict": verdict,
        "error": None,
        "processed_at": now_utc(),
    }


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def generate_headline(
    client: anthropic.Anthropic,
    summary_payload: dict[str, Any],
) -> str:
    user_prompt = (
        "Write exactly 3 plain-English sentences for a Principal Contractor Head of "
        "Safety. Cover: what the data shows, what risk it implies, and what Safe "
        "Method would have caught.\n\n"
        f"SUMMARY DATA:\n{json.dumps(summary_payload, ensure_ascii=True, indent=2)}"
    )
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=220,
            system=RETRO_HEADLINE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text if response.content else ""
        return " ".join(text.strip().split())
    except Exception as exc:
        return (
            "The overnight sample shows repeated compliance gaps across legal, structural, "
            f"and administrative controls ({exc}). This indicates latent WHS risk where "
            "critical controls may be undocumented or inconsistently sequenced. Safe Method "
            "would have surfaced these omissions early as actionable gaps before site issue."
        )


def write_report(
    report_path: Path,
    document_count: int,
    gap_results: list[dict[str, Any]],
    sequence_results: list[dict[str, Any]],
    hrcw_results: list[dict[str, Any]],
    headline: str,
) -> None:
    hard_fails = sum(int(r.get("hard_fail_count", 0)) for r in gap_results)
    structural = sum(int(r.get("structural_count", 0)) for r in gap_results)
    admin = sum(int(r.get("administrative_count", 0)) for r in gap_results)
    total_gaps = hard_fails + structural + admin

    hard_fail_counter: Counter[str] = Counter()
    for doc in gap_results:
        for row in doc.get("gaps_classified", []):
            if isinstance(row, dict) and row.get("severity") == "hard_fail":
                hard_fail_counter[str(row.get("gap", "")).strip()] += 1
    top_hard_fails = hard_fail_counter.most_common(5)

    no_sequence = sum(1 for r in sequence_results if not r.get("has_task_sequence", False))
    no_prestart = sum(1 for r in sequence_results if not r.get("has_prestart", False))
    no_permit = sum(1 for r in sequence_results if not r.get("has_permit_gate", False))
    truncated = sum(1 for r in sequence_results if r.get("has_truncated_steps", False))
    verdict_counts = Counter(str(r.get("sequence_verdict", "PARTIAL")).upper() for r in sequence_results)

    incomplete_hrcw = sum(1 for r in hrcw_results if str(r.get("hrcw_verdict", "")).upper() == "INCOMPLETE")
    missing_counter: Counter[str] = Counter()
    for r in hrcw_results:
        missing = r.get("missing", [])
        if isinstance(missing, list):
            for item in missing:
                missing_counter[str(item).strip()] += 1
    most_missing = missing_counter.most_common(1)[0][0] if missing_counter else "None identified"

    def pct(val: int) -> float:
        return (val / total_gaps * 100.0) if total_gaps else 0.0

    lines: list[str] = []
    lines.append("=== SAFE METHOD OVERNIGHT ANALYSIS ===")
    lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Documents analysed: {document_count}")
    lines.append("")
    lines.append("--- GAP SEVERITY SUMMARY ---")
    lines.append(f"Total gaps classified: {total_gaps}")
    lines.append(f"Hard fails: {hard_fails} ({pct(hard_fails):.1f}%)")
    lines.append(f"Structural: {structural} ({pct(structural):.1f}%)")
    lines.append(f"Administrative: {admin} ({pct(admin):.1f}%)")
    lines.append("")
    lines.append("Top 5 hard fails:")
    if top_hard_fails:
        for i, (gap_text, _) in enumerate(top_hard_fails, start=1):
            lines.append(f"{i}. {gap_text}")
    else:
        for i in range(1, 6):
            lines.append(f"{i}. None")
    lines.append("")
    lines.append("--- SEQUENCE ANALYSIS SUMMARY ---")
    lines.append(f"Documents with no task sequence: {no_sequence}/{document_count}")
    lines.append(f"Documents with no pre-start gate: {no_prestart}/{document_count}")
    lines.append(f"Documents with no permit gate: {no_permit}/{document_count}")
    lines.append(f"Documents with truncated steps: {truncated}/{document_count}")
    lines.append("Overall sequence verdict:")
    lines.append(
        f"  PASS: {verdict_counts.get('PASS', 0)}  "
        f"PARTIAL: {verdict_counts.get('PARTIAL', 0)}  "
        f"FAIL: {verdict_counts.get('FAIL', 0)}"
    )
    lines.append("")
    lines.append("--- HRCW COMPLETENESS SUMMARY ---")
    lines.append(f"Documents with incomplete HRCW: {incomplete_hrcw}/{document_count}")
    lines.append(f"Most commonly missing category: {most_missing}")
    lines.append("")
    lines.append("--- RETRO-AUDIT HEADLINE ---")
    lines.append(headline)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    batch_path = Path(args.batch_file).expanduser().resolve()
    input_folder = Path(args.input_folder).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    gap_out = output_dir / "gap_severity.json"
    sequence_out = output_dir / "sequence_analysis.json"
    hrcw_out = output_dir / "hrcw_analysis.json"
    report_out = output_dir / "overnight_report.txt"

    print(f"[INFO] Loading batch input: {batch_path}")
    docs = load_batch(batch_path)
    if args.limit and args.limit > 0:
        docs = docs[: args.limit]
        print(f"[INFO] Limit applied: {len(docs)} document(s)")
    else:
        print(f"[INFO] Documents loaded: {len(docs)}")

    client = get_client()
    delay = max(float(args.delay), 0.0)

    gap_results: list[dict[str, Any]] = []
    sequence_results: list[dict[str, Any]] = []
    hrcw_results: list[dict[str, Any]] = []
    text_cache: dict[str, str] = {}

    for idx, doc in enumerate(docs, start=1):
        filename = str(doc.get("filename", f"document_{idx}"))
        print(f"[{idx}/{len(docs)}] GAP severity: {filename}")
        try:
            gaps = doc.get("gaps", [])
            if not isinstance(gaps, list):
                gaps = []
            gap_result = classify_gap_severity(client, filename, gaps)
        except Exception as exc:
            gap_result = {
                "filename": filename,
                "gaps_classified": [],
                "hard_fail_count": 0,
                "structural_count": 0,
                "administrative_count": 0,
                "error": str(exc),
                "processed_at": now_utc(),
            }
            print(f"  [WARN] Gap severity failed: {exc}")
        gap_results.append(gap_result)
        save_json(gap_out, gap_results)
        time.sleep(delay)

        print(f"[{idx}/{len(docs)}] Extract text: {filename}")
        source_path = find_source_path(doc, input_folder)
        if source_path is None:
            text_err = f"Source file not found under {input_folder}"
            print(f"  [WARN] {text_err}")
            seq_result = {
                "filename": filename,
                "has_task_sequence": False,
                "has_prestart": False,
                "has_permit_gate": False,
                "has_postwork_gate": False,
                "has_truncated_steps": False,
                "sequence_verdict": "PARTIAL",
                "summary": "",
                "error": text_err,
                "processed_at": now_utc(),
            }
            h_result = {
                "filename": filename,
                "should_be_selected": [],
                "are_selected": [],
                "missing": [],
                "hrcw_verdict": "UNKNOWN",
                "error": text_err,
                "processed_at": now_utc(),
            }
            sequence_results.append(seq_result)
            hrcw_results.append(h_result)
            save_json(sequence_out, sequence_results)
            save_json(hrcw_out, hrcw_results)
            continue

        try:
            file_bytes = source_path.read_bytes()
            extracted_text = extract_text(file_bytes, source_path.name)
            text_cache[filename] = extracted_text
            print(f"  [OK] Extracted chars: {len(extracted_text)}")
        except Exception as exc:
            text_err = f"Text extraction failed: {exc}"
            print(f"  [WARN] {text_err}")
            seq_result = {
                "filename": filename,
                "has_task_sequence": False,
                "has_prestart": False,
                "has_permit_gate": False,
                "has_postwork_gate": False,
                "has_truncated_steps": False,
                "sequence_verdict": "PARTIAL",
                "summary": "",
                "error": text_err,
                "processed_at": now_utc(),
            }
            h_result = {
                "filename": filename,
                "should_be_selected": [],
                "are_selected": [],
                "missing": [],
                "hrcw_verdict": "UNKNOWN",
                "error": text_err,
                "processed_at": now_utc(),
            }
            sequence_results.append(seq_result)
            hrcw_results.append(h_result)
            save_json(sequence_out, sequence_results)
            save_json(hrcw_out, hrcw_results)
            continue

        print(f"[{idx}/{len(docs)}] Sequence analysis: {filename}")
        try:
            seq_result = analyse_sequence(client, filename, extracted_text)
        except Exception as exc:
            seq_result = {
                "filename": filename,
                "has_task_sequence": False,
                "has_prestart": False,
                "has_permit_gate": False,
                "has_postwork_gate": False,
                "has_truncated_steps": False,
                "sequence_verdict": "PARTIAL",
                "summary": "",
                "error": str(exc),
                "processed_at": now_utc(),
            }
            print(f"  [WARN] Sequence analysis failed: {exc}")
        sequence_results.append(seq_result)
        save_json(sequence_out, sequence_results)
        time.sleep(delay)

        print(f"[{idx}/{len(docs)}] HRCW completeness: {filename}")
        try:
            h_result = analyse_hrcw(client, filename, extracted_text)
        except Exception as exc:
            h_result = {
                "filename": filename,
                "should_be_selected": [],
                "are_selected": [],
                "missing": [],
                "hrcw_verdict": "UNKNOWN",
                "error": str(exc),
                "processed_at": now_utc(),
            }
            print(f"  [WARN] HRCW analysis failed: {exc}")
        hrcw_results.append(h_result)
        save_json(hrcw_out, hrcw_results)
        time.sleep(delay)

    headline_context = {
        "documents_analysed": len(docs),
        "gap_summary": {
            "hard_fail": sum(int(r.get("hard_fail_count", 0)) for r in gap_results),
            "structural": sum(int(r.get("structural_count", 0)) for r in gap_results),
            "administrative": sum(int(r.get("administrative_count", 0)) for r in gap_results),
        },
        "sequence_verdicts": Counter(
            str(r.get("sequence_verdict", "PARTIAL")).upper() for r in sequence_results
        ),
        "incomplete_hrcw_docs": sum(
            1 for r in hrcw_results if str(r.get("hrcw_verdict", "")).upper() == "INCOMPLETE"
        ),
    }
    headline = generate_headline(client, headline_context)

    write_report(
        report_out,
        document_count=len(docs),
        gap_results=gap_results,
        sequence_results=sequence_results,
        hrcw_results=hrcw_results,
        headline=headline,
    )

    print("[DONE] Analysis outputs:")
    print(f"  - {gap_out}")
    print(f"  - {sequence_out}")
    print(f"  - {hrcw_out}")
    print(f"  - {report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
