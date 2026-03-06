#!/usr/bin/env python3
"""
Gatekeeper SWMS Validation Engine

12-check readability and integrity guardrail suite.
Checks run in order 1–12. Hard fails block generation.
Warnings are logged but do not block.

Entry point: score_task(task: TaskBlock) -> ValidationResult
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.schema import TaskBlock, ValidationResult

# ============================================================
# CONSTANTS — single source of truth used by validate.py and generate.py
# ============================================================

WAH_SENTENCE = (
    "If this task involves elevated work or exposure to an "
    "unprotected edge (> 1.5 m), comply with the relevant WAH "
    "(High-6) controls and HOLD POINTS for the selected access "
    "method (Ladder / Scaffold / EWP / Industrial Rope Access), "
    "including edge protection/fall prevention, exclusion/drop "
    "zones to full fall-line, and rescue arrangements per "
    "Emergency Response."
)

# Taxonomy v2.0 — hazard families (used for embedded-code detection in bullet text)
HAZARD_FAMILIES = [
    "WAH", "IRA", "ELE", "SIL", "STR", "CFS", "ENE",
    "HOT", "MOB", "ASB", "LED", "TRF", "ENV", "CHM", "SYS"
]

# Taxonomy v2.0 — approved full CCVS codes (used to validate ccvs_code field)
APPROVED_CCVS_CODES = [
    "WAH-H6", "WAH-H9",
    "IRA-H6", "IRA-H9",
    "ELE-M4", "ELE-H6",
    "SIL-H6", "SIL-H9",
    "STR-H6", "STR-H9",
    "CFS-H9",
    "ENE-M4", "ENE-H6",
    "HOT-M4", "HOT-H6",
    "MOB-M4", "MOB-H6",
    "ASB-H6", "ASB-H9",
    "LED-H6",
    "CHM-M3", "CHM-H6",
    "TRF-M4", "TRF-H6",
    "SYS-L1", "SYS-L2", "SYS-M3", "SYS-M4", "SYS-H6", "SYS-H9"
]

# Banned vocabulary — phrase: suggested substitution (None = warn without fix)
BANNED_WORDS = {
    "prior to": "before",
    "commencing": "starting",
    "utilised": "used",
    "conducted": "carried out",
    "in accordance with": "per",
    "personnel": "workers",
    "established": None,
}

APPROVED_VERBS = {
    "Verify", "Install", "Inspect", "Barricade", "Record", "Tag-out",
    "Check", "Confirm", "Ensure", "Remove", "Isolate", "Test", "Brief",
    "Establish", "Complete", "Maintain", "Wear", "Use", "Apply", "Stop",
    "Notify", "Review", "Secure", "Mark", "Restrict", "Monitor", "Attach",
    "Position", "Set", "Clean", "Store", "Display", "Report", "Obtain",
    "Conduct", "Assess", "Deploy", "Erect", "Lower", "Raise", "Lock",
    "Seal", "Cover", "Label", "Follow", "Keep", "Place", "Provide",
}

ROLE_NAMES = {
    "SUP", "WKR", "SUB", "PM", "OP",
    "Supervisor", "Worker", "Subcontractor", "Operator",
}

_BULLET_FIELDS = ("controls", "stop_work", "hold_points", "admin", "ppe")


# ============================================================
# HELPERS
# ============================================================

def count_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:-")
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^aeiou]es|[^aeiou]ed)$", "", word)
    word = re.sub(r"e$", "", word)
    return max(1, len(re.findall(r"[aeiou]+", word)))


def _fog(bullet: str) -> tuple[float, list[str]]:
    """Return (fog_score, complex_words) for a single bullet string.

    Returns 0.0 for items with fewer than 5 words — the Gunning Fog formula
    produces unreliable results on very short fragments (a single complex word
    can dominate the ratio, giving false positives).
    """
    words = bullet.split()
    n = len(words)
    if n < 8:
        return 0.0, []
    complex_words = [w for w in words if count_syllables(w) >= 3]
    fog = 0.4 * (n + 100 * (len(complex_words) / n))
    return round(fog, 2), complex_words


def _preview(s: str, length: int = 60) -> str:
    return s[:length] if len(s) <= length else s[:length] + "…"


def _is_wah_exempt(bullet: str) -> bool:
    return bullet.strip() == WAH_SENTENCE.strip()


# ============================================================
# SCORE_TASK — runs all 12 checks, returns ValidationResult
# ============================================================

def score_task(task: TaskBlock) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    fog_scores: dict[str, float] = {}
    word_counts: dict[str, int] = {}

    # ----------------------------------------------------------
    # CHECK 1: SCHEMA CHECK
    # Pydantic validates fields at TaskBlock construction time.
    # If we receive a TaskBlock instance, schema is already valid.
    # ----------------------------------------------------------
    # (validated by Pydantic at construction — no runtime action needed)

    # ----------------------------------------------------------
    # CHECK 2: CCVS INTEGRITY
    # 2a: Hazard family codes must not appear embedded in bullet text fields.
    #     WAH sentence is exempt (it intentionally references WAH controls).
    # 2b: ccvs_code field value (if set) must be an approved full CCVS code.
    # ----------------------------------------------------------
    ccvs_fields = {
        "controls": task.controls,
        "admin": task.admin,
        "ppe": task.ppe,
        "hold_points": task.hold_points,
        "stop_work": task.stop_work,
    }
    for fname, items in ccvs_fields.items():
        for item in items:
            if _is_wah_exempt(item):
                continue
            for family in HAZARD_FAMILIES:
                # (?!-) excludes hyphenated compounds e.g. "ELE-rated" or "WAH-H6"
                if re.search(rf"\b{re.escape(family)}\b(?!-)", item):
                    errors.append(
                        f"Check 2 — Hazard family code '{family}' found embedded in "
                        f"{fname}: '{_preview(item)}'"
                    )

    if task.ccvs_code is not None and task.ccvs_code not in APPROVED_CCVS_CODES:
        errors.append(
            f"Check 2 — ccvs_code '{task.ccvs_code}' is not an approved CCVS code"
        )

    # ----------------------------------------------------------
    # CHECK 3: RESPONSIBILITY INTEGRITY
    # Role names must not appear inside controls, admin, or ppe text.
    # WAH sentence is exempt.
    # ----------------------------------------------------------
    role_check_fields = {
        "controls": task.controls,
        "admin": task.admin,
        "ppe": task.ppe,
    }
    for fname, items in role_check_fields.items():
        for item in items:
            if _is_wah_exempt(item):
                continue
            for role in ROLE_NAMES:
                if re.search(rf"\b{re.escape(role)}\b", item):
                    errors.append(
                        f"Check 3 — Role name '{role}' found in "
                        f"{fname}: '{_preview(item)}'"
                    )

    # ----------------------------------------------------------
    # CHECK 4: WAH RULE
    # ----------------------------------------------------------
    if task.wah_applicable:
        if not task.controls:
            errors.append(
                "Check 4 — wah_applicable is True but controls list is empty"
            )
        elif task.controls[0].strip() != WAH_SENTENCE.strip():
            errors.append(
                f"Check 4 — controls[0] does not match required WAH sentence. "
                f"Got: '{_preview(task.controls[0])}'"
            )

    # ----------------------------------------------------------
    # CHECKS 5–10: Per-bullet checks
    # WAH sentence is exempt from checks 5–10.
    # ----------------------------------------------------------
    for fname in _BULLET_FIELDS:
        for item in getattr(task, fname, []):
            if _is_wah_exempt(item):
                continue

            preview = _preview(item)
            words = item.split()
            n = len(words)
            word_counts[preview] = n

            # CHECK 5: ONE-CONTROL RULE (warn only)
            if " — " in item or "; " in item:
                warnings.append(
                    f"Check 5 — Stacked controls in {fname} "
                    f"(contains ' — ' or '; '): '{preview}'"
                )

            # CHECK 6: WORD CAP
            if n > 18:
                errors.append(
                    f"Check 6 — Bullet exceeds 18-word hard cap ({n} words) "
                    f"in {fname}: '{preview}'"
                )
            elif n > 12:
                warnings.append(
                    f"Check 6 — Bullet exceeds 12-word soft cap ({n} words) "
                    f"in {fname}: '{preview}'"
                )

            # CHECK 7: COMMA / SEMICOLON
            if ";" in item:
                errors.append(
                    f"Check 7 — Semicolon found in {fname}: '{preview}'"
                )
            comma_count = item.count(",")
            if comma_count > 1:
                warnings.append(
                    f"Check 7 — {comma_count} commas in {fname}: '{preview}'"
                )

            # CHECK 8: VERB-FIRST (warn only)
            if words:
                first_word = re.sub(r"[^A-Za-z\-]", "", words[0])
                if first_word not in APPROVED_VERBS:
                    warnings.append(
                        f"Check 8 — First word '{first_word}' not in approved "
                        f"verb list in {fname}: '{preview}'"
                    )

            # CHECK 9: PER-BULLET FOG
            # PPE fields contain equipment lists (not prose) — fog is not meaningful.
            # stop_work allows higher complexity (technical precision required).
            fog, complex_words = _fog(item) if fname != "ppe" else (0.0, [])
            fog_scores[preview] = fog
            fog_hard_cap = 20 if fname == "admin" else 16 if fname == "stop_work" else 14
            if fog > fog_hard_cap:
                errors.append(
                    f"Check 9 — Fog score {fog:.1f} exceeds hard cap {fog_hard_cap} "
                    f"in {fname}: '{preview}' "
                    f"(complex words: {complex_words})"
                )
            elif fog > 12:
                warnings.append(
                    f"Check 9 — Fog score {fog:.1f} exceeds soft cap 12 "
                    f"in {fname}: '{preview}' "
                    f"(complex words: {complex_words})"
                )

            # CHECK 10: VOCABULARY CHECK (warn only)
            text_lower = item.lower()
            for phrase, substitute in BANNED_WORDS.items():
                if phrase in text_lower:
                    sub_note = (
                        f" — suggest '{substitute}'"
                        if substitute
                        else " — review usage"
                    )
                    warnings.append(
                        f"Check 10 — Banned phrase '{phrase}'{sub_note} "
                        f"in {fname}: '{preview}'"
                    )

    # ----------------------------------------------------------
    # CHECK 11: SECTION COUNT CHECK
    # ----------------------------------------------------------
    hp_count = len(task.hold_points)
    ctrl_count = len(task.controls)
    sw_count = len(task.stop_work)
    ppe_count = len(task.ppe)

    if hp_count > 10:
        errors.append(f"Check 11 — hold_points exceeds 10 ({hp_count} items)")
    elif hp_count < 2:
        warnings.append(f"Check 11 — hold_points has fewer than 2 items ({hp_count})")

    if ctrl_count > 25:
        errors.append(f"Check 11 — controls exceeds 25 ({ctrl_count} items)")
    elif ctrl_count < 3:
        warnings.append(f"Check 11 — controls has fewer than 3 items ({ctrl_count})")

    if sw_count > 10:
        errors.append(f"Check 11 — stop_work exceeds 10 ({sw_count} items)")
    elif sw_count < 2:
        warnings.append(f"Check 11 — stop_work has fewer than 2 items ({sw_count})")

    if ppe_count == 0:
        warnings.append("Check 11 — ppe list is empty")

    # ----------------------------------------------------------
    # CHECK 12: RESPONSIBILITY LENGTH CHECK (warn only)
    # ----------------------------------------------------------
    for role, obligation in task.responsibility.items():
        wc = len(obligation.split())
        if wc > 10:
            warnings.append(
                f"Check 12 — Responsibility obligation for '{role}' "
                f"exceeds 10 words ({wc} words): '{_preview(obligation)}'"
            )

    passed = len(errors) == 0
    return ValidationResult(
        passed=passed,
        errors=errors,
        warnings=warnings,
        fog_scores=fog_scores,
        word_counts=word_counts,
    )


# Alias used by generate.py and library.py
validate_task = score_task
