"""
Tests for exclusion/variation context negation.

Validates that keywords mentioned in exclusion, variation, or
latent-condition clauses are suppressed from inference.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.inference_matrix import _is_negated


class TestExclusionContextNegation:
    """Keywords in exclusion/variation T&C clauses should be negated."""

    def test_asbestos_in_variation_clause(self):
        text = (
            "pre-existing toxic materials such as lead paints or asbestos "
            "particle containing materials will be subject to additional costs "
            "and time to prepare or remove. if uncovered during the works this "
            "will be a deemed variation."
        )
        assert _is_negated("asbestos", text), "Asbestos in variation clause should be negated"

    def test_lead_in_variation_clause(self):
        text = (
            "pre-existing toxic materials such as lead paints or asbestos "
            "will be subject to additional costs"
        )
        assert _is_negated("lead", text), "Lead in variation clause should be negated"

    def test_asbestos_in_confirmed_scope(self):
        text = "asbestos removal from ceiling panels in existing building"
        assert not _is_negated("asbestos", text), "Confirmed asbestos scope should NOT be negated"

    def test_excluded_from_scope(self):
        text = "asbestos management is excluded from this contract"
        assert _is_negated("asbestos", text), "'excluded from' should negate"

    def test_not_part_of_scope(self):
        text = "lead paint removal is not part of the scope of works"
        assert _is_negated("lead paint", text), "'not part of the scope' should negate"

    def test_latent_condition(self):
        text = "any asbestos identified is a latent condition and will be priced separately"
        assert _is_negated("asbestos", text), "'latent condition' should negate"

    def test_pre_existing_toxic(self):
        text = "pre-existing toxic materials such as asbestos will be a variation"
        assert _is_negated("asbestos", text), "'pre-existing toxic' should negate"

    def test_direct_negation_still_works(self):
        text = "no asbestos was identified in the survey"
        assert _is_negated("asbestos", text), "Direct 'no' negation should still work"

    def test_positive_scope_not_negated(self):
        text = "scaffold erection for facade remedial works including concrete spalling repair"
        assert not _is_negated("scaffold", text), "Positive scope should not be negated"
