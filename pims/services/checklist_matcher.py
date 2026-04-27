"""Cross-reference observations against checklist_items.

Phase 3 of the Site Visit Report pipeline (see
docs/pims_site_visit_report_spec.md). Pure-function matcher with no I/O —
the route layer fetches `checklist_items` and observations from Supabase
and hands them in.

Contract (spec lines 19-38):

    cross_reference(items, observations) -> (results, unmatched_observations)

  - States, in increasing severity:
        compliant_unobserved < compliant_verified < conditional < ncr
  - State per checklist item is the worst-severity status across its
    matched observations:
        any NCR              -> ncr
        any Conditional      -> conditional
        any Compliant        -> compliant_verified
        no matches at all    -> compliant_unobserved
  - Info observations pass through but DO NOT drive state. An item
    matched only by Info observations stays compliant_unobserved.
  - Every observation that fails to match any item:
        - lands in unmatched_observations (the second tuple element)
        - emits exactly one log.warning("unmatched observation %s ...")

Matching algorithm (no spec mandate beyond "no silent drops"; we re-use
the proven pattern from the legacy audit-report module):

  Primary:   case-insensitive equality on ccvs_code (when both sides
             have a non-empty value).
  Fallback:  difflib SequenceMatcher ratio >= 0.75 on
             "category_name + criteria" vs
             "ccvs_category + observation_text_enriched (or
             observation_text)". The best-scoring item that clears the
             threshold wins; ties go to the lowest (category_no, item_no).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

log = logging.getLogger(__name__)

# State constants — string values are the public contract used by the
# renderer for shading lookup (spec lines 110-119) and surfaced in API
# responses. Do not rename without updating the renderer + spec.
STATE_COMPLIANT_UNOBSERVED = "compliant_unobserved"
STATE_COMPLIANT_VERIFIED = "compliant_verified"
STATE_CONDITIONAL = "conditional"
STATE_NCR = "ncr"

_STATE_RANK = {
    STATE_COMPLIANT_UNOBSERVED: 0,
    STATE_COMPLIANT_VERIFIED: 1,
    STATE_CONDITIONAL: 2,
    STATE_NCR: 3,
}

# pims_observations.conformance_status -> state contribution. Info is
# deliberately absent: it doesn't lift state above compliant_unobserved.
_STATUS_TO_STATE = {
    "Compliant": STATE_COMPLIANT_VERIFIED,
    "Conditional": STATE_CONDITIONAL,
    "NCR": STATE_NCR,
}

MATCH_RATIO_THRESHOLD = 0.75


@dataclass(frozen=True)
class ChecklistItem:
    """One row from public.checklist_items.

    Frozen because results reference items by identity; mutating an item
    after the matcher has emitted results would break worst-severity
    aggregation downstream.
    """
    id: str
    category_no: str
    category_name: str
    item_no: str
    criteria: str
    instruction: str
    ccvs_category: str | None
    ccvs_code: str | None
    project_value_tier: str

    @classmethod
    def from_row(cls, row: dict) -> "ChecklistItem":
        return cls(
            id=str(row["id"]),
            category_no=row["category_no"],
            category_name=row["category_name"],
            item_no=row["item_no"],
            criteria=row["criteria"],
            instruction=row["instruction"],
            ccvs_category=row.get("ccvs_category"),
            ccvs_code=row.get("ccvs_code"),
            project_value_tier=row["project_value_tier"],
        )


@dataclass
class ChecklistResult:
    """One checklist item + every observation that matched it + the
    derived worst-severity state."""
    item: ChecklistItem
    matched_observations: list[dict] = field(default_factory=list)
    state: str = STATE_COMPLIANT_UNOBSERVED


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _obs_blob(obs: dict) -> str:
    return (
        _norm(obs.get("ccvs_category"))
        + " "
        + _norm(obs.get("observation_text_enriched") or obs.get("observation_text"))
    ).strip()


def _item_blob(item: ChecklistItem) -> str:
    return (_norm(item.category_name) + " " + _norm(item.criteria)).strip()


def _match_one(
    obs: dict, items: list[ChecklistItem]
) -> ChecklistItem | None:
    """Return the single best-scoring item for `obs` or None.

    Primary: ccvs_code equality. Fallback: difflib ratio >= 0.75. Ties
    on the fallback resolve to the lowest (category_no, item_no) so the
    matcher is deterministic across runs.
    """
    obs_code = _norm(obs.get("ccvs_code"))
    if obs_code:
        for it in items:
            if it.ccvs_code and _norm(it.ccvs_code) == obs_code:
                return it

    blob = _obs_blob(obs)
    if not blob:
        return None

    best: tuple[float, tuple[str, str], ChecklistItem] | None = None
    for it in items:
        ratio = SequenceMatcher(None, _item_blob(it), blob).ratio()
        if ratio < MATCH_RATIO_THRESHOLD:
            continue
        # Lower (category_no, item_no) wins ties — sort key is (-ratio, key)
        # so the highest ratio is preferred, then lexicographic order.
        candidate = (ratio, (it.category_no, it.item_no), it)
        if best is None:
            best = candidate
        elif candidate[0] > best[0]:
            best = candidate
        elif candidate[0] == best[0] and candidate[1] < best[1]:
            best = candidate
    return best[2] if best else None


def _derive_state(observations: Iterable[dict]) -> str:
    """Worst-severity state across observations. Info doesn't count."""
    rank = _STATE_RANK[STATE_COMPLIANT_UNOBSERVED]
    state = STATE_COMPLIANT_UNOBSERVED
    for obs in observations:
        s = _STATUS_TO_STATE.get(obs.get("conformance_status") or "")
        if s is None:
            continue
        if _STATE_RANK[s] > rank:
            rank = _STATE_RANK[s]
            state = s
    return state


def cross_reference(
    items: list[ChecklistItem],
    observations: list[dict],
) -> tuple[list[ChecklistResult], list[dict]]:
    """Match observations to checklist items; return (results, unmatched).

    See module docstring for the contract. Observations are paired to at
    most one item; multi-match per item is supported (an item with five
    matching observations renders five evidence rows in the report — spec
    line 121).
    """
    results: dict[str, ChecklistResult] = {
        it.id: ChecklistResult(item=it) for it in items
    }
    unmatched: list[dict] = []

    for obs in observations:
        match = _match_one(obs, items)
        if match is None:
            obs_id = obs.get("id") or obs.get("seq_no") or "<no-id>"
            log.warning(
                "unmatched observation %s (status=%s, ccvs=%s)",
                obs_id,
                obs.get("conformance_status"),
                obs.get("ccvs_code"),
            )
            unmatched.append(obs)
            continue
        results[match.id].matched_observations.append(obs)

    for r in results.values():
        r.state = _derive_state(r.matched_observations)

    # Preserve item order from the input so the caller controls
    # rendering order (typically (category_no, item_no) ascending).
    ordered = [results[it.id] for it in items]
    return ordered, unmatched
