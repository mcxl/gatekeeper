from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "pims_dashboard_rpd.html").read_text(encoding="utf-8")
MIGRATION = (ROOT / "pims" / "migrations" / "2026-08-31_pims_rpd_cleanup.sql").read_text(encoding="utf-8")


def test_live_register_uses_fifty_rows_and_all_open_default():
    assert "const ALL_OBS_PAGE_SIZE = 50;" in HTML
    assert "let openActionsScope = 'all'" in HTML
    assert 'id="openActionsScopeAll"' in HTML
    assert 'class="period-btn active" id="openActionsScopeAll"' in HTML


def test_dashboard_has_stable_sequence_photo_manager_and_ccvs_helpers():
    assert "function buildDerivedSequenceMap()" in HTML
    assert "function seqFor(o)" in HTML
    assert "function photoCell(o)" in HTML
    assert "function projectManagerFor(o)" in HTML
    assert "PROJECT_MANAGER_BY_ADDRESS" in HTML
    assert "project_manager" in HTML
    assert "category: o.ccvs_category, confidence: o.ccvs_confidence" in HTML
    assert "ccvs-unassigned" in HTML


def test_ongoing_due_label_has_high_contrast_pill():
    assert ".due-ongoing" in HTML
    assert "background:#dbeafe" in HTML
    assert "color:#1e3a8a" in HTML


def test_manager_migration_is_additive_and_idempotent():
    assert "ADD COLUMN IF NOT EXISTS project_manager text" in MIGRATION
    assert "WHERE a.id = c.id" in MIGRATION
    assert "project_manager IS NULL OR btrim(a.project_manager) = ''" in MIGRATION
    for manager in ("Yas N", "David O", "Jim G", "David O / DO"):
        assert manager in MIGRATION
