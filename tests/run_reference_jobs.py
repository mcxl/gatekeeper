#!/usr/bin/env python3
"""
tests/run_reference_jobs.py
Run all reference jobs through the inference matrix and report
pass/fail against each job's checklist.

Usage:
    python tests/run_reference_jobs.py
    python tests/run_reference_jobs.py --job 01_tiltup
    python tests/run_reference_jobs.py --verbose

Does NOT call the Claude API -inference matrix only (milliseconds).
Use this after any change to inference_matrix.py, decomposer.py,
or control_writer.py to verify nothing silently broke.
"""

import sys
import os
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.inference_matrix import infer_to_dict

FIXTURES_DIR = Path(__file__).parent / "reference_jobs"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"


def check_job(job: dict, verbose: bool = False) -> dict:
    """Run a single reference job through inference and check results."""
    description = job["description"]
    jurisdiction = job.get("jurisdiction", "AU")
    checklist = job["checklist"]

    inference = infer_to_dict(description, jurisdiction=jurisdiction)

    failures = []
    warnings = []
    passes = []

    # HRCW must match
    if checklist.get("hrcw") is not None:
        if inference.get("hrcw") == checklist["hrcw"]:
            passes.append("hrcw flag correct")
        else:
            failures.append(
                f"hrcw: expected {checklist['hrcw']}, "
                f"got {inference.get('hrcw')}"
            )

    # HRCW flags that must be present
    hrcw_flags = inference.get("hrcw_flags", {})
    for flag in checklist.get("hrcw_flags_must_include", []):
        if hrcw_flags.get(flag):
            passes.append(f"hrcw_flag '{flag}' present")
        else:
            failures.append(f"hrcw_flag '{flag}' missing -"
                          f"got flags: {[k for k,v in hrcw_flags.items() if v]}")

    # HRCW flags that must NOT be present
    for flag in checklist.get("hrcw_flags_must_exclude", []):
        if not hrcw_flags.get(flag):
            passes.append(f"hrcw_flag '{flag}' correctly absent")
        else:
            failures.append(f"hrcw_flag '{flag}' should not be set")

    # PPE items that must appear (case-insensitive substring match)
    ppe_text = " ".join(inference.get("ppe", [])).lower()
    for item in checklist.get("ppe_must_include", []):
        if item.lower() in ppe_text:
            passes.append(f"ppe includes '{item}'")
        else:
            warnings.append(f"ppe missing '{item}'")

    # Certifications that must appear
    certs_text = " ".join(inference.get("certifications", [])).lower()
    for item in checklist.get("certs_must_include", []):
        if item.lower() in certs_text:
            passes.append(f"cert includes '{item}'")
        else:
            warnings.append(f"cert missing '{item}'")

    # Permits that must appear
    permits_text = " ".join(inference.get("permits", [])).lower()
    for item in checklist.get("permits_must_include", []):
        if item.lower() in permits_text:
            passes.append(f"permit includes '{item}'")
        else:
            warnings.append(f"permit missing '{item}'")

    # Notes that must appear
    notes_text = " ".join(inference.get("regulatory_notes", [])).lower()
    for item in checklist.get("notes_must_include", []):
        if item.lower() in notes_text:
            passes.append(f"notes include '{item}'")
        else:
            warnings.append(f"notes missing '{item}'")

    # Forbidden strings must not appear anywhere in inference output
    full_text = json.dumps(inference).lower()
    for item in checklist.get("forbidden_strings_anywhere", []):
        if item.lower() in full_text:
            failures.append(f"forbidden string found: '{item}'")
        else:
            passes.append(f"forbidden string absent: '{item}'")

    return {
        "id": job["id"],
        "name": job["name"],
        "passes": passes,
        "warnings": warnings,
        "failures": failures,
        "passed": len(failures) == 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run reference jobs through inference matrix"
    )
    parser.add_argument("--job", help="Run a single job by id")
    parser.add_argument("--verbose", action="store_true",
                        help="Show all pass results too")
    args = parser.parse_args()

    job_files = sorted(FIXTURES_DIR.glob("*.json"))
    if args.job:
        job_files = [f for f in job_files if args.job in f.stem]
        if not job_files:
            print(f"No job found matching: {args.job}")
            sys.exit(1)

    if not job_files:
        print(f"No reference job files found in {FIXTURES_DIR}")
        sys.exit(1)

    total = 0
    passed = 0
    failed = 0

    print(f"\nGatekeeper Reference Job Checker")
    print(f"{'=' * 50}")

    for job_file in job_files:
        with open(job_file) as f:
            job = json.load(f)

        result = check_job(job, verbose=args.verbose)
        total += 1

        status = PASS if result["passed"] else FAIL
        print(f"\n{status} {result['id']} -{result['name']}")

        if result["failures"]:
            failed += 1
            for failure in result["failures"]:
                print(f"    {FAIL} {failure}")
        else:
            passed += 1

        if result["warnings"]:
            for warning in result["warnings"]:
                print(f"    {WARN} {warning}")

        if args.verbose and result["passes"]:
            for p in result["passes"]:
                print(f"    {PASS} {p}")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} passed, "
          f"{failed} failed\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
