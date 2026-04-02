"""
tests/test_procore_webhook.py — Tests for Procore review-first workflow.
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
from core.procore.prescreen_reviewer import run_prescreen_review

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "procore"


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
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
        payload = _load_fixture("submittal_created")
        event = parse_event(payload)
        assert event.event_type == "submittals.submittal_logs.created"
        assert event.project_id == 12345
        assert event.delivery_id == "evt-abc123-def456"

    def test_extract_pdf_attachments(self):
        payload = _load_fixture("submittal_created")
        event = parse_event(payload)
        attachments = extract_submittal_attachments(event)
        assert len(attachments) == 1
        assert attachments[0].filename == "SWMS_Scaffold_Bay3_v1.pdf"

    def test_no_attachments(self):
        payload = {"event_type": "test", "data": {}, "metadata": {}}
        event = parse_event(payload)
        assert len(extract_submittal_attachments(event)) == 0


# ── Idempotency ─────────────────────────────────────────────────────────────

class TestIdempotency:
    def setup_method(self):
        reset_idempotency()

    def test_first_delivery_not_duplicate(self):
        assert not is_duplicate("evt-001")

    def test_second_delivery_is_duplicate(self):
        is_duplicate("evt-002")
        assert is_duplicate("evt-002")

    def test_different_ids_not_duplicate(self):
        is_duplicate("evt-003")
        assert not is_duplicate("evt-004")


# ── Phase 2 pre-screen review ──────────────────────────────────────────────

class TestPrescreenReviewPhase2:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.rule_pack = _load_fixture("project_rule_pack_12345")
        self.swms_text = (
            "SWMS - Scaffold Erection Bay 3\n"
            "Task 1: Erect scaffold to level 3\n"
            "Hazard: Fall from height\n"
            "Controls: Install edge protection. Use harness with double lanyard.\n"
            "Follow SWMS at all times.\n"
            "Task 2: Install guardrails and platforms\n"
            "Controls: Supervisor to monitor work progress.\n"
            "Task 3: Inspect and hand over scaffold\n"
            "Task 4: Demobilise scaffold and clear site\n"
        )

    def test_review_version_is_2(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["review_version"] == "2.0"

    def test_workflow_state_in_allowed(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["workflow_state"] in ALLOWED_WORKFLOW_STATES

    def test_status_in_allowed(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["status_recommendation"] in ALLOWED_STATUSES

    def test_requires_human_review_always_true(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["requires_human_review"] is True

    def test_status_never_uses_approval_language(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        full_text = json.dumps(result).lower()
        for banned in ("approved", "accepted", "compliant"):
            assert f'"{banned}"' not in full_text

    def test_max_amendments_enforced(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert len(result["required_amendments"]) <= MAX_REQUIRED_AMENDMENTS

    def test_amendments_have_priority(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        for a in result["required_amendments"]:
            assert "priority" in a
            assert isinstance(a["priority"], int)

    def test_amendments_prioritized_mandatory_first(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        amendments = result["required_amendments"]
        if len(amendments) >= 2:
            # All mandatory should come before advisory
            mandatory_idx = [i for i, a in enumerate(amendments) if a["severity"] == "mandatory"]
            advisory_idx = [i for i, a in enumerate(amendments) if a["severity"] == "advisory"]
            if mandatory_idx and advisory_idx:
                assert max(mandatory_idx) < min(advisory_idx)

    def test_project_mismatches_separated_from_structural(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "project_specific_mismatches" in result
        assert "structural_findings" in result
        assert isinstance(result["project_specific_mismatches"], list)
        assert isinstance(result["structural_findings"], dict)

    def test_document_fingerprint_present(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "document_fingerprint" in result
        assert len(result["document_fingerprint"]) == 16

    def test_document_fingerprint_stable(self):
        r1 = run_prescreen_review(self.swms_text, self.rule_pack)
        r2 = run_prescreen_review(self.swms_text, self.rule_pack)
        assert r1["document_fingerprint"] == r2["document_fingerprint"]

    def test_reviewed_at_present(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "reviewed_at" in result
        assert "T" in result["reviewed_at"]

    def test_job_id_and_document_ref_passed_through(self):
        result = run_prescreen_review(
            self.swms_text, self.rule_pack,
            job_id="test-123", document_reference="SWMS_v1.pdf",
        )
        assert result["job_id"] == "test-123"
        assert result["document_reference"] == "SWMS_v1.pdf"

    def test_disclaimer_present(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["review_disclaimer"] == REVIEW_DISCLAIMER

    def test_rescue_plan_flagged(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        titles = [a["title"] for a in result["required_amendments"]]
        assert any("rescue plan" in t.lower() for t in titles)

    def test_filler_controls_detected(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["structural_findings"]["control_credibility"] == "ISSUES FOUND"

    def test_clean_swms_reviewed_pending_human(self):
        clean = (
            "SWMS - Office Painting\n"
            "HRCW: Not applicable\n"
            "Task 1: Prepare surfaces\nControls: Wet areas barricaded.\n"
            "Task 2: Apply paint\nControls: Ventilation maintained.\n"
        )
        result = run_prescreen_review(clean, {"rules": [], "structural_expectations": []})
        assert result["workflow_state"] == "reviewed_pending_human"
        assert result["requires_human_review"] is True

    def test_missing_rule_pack_noted(self):
        result = run_prescreen_review(
            "Some SWMS text for scaffold.", {"rules": [], "structural_expectations": []},
        )
        assert result["project_rule_pack_available"] is False
        assert "structural review only" in result["review_summary"].lower()

    def test_empty_rule_pack_valid_artifact(self):
        result = run_prescreen_review("SWMS text.", {"rules": [], "structural_expectations": []})
        assert result["review_version"] == "2.0"
        assert result["requires_human_review"] is True
        assert result["workflow_state"] in ALLOWED_WORKFLOW_STATES


# ── Workflow state vocabulary ───────────────────────────────────────────────

class TestWorkflowStateVocabulary:
    def test_no_approval_states(self):
        for state in ALLOWED_WORKFLOW_STATES:
            assert "approved" not in state
            assert "accepted" not in state
            assert "compliant" not in state
            assert "passed" not in state

    def test_no_approval_statuses(self):
        for status in ALLOWED_STATUSES:
            assert "Approved" not in status
            assert "Accepted" not in status
            assert "Compliant" not in status


# ── Payload logging ─────────────────────────────────────────────────────────

class TestPayloadLogging:
    def test_log_payload_creates_file(self, tmp_path, monkeypatch):
        import core.procore.webhook_handler as wh
        monkeypatch.setattr(wh, "_PAYLOAD_LOG", tmp_path / "payloads.jsonl")
        monkeypatch.setattr(wh, "_DATA_DIR", tmp_path)

        payload = _load_fixture("submittal_created")
        event = parse_event(payload)
        log_payload(event)

        log_file = tmp_path / "payloads.jsonl"
        assert log_file.exists()
        record = json.loads(log_file.read_text().strip())
        assert record["delivery_id"] == "evt-abc123-def456"


# ── API endpoint ────────────────────────────────────────────────────────────

class TestWebhookEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        reset_idempotency()
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        rule_pack = _load_fixture("project_rule_pack_12345")
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(rule_pack), encoding="utf-8"
        )
        yield
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def test_valid_submittal_reviewed(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = (
            "SWMS - Scaffold Erection Bay 3\n"
            "Task 1: Erect scaffold to level 3 using harness.\nControls: Follow SWMS.\n"
        )

        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "reviewed"
        assert body["review"]["review_version"] == "2.0"
        assert body["review"]["requires_human_review"] is True
        assert body["review"]["workflow_state"] in ALLOWED_WORKFLOW_STATES

    def test_duplicate_processed_once(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "Some SWMS text."

        r1 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r1.json()["status"] == "reviewed"

        r2 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r2.json()["status"] == "already_processed"

    def test_missing_rule_pack(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["project_id"] = 99999
        payload["metadata"]["delivery_id"] = "evt-missing-pack"
        payload["_simulated_swms_text"] = "text"

        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        assert response.json()["status"] == "no_rule_pack"

    def test_non_submittal_ignored(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = {"event_type": "budget.updated", "metadata": {"delivery_id": "evt-budget"}}
        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        assert response.json()["status"] == "ignored"

    def test_invalid_json_returns_400(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post("/v1/procore/webhook", content=b"not json",
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 400

    def test_retrieval_mode_in_response(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["metadata"]["delivery_id"] = "evt-retrieval-mode"
        payload["_simulated_swms_text"] = "Scaffold SWMS with harness."

        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        body = response.json()
        assert body["retrieval_mode"] == "simulated"
        assert body["comment_posted"] is False


# ── API client unit tests ───────────────────────────────────────────────────

class TestApiClient:
    def test_format_review_as_comment(self):
        from core.procore.api_client import format_review_as_comment
        artifact = {
            "status_recommendation": "Return for Amendment",
            "review_confidence": "HIGH",
            "required_amendments": [
                {"title": "Missing rescue plan", "severity": "mandatory",
                 "reason": "No rescue plan found.", "priority": 1},
            ],
            "structural_findings": {
                "sequence": "No issues detected",
                "hrcw_alignment": "ISSUES FOUND",
                "control_credibility": "No issues detected",
                "unsupported_controls": "No issues detected",
            },
            "review_disclaimer": REVIEW_DISCLAIMER,
        }
        comment = format_review_as_comment(artifact, "SWMS_Test.pdf")
        assert "Return for Amendment" in comment
        assert "Human review is required" in comment
        for banned in ("Approved", "Accepted", "Compliant"):
            assert banned not in comment

    def test_get_headers_raises_without_token(self, monkeypatch):
        import core.procore.api_client as client_mod
        monkeypatch.setattr(client_mod, "PROCORE_ACCESS_TOKEN", "")
        with pytest.raises(ValueError, match="PROCORE_ACCESS_TOKEN"):
            client_mod._get_headers()

    def test_get_headers_includes_token(self, monkeypatch):
        import core.procore.api_client as client_mod
        monkeypatch.setattr(client_mod, "PROCORE_ACCESS_TOKEN", "test-token")
        monkeypatch.setattr(client_mod, "PROCORE_COMPANY_ID", "99")
        headers = client_mod._get_headers()
        assert headers["Authorization"] == "Bearer test-token"


# ── Config validation ───────────────────────────────────────────────────────

class TestConfigValidation:
    def test_webhook_secret_env_var(self):
        import api.main as main_mod
        assert hasattr(main_mod, "_PROCORE_WEBHOOK_SECRET")

    def test_rule_packs_dir_createable(self):
        import api.main as main_mod
        main_mod._PROCORE_RULE_PACKS_DIR.mkdir(parents=True, exist_ok=True)
        assert main_mod._PROCORE_RULE_PACKS_DIR.exists()


# ── Resubmission comparison preparation ────────────────────────────────────

class TestResubmissionPrep:
    def test_artifact_has_identifiers_for_comparison(self):
        """Phase 2 artifact should have enough identifiers for later version comparison."""
        rule_pack = _load_fixture("project_rule_pack_12345")
        result = run_prescreen_review(
            "Scaffold SWMS with harness.", rule_pack,
            job_id="procore-12345-98765",
            document_reference="SWMS_v1.pdf",
        )
        assert result["job_id"]
        assert result["project_id"]
        assert result["document_reference"]
        assert result["document_fingerprint"]
        assert result["reviewed_at"]

    def test_different_text_different_fingerprint(self):
        rule_pack = _load_fixture("project_rule_pack_12345")
        r1 = run_prescreen_review("SWMS version 1 text.", rule_pack)
        r2 = run_prescreen_review("SWMS version 2 text with amendments.", rule_pack)
        assert r1["document_fingerprint"] != r2["document_fingerprint"]
