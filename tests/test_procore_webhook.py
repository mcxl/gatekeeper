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


@pytest.fixture(autouse=True)
def _in_memory_idempotency(monkeypatch):
    # Default to the in-memory idempotency path for deterministic offline tests;
    # the durable-path tests opt back in by setting SUPABASE_SERVICE_ROLE_KEY.
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    # Neutralise the durable status writer so background tasks never hit Supabase.
    import core.job_state as js

    async def _noop_record_state(*a, **k):
        return None

    monkeypatch.setattr(js, "record_state", _noop_record_state)


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

    @pytest.fixture(autouse=True)
    def _bypass_auth(self, monkeypatch):
        # These tests exercise review logic, not auth. Run with auth bypassed;
        # fail-closed auth behaviour is covered in TestWebhookAuth (T2).
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "false")

    def test_valid_submittal_accepted_202(self):
        # T4: heavy review runs async; the endpoint returns 202 quickly.
        # Review-content assertions live in TestProcorePipeline.
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
        r = client.post("/v1/procore/webhook", content=json.dumps(payload),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

    def test_duplicate_processed_once(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        r1 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r1.status_code == 202
        assert r1.json()["status"] == "accepted"
        r2 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r2.json()["status"] == "already_processed"

    def test_missing_rule_pack_accepted_202(self):
        # T10/T4: a project with no rule pack is still accepted (202); the
        # baseline review runs in the background (see TestProcorePipeline for the
        # project_review_status=UNAVAILABLE assertion).
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
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

    def test_non_submittal_accepted_202(self):
        # Cheap gating now happens in the background; the endpoint still 202s.
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        payload = {"event_type": "budget.updated", "metadata": {"delivery_id": "evt-b"}}
        r = client.post("/v1/procore/webhook", content=json.dumps(payload),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

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


# ── Webhook auth (T2) ────────────────────────────────────────────────────────

class TestWebhookAuth:
    """T2: fail-closed, scheme-agnostic auth on /v1/procore/webhook."""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_idempotency()
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(_load_fixture("project_rule_pack_12345")), encoding="utf-8")
        yield
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def _client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_fail_closed_unverified_rejects_with_no_side_effects(self, monkeypatch):
        # Default posture: auth required + scheme unverified -> reject all,
        # before any side effect runs.
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "true")
        monkeypatch.setenv("PROCORE_AUTH_SCHEME", "unverified")
        monkeypatch.setenv("PROCORE_WEBHOOK_SECRET", "s3cr3t")

        import core.procore.webhook_handler as wh
        import core.procore.prescreen_reviewer as pr
        import core.procore.api_client as ac
        calls = []
        monkeypatch.setattr(wh, "log_payload", lambda *a, **k: calls.append("log_payload"))
        monkeypatch.setattr(pr, "run_prescreen_review", lambda *a, **k: calls.append("review"))
        monkeypatch.setattr(ac, "fetch_attachment", lambda *a, **k: calls.append("fetch"))
        monkeypatch.setattr(ac, "post_submittal_comment", lambda *a, **k: calls.append("comment"))

        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        r = self._client().post("/v1/procore/webhook", content=json.dumps(payload),
                                headers={"Content-Type": "application/json"})
        assert r.status_code == 401
        assert calls == []  # no side effects executed before rejection

    def test_no_secret_rejects(self, monkeypatch):
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "true")
        monkeypatch.setenv("PROCORE_AUTH_SCHEME", "authorization_bearer")
        monkeypatch.delenv("PROCORE_WEBHOOK_SECRET", raising=False)
        r = self._client().post("/v1/procore/webhook", content=b"{}",
                                headers={"Content-Type": "application/json"})
        assert r.status_code == 401

    def test_bad_bearer_rejects(self, monkeypatch):
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "true")
        monkeypatch.setenv("PROCORE_AUTH_SCHEME", "authorization_bearer")
        monkeypatch.setenv("PROCORE_WEBHOOK_SECRET", "s3cr3t")
        r = self._client().post("/v1/procore/webhook", content=b"{}",
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_valid_bearer_proceeds(self, monkeypatch):
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "true")
        monkeypatch.setenv("PROCORE_AUTH_SCHEME", "authorization_bearer")
        monkeypatch.setenv("PROCORE_WEBHOOK_SECRET", "s3cr3t")
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = (
            "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
        )
        r = self._client().post(
            "/v1/procore/webhook", content=json.dumps(payload),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer s3cr3t"})
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

    def test_valid_hmac_proceeds(self, monkeypatch):
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "true")
        monkeypatch.setenv("PROCORE_AUTH_SCHEME", "hmac_sha256")
        monkeypatch.setenv("PROCORE_WEBHOOK_SECRET", "s3cr3t")
        monkeypatch.setenv("PROCORE_SIGNATURE_HEADER", "X-Procore-Signature")
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        body = json.dumps(payload).encode()
        sig = hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
        r = self._client().post(
            "/v1/procore/webhook", content=body,
            headers={"Content-Type": "application/json",
                     "X-Procore-Signature": sig})
        assert r.status_code == 202


# ── Durable idempotency (T3) ─────────────────────────────────────────────────

class TestWebhookIdempotency:
    """T3: durable reservation before side effects; body-hash fallback."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        reset_idempotency()
        monkeypatch.setenv("PROCORE_REQUIRE_AUTH", "false")
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(_load_fixture("project_rule_pack_12345")), encoding="utf-8")
        yield
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def _client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_no_delivery_id_dedupes_via_body_hash(self):
        # A payload with no delivery_id must still de-duplicate on the body hash
        # (previously such events were never de-duplicated).
        payload = _load_fixture("submittal_created")
        payload.get("metadata", {}).pop("delivery_id", None)
        payload.pop("delivery_id", None)
        payload["_simulated_swms_text"] = "text"
        body = json.dumps(payload)
        client = self._client()
        r1 = client.post("/v1/procore/webhook", content=body,
                         headers={"Content-Type": "application/json"})
        r2 = client.post("/v1/procore/webhook", content=body,
                         headers={"Content-Type": "application/json"})
        assert r1.json()["status"] == "accepted"
        assert r2.json()["status"] == "already_processed"

    def test_reservation_runs_before_log_payload(self, monkeypatch):
        # On a duplicate, log_payload must NOT run again — reservation precedes it.
        import core.procore.webhook_handler as wh
        logged = []
        real = wh.log_payload
        monkeypatch.setattr(wh, "log_payload", lambda e: (logged.append(1), real(e))[1])
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        body = json.dumps(payload)
        client = self._client()
        client.post("/v1/procore/webhook", content=body,
                    headers={"Content-Type": "application/json"})
        client.post("/v1/procore/webhook", content=body,
                    headers={"Content-Type": "application/json"})
        assert len(logged) == 1  # logged once; duplicate rejected before logging

    def test_durable_path_used_when_supabase_configured(self, monkeypatch):
        import core.procore.webhook_handler as wh
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
        seen = set()

        def fake_rpc(key, cid):
            if key in seen:
                return False
            seen.add(key)
            return True

        monkeypatch.setattr(wh, "_reserve_supabase", fake_rpc)
        assert wh.reserve_delivery("k1") is True
        assert wh.reserve_delivery("k1") is False

    def test_durable_falls_back_to_memory_on_error(self, monkeypatch):
        import core.procore.webhook_handler as wh
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")

        def boom(key, cid):
            raise RuntimeError("network down")

        monkeypatch.setattr(wh, "_reserve_supabase", boom)
        reset_idempotency()
        assert wh.reserve_delivery("k2") is True   # fell back to memory
        assert wh.reserve_delivery("k2") is False  # memory de-dupes


# ── Async pipeline (T4) ──────────────────────────────────────────────────────

class TestProcorePipeline:
    """T4: the background pipeline returns the review outcome and surfaces
    failures (alert + recorded) instead of raising to the caller."""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_idempotency()
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(_load_fixture("project_rule_pack_12345")), encoding="utf-8")
        yield
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def _run(self, payload):
        import asyncio
        from api.main import _process_procore_v1_webhook
        event = parse_event(payload)
        return asyncio.run(_process_procore_v1_webhook(payload, event, "corr-test"))

    def test_pipeline_reviews_valid_submittal(self):
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = (
            "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
        )
        result = self._run(payload)
        assert result["status"] == "reviewed"
        assert result["review"]["review_version"] == "2.0"
        assert result["review"]["requires_human_review"] is True

    def test_pipeline_baseline_without_rule_pack_is_unavailable(self):
        payload = _load_fixture("submittal_created")
        payload["project_id"] = 99999
        payload["metadata"]["delivery_id"] = "evt-no-pack-pipe"
        payload["_simulated_swms_text"] = "Scaffold SWMS with harness. Follow SWMS.\n"
        result = self._run(payload)
        assert result["status"] == "reviewed"
        assert result["review"]["project_id"] == "99999"
        assert result["review"]["project_review_status"] == "UNAVAILABLE"

    def test_pipeline_ignores_non_submittal(self):
        result = self._run({"event_type": "budget.updated",
                            "metadata": {"delivery_id": "evt-ignore"}})
        assert result["status"] == "ignored"

    def test_pipeline_failure_is_alerted_not_raised(self, monkeypatch):
        import core.procore.prescreen_reviewer as pr
        import core.procore.alerts as alerts
        alerted = []
        monkeypatch.setattr(alerts, "alert_failure",
                            lambda msg, cid="": alerted.append((msg, cid)))

        def boom(*a, **k):
            raise RuntimeError("review engine down")

        monkeypatch.setattr(pr, "run_prescreen_review", boom)
        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "text"
        result = self._run(payload)  # must not raise
        assert result["status"] == "failed"
        assert "review engine down" in result["error"]
        assert len(alerted) == 1


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
