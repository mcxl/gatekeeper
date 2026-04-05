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
from core.utils import enforce_wah_flag

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

_GEOTECH_TERMS = ("geotech", "geotechnical", "soil report", "soil assessment", "foundation report")
_GEOTECH_DEFERRED = ("tba", "tbc", "to be", "pending", "not yet", "awaiting")
_DEPTH_PATTERN = re.compile(r"(\d+\.?\d*)\s*m(?:etre|eter|m|\b)", re.IGNORECASE)
_INFERRED_DEPTH_KEYWORDS = ("shoring", "trench shield", "trench box", "bench", "batter")
_STABLE_ROCK_TERMS = ("stable rock", "competent rock", "no shoring required")
_STABLE_ROCK_AUTHORITY = ("cpeng", "nper", "registered geotechnical", "geotechnical engineer")


def check_21_geotech_trigger(task: TaskBlock) -> str:
    """Check 21: Geotech trigger for excavation >= 1.5m.

    Returns 'PASS', 'FAIL', 'FAIL_STABLE_ROCK', or 'SKIP'.
    """
    hrcw_cat = str(getattr(task, "hrcw_category", "") or "").lower()
    task_text = task.task.lower() + " " + task.scope.lower()
    all_text = task_text + " " + " ".join(h.lower() for h in task.hazards)

    is_excavation = "excavat" in hrcw_cat or "trench" in hrcw_cat or "excavat" in task_text or "trench" in task_text

    if not is_excavation:
        return "SKIP"

    search_text = (
        all_text + " "
        + " ".join(c.lower() for c in task.controls)
        + " " + " ".join(a.lower() for a in task.admin)
        + " " + " ".join(s.lower() for s in task.stop_work)
        + " " + " ".join(h.lower() for h in task.hold_points)
    )

    # Check for explicit depth >= 1.5m
    depth_mentioned = False
    for match in _DEPTH_PATTERN.finditer(search_text):
        try:
            depth = float(match.group(1))
            if depth >= 1.5:
                depth_mentioned = True
                break
        except ValueError:
            continue

    # Infer depth >= 1.5m if shoring/trench-shield keywords present
    if not depth_mentioned:
        if any(kw in search_text for kw in _INFERRED_DEPTH_KEYWORDS):
            depth_mentioned = True

    if not depth_mentioned:
        return "SKIP"

    # Stable rock path — requires registered geotechnical authority
    if any(term in search_text for term in _STABLE_ROCK_TERMS):
        if any(auth in search_text for auth in _STABLE_ROCK_AUTHORITY):
            return "PASS"
        return "FAIL_STABLE_ROCK"

    # Check for geotech citation — exclude deferred/vague references
    for term in _GEOTECH_TERMS:
        if term in search_text:
            # Check if the citation is deferred
            for sent in search_text.split("."):
                if term in sent and any(d in sent for d in _GEOTECH_DEFERRED):
                    continue  # deferred — does not count
                if term in sent:
                    return "PASS"  # concrete citation found

    return "FAIL"


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

    if ctrl_count > 8:
        errors.append(f'Check 11 - {ctrl_count} controls: maximum 8 per task')
    elif ctrl_count > 6:
        warnings.append(f'Check 11 - {ctrl_count} controls: lean standard is max 6')

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

    # ----------------------------------------------------------
    # CHECK 13: PLAIN ENGLISH (WorkCover NSW) — warn only
    # ----------------------------------------------------------
    try:
        from vocab.swms_vocabulary import check_vocabulary as _pe_check
        all_text_fields = (
            task.controls + task.admin + task.ppe
            + task.hold_points + task.stop_work
        )
        for item in all_text_fields:
            pe_warnings = _pe_check(item)
            for w in pe_warnings:
                warnings.append(f"Check 13 — {w}: '{_preview(item)}'")
    except ImportError:
        pass

    # ----------------------------------------------------------
    # CHECK 21: GEOTECH TRIGGER
    # Excavation >= 1.5m requires geotechnical soil report citation.
    # ----------------------------------------------------------
    _geotech_result = check_21_geotech_trigger(task)
    if _geotech_result == "FAIL":
        errors.append(
            "Check 21 — Rule 21: No geotechnical soil report cited for "
            "excavation ≥ 1.5m. HRCW — work in excavations requires "
            "a current geotechnical assessment."
        )
    elif _geotech_result == "FAIL_STABLE_ROCK":
        errors.append(
            "Check 21 — Rule 21: 'Stable rock' claim requires sign-off "
            "by a CPEng, NPER, or registered geotechnical engineer. "
            "No qualifying authority cited."
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


# ============================================================
# MONITORING FREQUENCY NORMALIZATION
# ============================================================

VALID_MONITORING_FREQ = {
    "before each use", "each shift start", "continuous", "daily", "weekly",
}

MONITORING_FREQ_MAP = {
    "before use": "before each use", "prior to each use": "before each use",
    "pre-use": "before each use",
    "start of shift": "each shift start", "shift start": "each shift start",
    "per shift": "each shift start", "every shift": "each shift start",
    "before each shift start": "each shift start",
    "ongoing": "continuous", "continuously": "continuous",
    "constant": "continuous", "real-time": "continuous",
    "each day": "daily", "every day": "daily", "once daily": "daily",
    "each week": "weekly", "once weekly": "weekly", "every week": "weekly",
}


def normalise_monitoring_freq(mon: dict | None) -> dict | None:
    """Normalise monitoring.frequency to an approved value. Returns None if not a dict."""
    if not isinstance(mon, dict):
        return None
    freq = mon.get("frequency", "")
    if freq not in VALID_MONITORING_FREQ:
        mon["frequency"] = MONITORING_FREQ_MAP.get(freq.lower().strip(), "daily")
    return mon


# PRE-RENDER GUARDS (FIX_G)
# ============================================================

MAX_ADMIN = 20

def guard_tasks(tasks: list) -> list:
    """Apply pre-render guards to a list of task dicts/objects.

    G1: Force wah_applicable=False if ccvs_code doesn't start with WAH.
    G2: Cap admin controls at MAX_ADMIN items.
    Returns the (mutated) list.
    """
    for task in tasks:
        # G1 — WAH flag guard
        if isinstance(task, dict):
            enforce_wah_flag(task)
        elif not (getattr(task, "ccvs_code", None) or "").startswith("WAH"):
            task.wah_applicable = False

        # G2 — Admin controls hard cap
        if hasattr(task, "admin"):
            task.admin = task.admin[:MAX_ADMIN]
        elif isinstance(task, dict):
            for _key in ("admin", "admin_controls"):
                if _key in task:
                    task[_key] = task[_key][:MAX_ADMIN]
    return tasks


HALLUCINATED_REFS = {"AS/NZS 3580", "AS/NZS3580"}

def strip_hallucinated_refs(citations: list[str]) -> list[str]:
    """Remove known hallucinated standard references (H2)."""
    return [c for c in citations if c not in HALLUCINATED_REFS]


def set_cell_fill(cell, colour: str = "FFFFFF") -> None:
    """Set a cell's background fill colour (G3 — white cell fill)."""
    from docx.oxml.ns import qn
    from lxml import etree
    tc = cell._tc
    tcPr = tc.find(qn('w:tcPr'))
    if tcPr is None:
        tcPr = etree.SubElement(tc, qn('w:tcPr'))
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = etree.SubElement(tcPr, qn('w:shd'))
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), colour)
