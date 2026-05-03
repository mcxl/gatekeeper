#!/usr/bin/env python3
"""
Batch SWMS gap analysis runner.

Processes PDF/DOCX files recursively, posts each file to /upload/swms-gap,
and persists incremental results to JSONL plus rolling JSON array output.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

try:
    from core.document_extractor import extract_text as extract_document_text
except Exception:
    extract_document_text = None


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch SWMS gap analysis.")
    parser.add_argument("--folder", required=True, help="Path to input SWMS folder.")
    parser.add_argument("--output", required=True, help="Path to JSON output file.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for API endpoint (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3,
        help="Seconds delay between requests (default: 3).",
    )
    return parser.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_files(folder: Path) -> list[Path]:
    files = [
        p
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=lambda p: str(p).lower())


def determine_confidence_tier(score: float) -> str:
    if score > 0.8:
        return "green"
    if score >= 0.5:
        return "amber"
    return "red"


def estimate_pages(path: Path, size_bytes: int) -> int:
    if path.suffix.lower() == ".pdf":
        return max(1, math.ceil(size_bytes / (50 * 1024)))
    return max(1, math.ceil(size_bytes / (80 * 1024)))


def count_chars_if_possible(file_bytes: bytes, filename: str) -> int | None:
    if extract_document_text is None:
        return None
    try:
        text = extract_document_text(file_bytes, filename)
        return len(text or "")
    except Exception:
        return None


def write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=True) + "\n")


def process_file(
    client: httpx.Client,
    base_url: str,
    file_path: Path,
) -> dict[str, Any]:
    processed_at = now_utc_iso()
    file_bytes = file_path.read_bytes()
    file_size_bytes = file_path.stat().st_size
    estimated_pages = estimate_pages(file_path, file_size_bytes)
    extracted_char_count = count_chars_if_possible(file_bytes, file_path.name)

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    endpoint = f"{base_url.rstrip('/')}/upload/swms-gap"

    result: dict[str, Any] = {
        "filename": file_path.name,
        "relative_path": str(file_path),
        "file_size_bytes": file_size_bytes,
        "estimated_pages": estimated_pages,
        "extracted_char_count": extracted_char_count,
        "confidence_tier": "red",
        "confidence_score": 0.0,
        "gap_count": 0,
        "matched_count": 0,
        "gaps": [],
        "matched": [],
        "error": None,
        "processed_at": processed_at,
    }

    try:
        response = client.post(
            endpoint,
            files={"file": (file_path.name, file_bytes, mime_type)},
        )
        response.raise_for_status()
        payload = response.json()

        gaps = payload.get("gaps") or []
        matched = payload.get("matched") or []
        confidence_raw = payload.get("confidence", 0.0)
        try:
            confidence_score = float(confidence_raw)
        except (TypeError, ValueError):
            confidence_score = 0.0

        result["confidence_score"] = confidence_score
        result["confidence_tier"] = determine_confidence_tier(confidence_score)
        result["gap_count"] = len(gaps) if isinstance(gaps, list) else 0
        result["matched_count"] = len(matched) if isinstance(matched, list) else 0
        result["gaps"] = gaps if isinstance(gaps, list) else []
        result["matched"] = matched if isinstance(matched, list) else []
    except Exception as exc:
        result["error"] = str(exc)

    return result


def print_summary(results: list[dict[str, Any]], output_path: Path) -> None:
    total = len(results)
    green = sum(1 for r in results if r.get("confidence_tier") == "green")
    amber = sum(1 for r in results if r.get("confidence_tier") == "amber")
    red = sum(1 for r in results if r.get("confidence_tier") == "red")
    errors = sum(1 for r in results if r.get("error"))
    avg_gaps = (
        sum(float(r.get("gap_count", 0)) for r in results) / total if total else 0.0
    )

    print("=== BATCH COMPLETE ===")
    print(f"Total: {total}")
    print(f"Green: {green}  Amber: {amber}  Red: {red}")
    print(f"Avg gaps: {avg_gaps:.1f}")
    print(f"Errors: {errors}")
    print(f"Results: {output_path}")


def main() -> int:
    args = parse_args()

    input_folder = Path(args.folder).expanduser().resolve()
    output_json = Path(args.output).expanduser().resolve()
    output_jsonl = output_json.with_suffix(".jsonl")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.write_text("", encoding="utf-8")

    if not input_folder.exists():
        print(f"Input folder not found: {input_folder}")
        write_json(output_json, [])
        print_summary([], output_json)
        return 1

    files = discover_files(input_folder)
    total = len(files)
    results: list[dict[str, Any]] = []

    if total == 0:
        print(f"No .pdf or .docx files found in: {input_folder}")
        write_json(output_json, results)
        print_summary(results, output_json)
        return 0

    with httpx.Client(timeout=120.0) as client:
        for idx, file_path in enumerate(files, start=1):
            print(f"Processing {idx}/{total}: {file_path.name}")
            result = process_file(client, args.base_url, file_path)
            results.append(result)

            print(
                f"  Confidence: {result['confidence_tier']} "
                f"({result['confidence_score']:.2f})"
            )
            print(
                f"  Gaps: {result['gap_count']}  "
                f"Matched: {result['matched_count']}"
            )
            if result.get("error"):
                print(f"  Error: {result['error']}")

            append_jsonl(output_jsonl, result)
            write_json(output_json, results)

            if idx < total and args.delay > 0:
                time.sleep(args.delay)

    write_json(output_json, results)
    print_summary(results, output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

