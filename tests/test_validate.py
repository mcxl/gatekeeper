"""
Tests for core/validate.py — 12-check SWMS validation engine.

Each test targets a specific check. Numbered to match check order.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import TaskBlock
from core.validate import score_task, WAH_SENTENCE


# ============================================================
# HELPERS
# ============================================================

def _make_task(**kwargs) -> TaskBlock:
    """Minimal valid TaskBlock with clean defaults that pass all checks."""
    defaults = dict(
        task="Test Task",
        scope="Test scope description",
        risk_pre="Medium-4",
        risk_post="Low-1",
        responsibility={"SUP": "Oversee task execution"},
        controls=[
            "Inspect area before starting work",
            "Wear correct PPE at all times",
            "Remove debris from work zone",
        ],
        hold_points=[
            "Verify setup is complete",
            "Confirm crew has been briefed",
        ],
        stop_work=[
            "Stop if conditions change",
            "Stop if equipment fails",
        ],
        ppe=["Wear hard hat and boots"],
        admin=[],
    )
    defaults.update(kwargs)
    return TaskBlock(**defaults)


# ============================================================
# CHECK 2 — CCVS INTEGRITY
# ============================================================

def test_ccvs_bleed():
    """Bullet containing bare hazard family code 'WAH' in controls → fails check 2."""
    task = _make_task(controls=[
        "WAH verification required for this task",
        "Inspect area before starting work",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert not result.passed
    assert any("Check 2" in e and "WAH" in e for e in result.errors)


def test_ccvs_hyphenated_code_ok():
    """Hyphenated CCVS code 'WAH-H6' in controls is NOT flagged (it's a valid reference)."""
    task = _make_task(controls=[
        "WAH-H6 verification required for this task",
        "Inspect area before starting work",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert not any("Check 2" in e and "WAH" in e for e in result.errors)


# ============================================================
# CHECK 4 — WAH RULE
# ============================================================

def test_wah_missing():
    """wah_applicable True but controls[0] is not the canonical WAH sentence → fails check 4."""
    task = _make_task(
        wah_applicable=True,
        controls=[
            "Wear harness when working at height",
            "Inspect anchor points before use",
            "Remove debris from work zone",
        ],
    )
    result = score_task(task)
    assert not result.passed
    assert any("Check 4" in e for e in result.errors)


# ============================================================
# CHECK 5 — ONE-CONTROL RULE
# ============================================================

def test_stacked_control():
    """Bullet with ' — ' separating two items → warning on check 5."""
    task = _make_task(controls=[
        "Inspect area before starting work",
        "Wear correct PPE — Ensure harness is fitted",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert any("Check 5" in w for w in result.warnings)


# ============================================================
# CHECK 6 — WORD CAP
# ============================================================

def test_word_cap():
    """19-word bullet → hard fail on check 6."""
    long_bullet = (
        "Inspect the scaffold structure and verify that all "
        "connections are secure and all guardrails are in position "
        "before allowing any workers to access the platform area"
    )
    words = long_bullet.split()
    assert len(words) > 18, f"Bullet only has {len(words)} words — adjust test"
    task = _make_task(controls=[
        long_bullet,
        "Wear correct PPE at all times",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert not result.passed
    assert any("Check 6" in e for e in result.errors)


# ============================================================
# CHECK 7 — COMMA / SEMICOLON
# ============================================================

def test_semicolon():
    """Bullet containing semicolon → hard fail on check 7."""
    task = _make_task(controls=[
        "Inspect area; confirm clear before starting",
        "Wear correct PPE at all times",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert not result.passed
    assert any("Check 7" in e for e in result.errors)


# ============================================================
# CHECK 8 — VERB-FIRST
# ============================================================

def test_verb_first():
    """Bullet starting with 'The' (not in approved verbs) → warning on check 8."""
    task = _make_task(controls=[
        "The area must be inspected before starting",
        "Wear correct PPE at all times",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert any("Check 8" in w and "The" in w for w in result.warnings)


# ============================================================
# CHECK 9 — PER-BULLET FOG
# ============================================================

def test_fog_per_bullet():
    """High-complexity bullet with Fog > 14 → hard fail on check 9."""
    # 9 words, 7 with 3+ syllables → Fog ≈ 34.7 (well above 14)
    complex_bullet = (
        "Verify electrochemical deterioration methodology documentation "
        "comprehensively for infrastructure remediation processes"
    )
    task = _make_task(controls=[
        complex_bullet,
        "Wear correct PPE at all times",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert not result.passed
    assert any("Check 9" in e for e in result.errors)


# ============================================================
# CHECK 10 — VOCABULARY CHECK
# ============================================================

def test_banned_word():
    """Bullet containing 'prior to' → warning on check 10."""
    task = _make_task(controls=[
        "Inspect site prior to starting work",
        "Wear correct PPE at all times",
        "Remove debris from work zone",
    ])
    result = score_task(task)
    assert any("Check 10" in w and "prior to" in w for w in result.warnings)


# ============================================================
# CHECK 11 — SECTION COUNT
# ============================================================

def test_section_too_large():
    """26 controls → hard fail on check 11."""
    many_controls = [f"Inspect item number {i} before use" for i in range(26)]
    task = _make_task(controls=many_controls)
    result = score_task(task)
    assert not result.passed
    assert any("Check 11" in e and "controls" in e for e in result.errors)


# ============================================================
# CHECK 12 — RESPONSIBILITY LENGTH
# ============================================================

def test_responsibility_length():
    """11-word obligation in responsibility → warning on check 12."""
    task = _make_task(
        responsibility={"SUP": "Oversee work and ensure all safety controls are applied correctly here"}
    )
    result = score_task(task)
    assert any("Check 12" in w and "SUP" in w for w in result.warnings)


# ============================================================
# WAH EXEMPTION
# ============================================================

def test_wah_exempt():
    """WAH sentence in controls[0] passes all bullet-level checks."""
    task = _make_task(
        wah_applicable=True,
        controls=[
            WAH_SENTENCE,
            "Inspect harness before each use",
            "Wear hard hat at all times",
        ],
    )
    result = score_task(task)
    # Check 4 must pass — sentence matches
    assert not any("Check 4" in e for e in result.errors)
    # WAH sentence must not trigger word cap (it is > 18 words)
    wah_preview = WAH_SENTENCE[:60]
    assert not any(wah_preview in e for e in result.errors)
    # Overall: no errors at all from the WAH sentence
    assert result.passed, f"Expected pass. Errors: {result.errors}"


# ============================================================
# FULL PASS
# ============================================================

def test_full_pass():
    """Clean TaskBlock with all fields correct → passes all 12 checks, no errors."""
    task = TaskBlock(
        task="Facade Repair Works",
        scope="Spalling concrete repair on levels 3–5 east elevation",
        risk_pre="Medium-4",
        risk_post="Low-1",
        hold_points=[
            "Verify scaffold is erected and tagged",
            "Confirm engineer has reviewed repair extent",
        ],
        controls=[
            "Inspect scaffold before each shift start",
            "Wear harness and attach to anchor point",
            "Remove loose concrete before applying repair",
        ],
        stop_work=[
            "Stop if wind speed exceeds safe limit",
            "Stop if scaffold is damaged or unsecured",
        ],
        admin=[],
        ppe=["Wear hard hat and steel-capped boots"],
        responsibility={"SUP": "Supervise all facade repair works"},
        wah_applicable=False,
    )
    result = score_task(task)
    assert result.passed, f"Expected full pass. Errors: {result.errors}"
    assert result.errors == []


# ============================================================
# CHECK 11 — SECTION COUNT (targeted boundary tests)
# T5 additions
# ============================================================

def test_check11_passes_at_6():
    """6 controls is within the hard limit — no Check 11 error."""
    task = _make_task(controls=[f"Inspect item number {i} before use" for i in range(6)])
    result = score_task(task)
    assert not any("Check 11" in e and "controls" in e for e in result.errors), (
        f"Unexpected Check 11 error at 6 controls: {result.errors}"
    )


def test_check11_warns_at_7():
    """7 controls exceeds the lean standard (6) — Check 11 warning issued."""
    task = _make_task(controls=[f"Inspect item number {i} before use" for i in range(7)])
    result = score_task(task)
    assert any("Check 11" in w and "controls" in w for w in result.warnings), (
        f"Expected Check 11 warning at 7 controls. Warnings: {result.warnings}"
    )


def test_check11_errors_at_9():
    """9 controls exceeds the hard limit (8) — Check 11 error raised."""
    task = _make_task(controls=[f"Inspect item number {i} before use" for i in range(9)])
    result = score_task(task)
    assert not result.passed
    assert any("Check 11" in e and "controls" in e for e in result.errors), (
        f"Expected Check 11 error at 9 controls. Errors: {result.errors}"
    )


def test_check11_regression_25_must_fail():
    """Regression: 25 controls (original test case) must still fail Check 11."""
    task = _make_task(controls=[f"Inspect item number {i} before use" for i in range(25)])
    result = score_task(task)
    assert not result.passed
    assert any("Check 11" in e and "controls" in e for e in result.errors), (
        f"Regression: 25 controls must fail Check 11. Errors: {result.errors}"
    )
