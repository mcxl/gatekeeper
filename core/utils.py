"""
core/utils.py — Shared utility functions for the Gatekeeper pipeline.

Functions here consolidate logic that was previously duplicated inline
across agents/ and core/. Do not import from agents/ in this module —
keep it dependency-free so any layer can import it safely.
"""

from __future__ import annotations

import re

# ── Regex compiled once at import time ────────────────────────────────────────

_FENCE_OPEN = re.compile(r"^```[a-z]*\n?")
_FENCE_CLOSE = re.compile(r"\n?```$")

_ROLE_PREFIX = re.compile(
    r"^(SUP|WKR|SUB|PM|OP|Supervisor|Worker|Subcontractor|Operator)"
    r"\s+(to\s+|[-\u2014]\s*)",
    re.IGNORECASE,
)


# ── Public API ─────────────────────────────────────────────────────────────────


def strip_fences(text: str) -> str:
    """Strip leading and trailing markdown code fences from a string.

    Handles variants such as ```````, `````json`, `````python`, etc.
    The input string is stripped of surrounding whitespace before
    fence removal, matching the inline pattern used across all agents.

    Args:
        text: Raw text that may contain an opening fence (e.g. ``````json``)
              and/or a closing fence (``````).

    Returns:
        The text with fences removed and no leading/trailing whitespace.

    Examples:
        >>> strip_fences("```json\\n{}\n```")
        '{}'
        >>> strip_fences('{}')
        '{}'
    """
    text = text.strip()
    text = _FENCE_OPEN.sub("", text)
    text = _FENCE_CLOSE.sub("", text)
    return text


def enforce_wah_flag(task: dict) -> dict:
    """Force ``wah_applicable`` to ``False`` when ``ccvs_code`` is not a WAH code.

    Guards against agents incorrectly setting ``wah_applicable=True`` for
    non-WAH tasks (e.g. ``LED-H6``, ``SIL-H6``), which causes Check 4
    failures in validation and incorrect WAH content in rendered documents.

    The task dict is mutated in place **and** returned so callers can use
    either pattern::

        enforce_wah_flag(task)           # mutate in place
        task = enforce_wah_flag(task)    # or reassign

    Args:
        task: A TaskBlock dict containing at minimum ``ccvs_code`` and
              ``wah_applicable`` keys (both optional — missing keys are
              handled gracefully).

    Returns:
        The same dict, with ``wah_applicable`` corrected if needed.
    """
    ccvs_code = str(task.get("ccvs_code") or "N/A")
    if not ccvs_code.startswith("WAH"):
        task["wah_applicable"] = False
    return task


def strip_role_prefixes(items: list[str]) -> list[str]:
    """Strip role-name prefixes from control/admin bullet strings.

    Removes prefixes like ``"Supervisor to "``, ``"SUP - "``, ``"WKR — "``
    from the start of each string, then capitalises the first letter of the
    remaining text. Empty strings produced by stripping are preserved as-is.

    Matches the inline Check 3 guard logic in ``core/generate.py _parse_task()``.

    Recognised role tokens (case-insensitive):
        ``SUP``, ``WKR``, ``SUB``, ``PM``, ``OP``,
        ``Supervisor``, ``Worker``, ``Subcontractor``, ``Operator``

    Recognised separators following the role token:
        ``to `` (word), ``-`` (hyphen), ``—`` (em dash), with optional spaces.

    Args:
        items: List of bullet strings, e.g. control or admin field values.

    Returns:
        New list with role prefixes stripped and first letter capitalised.

    Examples:
        >>> strip_role_prefixes(["Supervisor to inspect containment"])
        ['Inspect containment']
        >>> strip_role_prefixes(["SUP — Check barriers before start"])
        ['Check barriers before start']
        >>> strip_role_prefixes(["Install edge protection"])
        ['Install edge protection']
    """
    cleaned: list[str] = []
    for item in items:
        stripped = _ROLE_PREFIX.sub("", item).strip()
        if stripped:
            stripped = stripped[0].upper() + stripped[1:]
        cleaned.append(stripped)
    return cleaned
