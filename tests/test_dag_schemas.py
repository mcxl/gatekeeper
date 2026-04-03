"""
tests/test_dag_schemas.py — CI validation: all DAG JSON files must parse against Pydantic schema.

Runs as part of pre-release gate.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.dag import DagRules, load_dag_rules

_DAG_RULES_DIR = Path(__file__).parent.parent / "core" / "dag_rules"


class TestAllDagSchemas:
    @pytest.fixture(params=list(_DAG_RULES_DIR.glob("*.json")))
    def dag_path(self, request):
        return request.param

    def test_dag_json_loads_cleanly(self, dag_path):
        """Each DAG JSON must validate against the DagRules Pydantic model."""
        rules = load_dag_rules(str(dag_path))
        assert isinstance(rules, DagRules)
        assert rules.category
        assert len(rules.nodes) > 0

    def test_dag_nodes_have_keywords(self, dag_path):
        rules = load_dag_rules(str(dag_path))
        for node in rules.nodes:
            assert node.id
            assert len(node.keywords) > 0, f"Node {node.id} has no keywords"

    def test_dag_nodes_have_valid_violation_type(self, dag_path):
        rules = load_dag_rules(str(dag_path))
        for node in rules.nodes:
            assert node.violation_type in ("HARD_FAIL", "HUMAN_REVIEW"), \
                f"Node {node.id} has invalid violation_type: {node.violation_type}"
