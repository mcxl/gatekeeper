"""
tests/test_procore_webhook.py — Tests for Procore review-first workflow Phase 2 (refined).
"""

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.procore.webhook_handler import (
    ALLOWED_STATUSES,
    ALLOWED_WORKFLOW_STATES,
    MAX_REQUIRED_AMENDMENTS,
    REVIEW_DISCLAIMER,
    extract_submittal_attachments,
    is_duplicate,
    log_payload,
    parse_event,
    reset_idempotency,
    validate_signature,
)
from core.procore.prescreen_reviewer import (
    ALLOWED_BASIS,
    REVIEW_DISCLAIMER_LOW,
    _normalize_basis,
    _sort_amendments,
    resolve_workflow_state,
    run_prescreen_review,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "procore"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


# ── Signature validation ────────────────────────────────────────────────────

class TestSignatureValidation:
    def test_valid_signature(self):
        secret = "test-secret-key"
        body = b'{"event_type": "test"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert validate_signature(body, sig, secret)

    def test_invalid_signature(self):
        assert not validate_signature(b"body", "wrong", "secret")

    def test_empty_secret_rejects(self):
        assert not validate_signature(b"body", "sig", "")

    def test_empty_signature_rejects(self):
        assert not validate_signature(b"body", "", "secret")


# ── Event parsing ───────────────────────────────────────────────────────────

class TestEventParsing:
    def test_parse_submittal_event(self):
        event = parse_event(_load_fixture("submittal_created"))
        assert event.event_type == "submittals.submittal_logs.created"
        assert event.project_id == 12345

    def test_extract_pdf_attachments(self):
        event = parse_event(_load_fixture("submittal_created"))
        atts = extract_submittal_attachments(event)
        assert len(atts) == 1
        assert atts[0].filename == "SWMS_Scaffold_Bay3_v1.pdf"


# ── Idempotency ─────────────────────────────────────────────────────────────

class TestIdempotency:
    def setup_method(self):
        reset_idempotency()

    def test_first_not_duplicate(self):
        assert not is_duplicate("evt-001")

    def test_second_is_duplicate(self):
        is_duplicate("evt-002")
        assert is_duplicate("evt-002")


# ── Basis normalization ─────────────────────────────────────────────────────

class TestBasisNormalization:
    def test_project_rule(self):
        assert _normalize_basis("project rule") == "project_rule"
        assert _normalize_basis("project_rule") == "project_rule"

    def test_hrcw_gap(self):
        assert _normalize_basis("HRCW gap") == "hrcw_gap"

    def test_unknown_defaults_to_reviewer_judgment(self):
        assert _normalize_basis("something unknown") == "reviewer_judgment"

    def test_all_allowed_values_are_stable(self):
        for b in ALLOWED_BASIS:
            assert _normalize_basis(b) == b


# ── Deterministic amendment ordering ────────────────────────────────────────

class TestAmendmentOrdering:
    def test_mandatory_before_advisory(self):
        amendments = [
            {"severity": "advisory", "basis": "project_rule"},
            {"severity": "mandatory", "basis": "project_rule"},
        ]
        sorted_a = _sort_amendments(amendments)
        assert sorted_a[0]["severity"] == "mandatory"

    def test_high_before_mandatory(self):
        amendments = [
            {"severity": "mandatory", "basis": "project_rule"},
            {"severity": "high", "basis": "hrcw_gap"},
        ]
        sorted_a = _sort_amendments(amendments)
        assert sorted_a[0]["severity"] == "high"

    def test_issue_gate_before_reviewer_judgment(self):
        amendments = [
            {"severity": "mandatory", "basis": "reviewer_judgment"},
            {"severity": "mandatory", "basis": "issue_gate_check"},
        ]
        sorted_a = _sort_amendments(amendments)
        assert sorted_a[0]["basis"] == "issue_gate_check"


# ── Workflow state precedence ───────────────────────────────────────────────

class TestWorkflowStatePrecedence:
    def test_low_confidence_forces_escalated(self):
        state, status = resolve_workflow_state("LOW", [], 0)
        assert state == "escalated_for_attention"
        assert status == "Escalate"

    def test_high_severity_forces_escalated(self):
        amendments = [{"severity": "high", "basis": "hrcw_gap"}]
        state, status = resolve_workflow_state("HIGH", amendments, 0)
        assert state == "escalated_for_attention"

    def test_hrcw_gap_forces_escalated(self):
        amendments = [{"severity": "mandatory", "basis": "hrcw_gap"}]
        state, status = resolve_workflow_state("MEDIUM", amendments, 0)
        assert state == "escalated_for_attention"

    def test_amendments_return_for_amendment(self):
        amendments = [{"severity": "mandatory", "basis": "project_rule"}]
        state, status = resolve_workflow_state("MEDIUM", amendments, 0)
        assert state == "returned_for_amendment_recommended"
        assert status == "Return for Amendment"

    def test_no_issues_reviewed_pending(self):
        state, status = resolve_workflow_state("HIGH", [], 0)
        assert state == "reviewed_pending_human"
        assert status == "Ready for Human Review"

    def test_state_always_in_allowed(self):
        for conf in ("HIGH", "MEDIUM", "LOW"):
            for amends in ([], [{"severity": "mandatory", "basis": "project_rule"}]):
                state, status = resolve_workflow_state(conf, amends, 0)
                assert state in ALLOWED_WORKFLOW_STATES
                assert status in ALLOWED_STATUSES


# ── Full review artifact ────────────────────────────────────────────────────

class TestPrescreenReviewRefined:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.rule_pack = _load_fixture("project_rule_pack_12345")
        self.swms_text = (
            "SWMS - Scaffold Erection Bay 3\n"
            "Task 1: Erect scaffold to level 3\nHazard: Fall from height\n"
            "Controls: Install edge protection. Use harness.\nFollow SWMS at all times.\n"
            "Task 2: Install guardrails\nControls: Supervisor to monitor.\n"
            "Task 3: Inspect scaffold\nTask 4: Demobilise\n"
        )

    def test_review_version_2(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r["review_version"] == "2.0"

    def test_requires_human_review_always_true(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r["requires_human_review"] is True

    def test_workflow_state_in_allowed(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r["workflow_state"] in ALLOWED_WORKFLOW_STATES

    def test_status_in_allowed(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r["status_recommendation"] in ALLOWED_STATUSES

    def test_no_approval_language(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        full = json.dumps(r).lower()
        for banned in ("approved", "accepted", "compliant"):
            assert f'"{banned}"' not in full

    def test_max_5_visible_amendments(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert len(r["required_amendments"]) <= MAX_REQUIRED_AMENDMENTS

    def test_suppressed_issue_count_present(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "suppressed_issue_count" in r
        assert isinstance(r["suppressed_issue_count"], int)

    def test_amendments_have_priority(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        for a in r["required_amendments"]:
            assert "priority" in a
            assert isinstance(a["priority"], int)

    def test_basis_values_in_vocabulary(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        for a in r["required_amendments"]:
            assert a["basis"] in ALLOWED_BASIS

    def test_project_review_status_available(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r["project_review_status"] == "AVAILABLE"

    def test_project_review_status_unavailable(self):
        r = run_prescreen_review(self.swms_text, {"rules": [], "structural_expectations": []})
        assert r["project_review_status"] == "UNAVAILABLE"

    def test_project_review_status_partial(self):
        r = run_prescreen_review(self.swms_text, {"rules": [{"rule_id": "R1", "category": "x", "requirement": "y"}], "structural_expectations": []})
        assert r["project_review_status"] == "PARTIAL"

    def test_stable_identifiers_present(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack,
                                  job_id="j1", document_reference="doc.pdf",
                                  source_surface="submittals", source_item_id="999")
        assert r["review_run_id"]
        assert r["document_hash"]
        assert r["source_surface"] == "submittals"
        assert r["source_item_id"] == "999"
        assert r["reviewed_at"]

    def test_document_hash_stable(self):
        r1 = run_prescreen_review(self.swms_text, self.rule_pack)
        r2 = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r1["document_hash"] == r2["document_hash"]

    def test_different_text_different_hash(self):
        r1 = run_prescreen_review("Version 1 text.", self.rule_pack)
        r2 = run_prescreen_review("Version 2 amended text.", self.rule_pack)
        assert r1["document_hash"] != r2["document_hash"]

    def test_evidence_ref_populated_for_project_rules(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        for a in r["required_amendments"]:
            assert a.get("evidence_ref"), f"Missing evidence_ref on: {a['title']}"

    def test_project_mismatches_separated(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert isinstance(r["project_specific_mismatches"], list)
        assert isinstance(r["structural_findings"], dict)

    def test_disclaimer_present(self):
        r = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "pre-screening support only" in r["review_disclaimer"]


# ── LOW confidence behavior ─────────────────────────────────────────────────

class TestLowConfidence:
    def test_short_text_forces_low_confidence(self):
        r = run_prescreen_review("Short.", {"rules": [], "structural_expectations": []})
        assert r["review_confidence"] == "LOW"

    def test_low_confidence_forces_escalated(self):
        r = run_prescreen_review("Short.", {"rules": [], "structural_expectations": []})
        assert r["workflow_state"] == "escalated_for_attention"
        assert r["status_recommendation"] == "Escalate"

    def test_low_confidence_strengthens_disclaimer(self):
        r = run_prescreen_review("Short.", {"rules": [], "structural_expectations": []})
        assert "LOW" in r["review_disclaimer"]
        assert "careful human review" in r["review_disclaimer"]


# ── Workflow vocabulary ─────────────────────────────────────────────────────

class TestVocabulary:
    def test_no_approval_in_workflow_states(self):
        for s in ALLOWED_WORKFLOW_STATES:
            for banned in ("approved", "accepted", "compliant", "passed"):
                assert banned not in s

    def test_no_approval_in_statuses(self):
        for s in ALLOWED_STATUSES:
            for banned in ("Approved", "Accepted", "Compliant", "Passed"):
                assert banned not in s


# ── Payload logging ─────────────────────────────────────────────────────────

class TestPayloadLogging:
    def test_log_creates_file(self, tmp_path, monkeypatch):
        import core.procore.webhook_handler as wh
        monkeypatch.setattr(wh, "_PAYLOAD_LOG", tmp_path / "payloads.jsonl")
        monkeypatch.setattr(wh, "_DATA_DIR", tmp_path)
        event = parse_event(_load_fixture("submittal_created"))
        log_payload(event)
        assert (tmp_path / "payloads.jsonl").exists()


# ── API endpoint ────────────────────────────────────────────────────────────

class TestWebhookEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        reset_idempotency()
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(_load_fixture("project_rule_pack_12345")), encoding="utf-8")
        yield
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def test_valid_submittal_reviewed(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
        r = client.post("/v1/procore/webhook", content=json.dumps(payload),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reviewed"
        assert body["review"]["review_version"] == "2.0"
        assert body["review"]["requires_human_review"] is True
        assert body["review"]["workflow_state"] in ALLOWED_WORKFLOW_STATES
        assert "suppressed_issue_count" in body["review"]

    def test_duplicate_processed_once(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        r1 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r1.json()["status"] == "reviewed"
        r2 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r2.json()["status"] == "already_processed"

    def test_missing_rule_pack_runs_baseline_review(self):
        # T10: a project with no rule pack still receives the baseline/structural
        # review (not an early "no_rule_pack" exit). project_id is preserved on
        # the artifact and project_review_status resolves to UNAVAILABLE.
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = _load_fixture("submittal_created")
        payload["project_id"] = 99999
        payload["metadata"]["delivery_id"] = "evt-no-pack"
        payload["_simulated_swms_text"] = (
            "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
        )
        r = client.post("/v1/procore/webhook", content=json.dumps(payload),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reviewed"
        review = body["review"]
        assert review["project_id"] == "99999"
        assert review["project_review_status"] == "UNAVAILABLE"
        assert review["requires_human_review"] is True

    def test_non_submittal_ignored(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = {"event_type": "budget.updated", "metadata": {"delivery_id": "evt-b"}}
        r = client.post("/v1/procore/webhook", content=json.dumps(payload),
                        headers={"Content-Type": "application/json"})
        assert r.json()["status"] == "ignored"

    def test_invalid_json_400(self):
        from fastapi.testclient import TestClient
        from api.main import app
        r = TestClient(app).post("/v1/procore/webhook", content=b"bad",
                                  headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_legacy_procore_route_not_registered_by_default(self):
        # T1: the deprecated /procore route is disabled unless
        # PROCORE_LEGACY_ROUTE_ENABLED=true. A default deployment must 404,
        # so the legacy route is not a reachable surface. The canonical
        # integration is /v1/procore/webhook.
        from fastapi.testclient import TestClient
        from api.main import app
        r = TestClient(app).post("/procore/webhook", content=b"{}",
                                 headers={"Content-Type": "application/json"})
        assert r.status_code == 404


# ── API client ──────────────────────────────────────────────────────────────

class TestApiClient:
    def test_format_comment(self):
        from core.procore.api_client import format_review_as_comment
        artifact = {
            "status_recommendation": "Return for Amendment",
            "review_confidence": "HIGH",
            "required_amendments": [{"title": "Missing rescue plan", "severity": "mandatory",
                                     "reason": "No rescue plan.", "priority": 1}],
            "structural_findings": {"sequence": "PASS", "hrcw_alignment": "ISSUES FOUND",
                                    "control_credibility": "PASS", "unsupported_controls": "PASS"},
            "review_disclaimer": REVIEW_DISCLAIMER,
        }
        comment = format_review_as_comment(artifact, "SWMS.pdf")
        assert "Return for Amendment" in comment
        assert "Human review is required" in comment

    def test_headers_raise_without_token(self, monkeypatch):
        import core.procore.api_client as m
        monkeypatch.setattr(m, "PROCORE_ACCESS_TOKEN", "")
        with pytest.raises(ValueError):
            m._get_headers()


# ── Resubmission comparison prep ────────────────────────────────────────────

class TestResubmissionPrep:
    def test_identifiers_for_comparison(self):
        r = run_prescreen_review(
            "Scaffold SWMS.", _load_fixture("project_rule_pack_12345"),
            job_id="j1", document_reference="v1.pdf",
            source_surface="submittals", source_item_id="123",
        )
        for key in ("review_run_id", "document_hash", "source_surface",
                     "source_item_id", "reviewed_at", "job_id", "project_id"):
            assert key in r, f"Missing {key}"
