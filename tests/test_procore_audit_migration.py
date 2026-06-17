"""Contract test for migration 008 — Procore audit trail (T6).

The migration cannot be applied in CI, so this guards the hardening invariants
against silent weakening: private schema + RLS, append-only triggers, retention
and customer-deletion functions, service-role-only EXECUTE, and no raw text.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "supabase" / "migrations" / "008_procore_audit.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_table_is_private_with_rls():
    sql = _sql()
    assert "create table if not exists private.procore_audit" in sql
    assert "alter table private.procore_audit enable row level security" in sql


def test_append_only_triggers():
    sql = _sql()
    assert "before update on private.procore_audit" in sql
    assert "before delete on private.procore_audit" in sql
    assert "append-only" in sql


def test_retention_and_deletion_functions():
    sql = _sql()
    assert "function public.purge_procore_audit" in sql
    assert "function public.delete_procore_audit_for_company" in sql
    assert "retention_days" in sql


def test_service_role_only_execute():
    sql = _sql()
    for fn in (
        "public.record_procore_audit(jsonb)",
        "public.purge_procore_audit()",
        "public.delete_procore_audit_for_company(bigint)",
    ):
        assert f"grant execute on function {fn} to service_role" in sql
        assert f"revoke all on function {fn} from public, anon, authenticated" in sql


def test_stores_hash_not_raw_text():
    sql = _sql()
    assert "document_hash" in sql
    assert "never raw swms text" in sql
