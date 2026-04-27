"""Phase 3 — pims.services.checklist_matcher.cross_reference contract tests.

Pins the spec (docs/pims_site_visit_report_spec.md lines 19-38):
  - State precedence: compliant_unobserved < compliant_verified < conditional < ncr
  - Worst-severity wins per item.
  - Info observations DO NOT lift state above compliant_unobserved.
  - cross_reference() returns (results, unmatched_observations).
  - Every unmatched observation emits exactly one log.warning.
"""
from __future__ import annotations

import logging
from uuid import uuid4

import pytest

from pims.services.checklist_matcher import (
    ChecklistItem,
    MATCH_RATIO_THRESHOLD,
    STATE_COMPLIANT_UNOBSERVED,
    STATE_COMPLIANT_VERIFIED,
    STATE_CONDITIONAL,
    STATE_NCR,
    cross_reference,
)


def _item(
    *, ccvs_code=None, ccvs_category=None,
    category_no="01", item_no="01",
    category_name="Planning and Risk Management",
    criteria="Is the project risk assessment completed?",
    instruction="Check risk assessment is current",
    tier="high",
) -> ChecklistItem:
    return ChecklistItem(
        id=str(uuid4()),
        category_no=category_no,
        category_name=category_name,
        item_no=item_no,
        criteria=criteria,
        instruction=instruction,
        ccvs_category=ccvs_category,
        ccvs_code=ccvs_code,
        project_value_tier=tier,
    )


def _obs(*, status=None, ccvs_code=None, text=None, ccvs_category=None,
         id_="obs-1"):
    return {
        "id": id_,
        "conformance_status": status,
        "ccvs_code": ccvs_code,
        "ccvs_category": ccvs_category,
        "observation_text": text,
        "observation_text_enriched": text,
    }


# ── State derivation ─────────────────────────────────────────────────────

class TestStateDerivation:
    def test_no_match_yields_compliant_unobserved(self):
        item = _item(ccvs_code="WAH-H6")
        results, unmatched = cross_reference([item], [])
        assert len(results) == 1
        assert results[0].state == STATE_COMPLIANT_UNOBSERVED
        assert results[0].matched_observations == []
        assert unmatched == []

    def test_single_compliant_match_yields_verified(self):
        item = _item(ccvs_code="WAH-H6")
        obs = _obs(status="Compliant", ccvs_code="WAH-H6")
        results, _ = cross_reference([item], [obs])
        assert results[0].state == STATE_COMPLIANT_VERIFIED

    def test_single_conditional_match_yields_conditional(self):
        item = _item(ccvs_code="WAH-H6")
        obs = _obs(status="Conditional", ccvs_code="WAH-H6")
        results, _ = cross_reference([item], [obs])
        assert results[0].state == STATE_CONDITIONAL

    def test_single_ncr_match_yields_ncr(self):
        item = _item(ccvs_code="WAH-H6")
        obs = _obs(status="NCR", ccvs_code="WAH-H6")
        results, _ = cross_reference([item], [obs])
        assert results[0].state == STATE_NCR

    def test_worst_severity_wins_ncr_over_compliant(self):
        item = _item(ccvs_code="WAH-H6")
        obs1 = _obs(status="Compliant", ccvs_code="WAH-H6", id_="o1")
        obs2 = _obs(status="NCR", ccvs_code="WAH-H6", id_="o2")
        results, _ = cross_reference([item], [obs1, obs2])
        assert results[0].state == STATE_NCR
        assert len(results[0].matched_observations) == 2

    def test_worst_severity_conditional_over_compliant(self):
        item = _item(ccvs_code="WAH-H6")
        obs1 = _obs(status="Compliant", ccvs_code="WAH-H6", id_="o1")
        obs2 = _obs(status="Conditional", ccvs_code="WAH-H6", id_="o2")
        results, _ = cross_reference([item], [obs1, obs2])
        assert results[0].state == STATE_CONDITIONAL


class TestInfoDoesNotDriveState:
    def test_info_only_match_stays_unobserved(self):
        item = _item(ccvs_code="WAH-H6")
        obs = _obs(status="Info", ccvs_code="WAH-H6")
        results, _ = cross_reference([item], [obs])
        # Info matches the item (so it's not unmatched) but state stays
        # compliant_unobserved per spec line 36.
        assert results[0].state == STATE_COMPLIANT_UNOBSERVED
        assert results[0].matched_observations == [obs]

    def test_info_alongside_compliant_does_not_alter(self):
        item = _item(ccvs_code="WAH-H6")
        obs1 = _obs(status="Compliant", ccvs_code="WAH-H6", id_="o1")
        obs2 = _obs(status="Info", ccvs_code="WAH-H6", id_="o2")
        results, _ = cross_reference([item], [obs1, obs2])
        assert results[0].state == STATE_COMPLIANT_VERIFIED


# ── Matching algorithm ──────────────────────────────────────────────────

class TestMatchingAlgorithm:
    def test_ccvs_code_equality_primary(self):
        item_a = _item(ccvs_code="WAH-H6", item_no="01")
        item_b = _item(ccvs_code="SIL-M3", item_no="02")
        # Observation text is similar to item_b's category text but
        # ccvs_code matches item_a — primary should win.
        obs = _obs(status="NCR", ccvs_code="WAH-H6")
        results, _ = cross_reference([item_a, item_b], [obs])
        assert results[0].state == STATE_NCR
        assert results[1].state == STATE_COMPLIANT_UNOBSERVED

    def test_fuzzy_fallback_when_no_ccvs_code(self):
        item = _item(
            category_name="Working at Height",
            criteria="Is fall arrest properly configured?",
        )
        obs = _obs(
            status="NCR",
            ccvs_category="Working at Height",
            text="Is fall arrest properly configured",
        )
        results, unmatched = cross_reference([item], [obs])
        assert results[0].state == STATE_NCR
        assert unmatched == []

    def test_fuzzy_threshold_excludes_unrelated(self):
        item = _item(criteria="Is fall arrest properly configured?")
        obs = _obs(status="NCR", text="zebras and giraffes on a Tuesday")
        results, unmatched = cross_reference([item], [obs])
        # Below threshold — must NOT match.
        assert results[0].state == STATE_COMPLIANT_UNOBSERVED
        assert obs in unmatched

    def test_threshold_constant_pinned(self):
        # If anyone changes the threshold the spec needs revisiting.
        assert MATCH_RATIO_THRESHOLD == 0.75


# ── Multi-match per item ────────────────────────────────────────────────

class TestMultiMatch:
    def test_item_with_five_matches_keeps_all(self):
        """Spec line 121: 'render one evidence row per matched
        observation under the item's category/criteria header. No
        summarisation, no "+N more" footnotes.' Matcher must preserve
        all matches."""
        item = _item(ccvs_code="WAH-H6")
        obs_list = [
            _obs(status="Compliant", ccvs_code="WAH-H6", id_=f"o{i}")
            for i in range(5)
        ]
        results, _ = cross_reference([item], obs_list)
        assert len(results[0].matched_observations) == 5

    def test_observation_pairs_to_at_most_one_item(self):
        item_a = _item(ccvs_code="WAH-H6", item_no="01")
        item_b = _item(ccvs_code="WAH-H6", item_no="02")
        obs = _obs(status="NCR", ccvs_code="WAH-H6")
        results, _ = cross_reference([item_a, item_b], [obs])
        # One observation must not appear under both items.
        total_matches = sum(len(r.matched_observations) for r in results)
        assert total_matches == 1


# ── Unmatched observations + warning emission ───────────────────────────

class TestUnmatched:
    def test_unmatched_observation_returned_and_logged(self, caplog):
        item = _item(ccvs_code="WAH-H6")
        obs = _obs(status="NCR", ccvs_code="ZZZ-Z0", id_="obs-orphan")

        with caplog.at_level(logging.WARNING, logger="pims.services.checklist_matcher"):
            results, unmatched = cross_reference([item], [obs])

        assert obs in unmatched
        assert results[0].state == STATE_COMPLIANT_UNOBSERVED
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "unmatched observation" in warnings[0].getMessage()
        assert "obs-orphan" in warnings[0].getMessage()

    def test_one_warning_per_unmatched(self, caplog):
        """Spec invariant #6 — exactly one log.warning per unmatched."""
        item = _item(ccvs_code="WAH-H6")
        obs_list = [
            _obs(status="NCR", ccvs_code="ZZZ-Z0", id_=f"orphan-{i}")
            for i in range(3)
        ]
        with caplog.at_level(logging.WARNING, logger="pims.services.checklist_matcher"):
            _, unmatched = cross_reference([item], obs_list)
        assert len(unmatched) == 3
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 3


# ── Determinism ─────────────────────────────────────────────────────────

class TestDeterminism:
    def test_fuzzy_ties_resolve_lexicographically(self):
        """Two items with identical fuzzy scores: the lower
        (category_no, item_no) wins."""
        same_cat = "Planning and Risk Management"
        same_text = "Is the something done correctly?"
        item_a = _item(category_no="03", item_no="02",
                       category_name=same_cat, criteria=same_text)
        item_b = _item(category_no="03", item_no="01",
                       category_name=same_cat, criteria=same_text)
        obs = _obs(status="NCR", ccvs_category=same_cat, text=same_text)
        results, _ = cross_reference([item_a, item_b], [obs])
        # item_b (item_no=01) should win the tie.
        for r in results:
            if r.item.item_no == "01":
                assert len(r.matched_observations) == 1
            else:
                assert len(r.matched_observations) == 0

    def test_results_preserve_input_order(self):
        a = _item(category_no="03", item_no="02")
        b = _item(category_no="03", item_no="01")
        c = _item(category_no="01", item_no="01")
        results, _ = cross_reference([a, b, c], [])
        assert [r.item.id for r in results] == [a.id, b.id, c.id]


# ── ChecklistItem.from_row ──────────────────────────────────────────────

def test_from_row_handles_supabase_payload():
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "category_no": "01",
        "category_name": "Planning and Risk Management",
        "item_no": "02",
        "criteria": "Is the project risk assessment completed?",
        "instruction": "Check risk assessment is current",
        "ccvs_category": None,
        "ccvs_code": None,
        "project_value_tier": "high",
        "created_at": "2026-04-27T00:00:00Z",   # ignored
        "updated_at": "2026-04-27T00:00:00Z",   # ignored
    }
    it = ChecklistItem.from_row(row)
    assert it.id == row["id"]
    assert it.category_no == "01"
    assert it.project_value_tier == "high"
