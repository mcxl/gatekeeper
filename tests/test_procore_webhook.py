"""
tests/test_procore_webhook.py — Tests for Procore webhook spike Phase 1.
"""

import hashlib
import hmac
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.procore.webhook_handler import (
    ALLOWED_STATUSES,
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
        assert event.resource_id == 98765
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
        attachments = extract_submittal_attachments(event)
        assert len(attachments) == 0


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


# ── Pre-screen review ──────────────────────────────────────────────────────

class TestPrescreenReview:
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

    def test_review_artifact_structure(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert "review_summary" in result
        assert "status_recommendation" in result
        assert "required_amendments" in result
        assert "project_specific_mismatches" in result
        assert "structural_findings" in result
        assert "review_confidence" in result
        assert "review_disclaimer" in result
        assert "requires_human_review" in result

    def test_requires_human_review_always_true(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["requires_human_review"] is True

    def test_status_uses_allowed_vocabulary(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["status_recommendation"] in ALLOWED_STATUSES

    def test_status_never_uses_approved(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        full_text = json.dumps(result).lower()
        for banned in ("approved", "accepted", "compliant", "passed"):
            # Allow "No issues detected" but not standalone "passed"
            assert f'"{banned}"' not in full_text, f"Banned term '{banned}' found in output"

    def test_max_amendments_enforced(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert len(result["required_amendments"]) <= MAX_REQUIRED_AMENDMENTS

    def test_disclaimer_present(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["review_disclaimer"] == REVIEW_DISCLAIMER

    def test_rescue_plan_flagged(self):
        """Scaffold SWMS without rescue plan should trigger amendment."""
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        titles = [a["title"] for a in result["required_amendments"]]
        assert any("rescue plan" in t.lower() for t in titles)

    def test_scaffold_design_flagged(self):
        """Scaffold SWMS without design reference should trigger amendment."""
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        titles = [a["title"] for a in result["required_amendments"]]
        assert any("scaffold design" in t.lower() for t in titles)

    def test_filler_controls_detected(self):
        result = run_prescreen_review(self.swms_text, self.rule_pack)
        assert result["structural_findings"]["control_credibility"] == "ISSUES FOUND"

    def test_clean_swms_passes_structural(self):
        clean = (
            "SWMS - Office Painting\n"
            "HRCW: Not applicable\n"
            "Task 1: Prepare and clean surfaces\n"
            "Controls: Wet areas barricaded. P2 mask during sanding.\n"
            "Task 2: Apply two-coat acrylic system\n"
            "Controls: Ventilation maintained. SDS on site.\n"
        )
        result = run_prescreen_review(clean, {"rules": [], "structural_expectations": []})
        assert result["structural_findings"]["control_credibility"] == "No issues detected"
        assert result["requires_human_review"] is True

    def test_empty_rule_pack_produces_valid_artifact(self):
        result = run_prescreen_review("Some SWMS text here.", {"rules": [], "structural_expectations": []})
        assert result["status_recommendation"] in ALLOWED_STATUSES
        assert result["requires_human_review"] is True


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
        # Set up rule pack for project 12345
        rule_packs_dir = Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"
        rule_packs_dir.mkdir(parents=True, exist_ok=True)
        rule_pack = _load_fixture("project_rule_pack_12345")
        (rule_packs_dir / "project_12345.json").write_text(
            json.dumps(rule_pack), encoding="utf-8"
        )
        yield
        # Cleanup
        (rule_packs_dir / "project_12345.json").unlink(missing_ok=True)

    def test_valid_submittal_reviewed(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = (
            "SWMS - Scaffold Erection Bay 3\n"
            "Task 1: Erect scaffold to level 3 using harness and edge protection.\n"
            "Controls: Install edge protection before access. Follow SWMS.\n"
        )

        response = client.post(
            "/v1/procore/webhook",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "reviewed"
        assert body["review"]["requires_human_review"] is True
        assert body["review"]["status_recommendation"] in ALLOWED_STATUSES

    def test_duplicate_processed_once(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["_simulated_swms_text"] = "Some SWMS text for scaffold work."

        # First call
        r1 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r1.status_code == 200
        assert r1.json()["status"] == "reviewed"

        # Second call — same delivery_id
        r2 = client.post("/v1/procore/webhook", content=json.dumps(payload),
                         headers={"Content-Type": "application/json"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_processed"

    def test_missing_rule_pack(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = _load_fixture("submittal_created")
        payload["project_id"] = 99999  # no rule pack for this
        payload["metadata"]["delivery_id"] = "evt-missing-pack"
        payload["_simulated_swms_text"] = "text"

        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        assert response.json()["status"] == "no_rule_pack"

    def test_non_submittal_ignored(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        payload = {"event_type": "budget.updated", "metadata": {"delivery_id": "evt-budget"}}
        response = client.post("/v1/procore/webhook", content=json.dumps(payload),
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_invalid_json_returns_400(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post("/v1/procore/webhook", content=b"not json",
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 400
