"""Wording-enrichment staging stage for RPD SSA audit generation.

Rewrites each row's ``finding`` text in place so that:

(a) it describes the actual observed instance, drawing on
    ``observation_text``, ``ccvs_category`` and ``legal_ref`` rather than
    repeating a generic template line,
(b) wording does not duplicate verbatim across NCRs in the same hazard
    family (grouped by ``ccvs_category``), and
(c) the breach is stated in a complete, grammatical sentence.

``observation_text`` and the source xlsx are never modified.

Gated by the env var ``PIMS_ENRICH_FINDINGS`` (truthy values:
``1``/``true``/``yes``/``on``) or the per-call ``enabled`` argument.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict

from pims.services.audit_report_from_xlsx import (
    ParsedObs,
    _anthropic_call,
    _strip_fences,
)

log = logging.getLogger(__name__)

ENV_FLAG = "PIMS_ENRICH_FINDINGS"


def is_enabled(override: bool | None = None) -> bool:
    if override is not None:
        return bool(override)
    raw = (os.environ.get(ENV_FLAG, "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _family_key(o: ParsedObs) -> str:
    return (o.ccvs_category or o.ccvs_code or "").strip().lower()


async def enrich_findings(
    site_obs: list[ParsedObs], enabled: bool | None = None,
) -> None:
    """In-place rewrite of ``finding`` for NCR/Conditional rows.

    No-op when the feature is disabled, when there are no eligible rows,
    or when the Anthropic call fails (original text preserved).
    """
    if not is_enabled(enabled):
        return

    eligible: list[tuple[int, ParsedObs]] = [
        (i, o) for i, o in enumerate(site_obs)
        if (o.status or "").strip() in {"NCR", "Conditional"}
        and (o.observation_text or "").strip()
    ]
    if not eligible:
        return

    # Family map gives the model explicit awareness of which rows share a
    # hazard family so it can vary phrasing across them.
    families: dict[str, list[int]] = defaultdict(list)
    for i, o in eligible:
        families[_family_key(o) or "(uncategorised)"].append(i)

    payload = [
        {
            "idx": i,
            "status": o.status,
            "ccvs_code": o.ccvs_code,
            "ccvs_category": o.ccvs_category,
            "legal_ref": o.legal_ref,
            "observation_text": o.observation_text,
            "current_finding": o.finding,
        }
        for i, o in eligible
    ]
    family_groups = {k: v for k, v in families.items() if len(v) > 1}

    system_blocks = [
        {"type": "text", "text":
            "You rewrite the 'finding' sentence(s) for rows of an Australian "
            "WHS site-inspection report. For each input row, return a "
            "rewritten finding that:\n"
            "  1. describes the actual observed instance, grounded in the "
            "     row's observation_text, ccvs_category and legal_ref — not "
            "     a generic template line;\n"
            "  2. states the breach as a complete, grammatical sentence "
            "     (subject + verb + object), Australian English;\n"
            "  3. does NOT duplicate the wording of other rows in the same "
            "     hazard family (see family_groups). Vary sentence "
            "     structure and verbs across siblings in a family while "
            "     keeping each finding faithful to its own observation.\n\n"
            "STRICT RULES:\n"
            "- Do not invent facts, measurements, dates, names or evidence "
            "  not present in observation_text.\n"
            "- Preserve numbers, units, codes (CCVS, WHS regulation refs), "
            "  proper nouns and site-specific identifiers exactly.\n"
            "- Cite the legal_ref in the finding when one is supplied "
            "  (e.g. 'contrary to WHS Reg cl.298'), but do not fabricate a "
            "  reference if the input field is blank.\n"
            "- Keep each finding to 1-2 sentences. No bullets, no headings.\n"
            "- The finding DESCRIBES what was observed and why it is a "
            "  breach. It is not the corrective action. Do not write "
            "  prescriptive 'must be X' / 'shall be Y' clauses — that "
            "  belongs in the recommendation, not the finding.\n"
            "- Rewrite whenever the current_finding is generic, terse, "
            "  template-style, or thinner than the observation_text "
            "  supports — even if it is grammatically correct. Only return "
            "  the current_finding unchanged if it is already specific to "
            "  the observed instance, well-formed, descriptive (not "
            "  prescriptive) and not duplicative within its family.\n\n"
            "Return ONLY a JSON array: "
            '[{"idx": <int>, "finding": "<rewritten finding>"}, ...]',
         "cache_control": {"type": "ephemeral"}},
    ]
    user = (
        "FAMILY_GROUPS (rows sharing a hazard family — vary wording across these):\n"
        + json.dumps(family_groups, ensure_ascii=False)
        + "\n\nROWS:\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        raw = await _anthropic_call(system_blocks, user, max_tokens=4096)
        records = json.loads(_strip_fences(raw))
    except Exception as e:
        log.warning(f"finding enrichment failed, leaving findings untouched: {e}")
        return

    by_idx: dict[int, str] = {}
    for r in records or []:
        if not isinstance(r, dict) or "idx" not in r:
            continue
        try:
            idx = int(r["idx"])
        except Exception:
            continue
        new = r.get("finding")
        if isinstance(new, str) and new.strip():
            by_idx[idx] = new.strip()

    applied = 0
    for i, o in eligible:
        if i in by_idx and by_idx[i] != (o.finding or ""):
            o.finding = by_idx[i]
            applied += 1
    log.info(f"finding enrichment applied to {applied} of {len(eligible)} eligible rows")
