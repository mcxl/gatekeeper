-- 008_procore_audit.sql
-- Minimal, append-only audit trail for Procore SWMS reviews (T6).
--
-- Stores ONLY audit metadata (hashes, rule-pack versions, finding counts,
-- status, write-back metadata, human-override trail) — never raw SWMS text or
-- Procore document content. Supports the "Procore remains system of record /
-- minimal audit metadata retained" data-handling statement.
--
-- Hardening (per docs/procore/STAGE3_CERTIFICATION_PLAN_V2.md §5 + pre-flight):
--   * table lives in a PRIVATE (non-PostgREST-exposed) schema with RLS;
--   * append-only: UPDATE always blocked; DELETE only via the controlled
--     retention/deletion functions (SECURITY DEFINER, run as owner);
--   * writes/purges/deletions go through SECURITY DEFINER functions in public
--     whose EXECUTE is granted to service_role only.

create schema if not exists private;

create table if not exists private.procore_audit (
    id                   bigint generated always as identity primary key,
    record_type          text not null default 'review',  -- 'review' | 'override'
    review_run_id        text,
    delivery_key         text,
    correlation_id       text,
    company_id           bigint,
    project_id           bigint,
    document_hash        text,        -- sha256 of the document; never raw SWMS text
    rule_pack_version    text,
    rule_library_version text,
    project_review_status text,
    status_recommendation text,
    workflow_state       text,
    review_confidence    text,
    finding_count        integer,
    hard_fail_count      integer,
    writeback            jsonb not null default '{}'::jsonb,
    reviewer_override    jsonb,        -- present on record_type = 'override'
    retention_days       integer not null default 365,
    created_at           timestamptz not null default now()
);

alter table private.procore_audit enable row level security;
-- No policies on purpose: only the SECURITY DEFINER functions (owner) and
-- service_role (which bypasses RLS) may touch this table.

create index if not exists idx_procore_audit_company_created
    on private.procore_audit (company_id, created_at desc);
create index if not exists idx_procore_audit_created
    on private.procore_audit (created_at);

-- Append-only: block UPDATE always; block DELETE unless a controlled purge
-- function has enabled the transaction-local delete guard.
-- The retention/deletion functions below set a transaction-local guard before
-- deleting, so controlled purges do not depend on the migration owner's role.
create or replace function private.prevent_procore_audit_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if tg_op = 'UPDATE' then
        raise exception 'private.procore_audit is append-only; UPDATE not permitted.';
    end if;
    if coalesce(current_setting('app.procore_audit_delete_allowed', true), '') <> 'on' then
        raise exception 'private.procore_audit is append-only; DELETE not permitted.';
    end if;
    return old;
end;
$$;

drop trigger if exists no_update_procore_audit on private.procore_audit;
create trigger no_update_procore_audit
    before update on private.procore_audit
    for each row execute function private.prevent_procore_audit_mutation();

drop trigger if exists no_delete_procore_audit on private.procore_audit;
create trigger no_delete_procore_audit
    before delete on private.procore_audit
    for each row execute function private.prevent_procore_audit_mutation();

-- Write one audit record (review or override). SECURITY DEFINER so PostgREST
-- callers reach the private table; EXECUTE restricted to service_role.
create or replace function public.record_procore_audit(p_record jsonb)
returns bigint
language plpgsql
security definer
set search_path = private, public
as $$
declare
    v_id bigint;
begin
    insert into private.procore_audit (
        record_type, review_run_id, delivery_key, correlation_id,
        company_id, project_id, document_hash, rule_pack_version,
        rule_library_version, project_review_status, status_recommendation,
        workflow_state, review_confidence, finding_count, hard_fail_count,
        writeback, reviewer_override, retention_days
    )
    values (
        coalesce(p_record->>'record_type', 'review'),
        p_record->>'review_run_id',
        p_record->>'delivery_key',
        p_record->>'correlation_id',
        (p_record->>'company_id')::bigint,
        (p_record->>'project_id')::bigint,
        p_record->>'document_hash',
        p_record->>'rule_pack_version',
        p_record->>'rule_library_version',
        p_record->>'project_review_status',
        p_record->>'status_recommendation',
        p_record->>'workflow_state',
        p_record->>'review_confidence',
        (p_record->>'finding_count')::integer,
        (p_record->>'hard_fail_count')::integer,
        coalesce(p_record->'writeback', '{}'::jsonb),
        p_record->'reviewer_override',
        coalesce((p_record->>'retention_days')::integer, 365)
    )
    returning id into v_id;
    return v_id;
end;
$$;

-- Retention purge: delete rows past their per-row retention window.
create or replace function public.purge_procore_audit()
returns integer
language plpgsql
security definer
set search_path = private, public
as $$
declare
    v_deleted integer;
begin
    perform set_config('app.procore_audit_delete_allowed', 'on', true);
    delete from private.procore_audit
    where created_at < now() - (retention_days || ' days')::interval;
    perform set_config('app.procore_audit_delete_allowed', 'off', true);
    get diagnostics v_deleted = row_count;
    return v_deleted;
exception
    when others then
        perform set_config('app.procore_audit_delete_allowed', 'off', true);
        raise;
end;
$$;

-- Customer deletion request: remove all audit rows for a company.
create or replace function public.delete_procore_audit_for_company(p_company_id bigint)
returns integer
language plpgsql
security definer
set search_path = private, public
as $$
declare
    v_deleted integer;
begin
    perform set_config('app.procore_audit_delete_allowed', 'on', true);
    delete from private.procore_audit where company_id = p_company_id;
    perform set_config('app.procore_audit_delete_allowed', 'off', true);
    get diagnostics v_deleted = row_count;
    return v_deleted;
exception
    when others then
        perform set_config('app.procore_audit_delete_allowed', 'off', true);
        raise;
end;
$$;

-- Least privilege: only the service role may call these RPCs.
revoke all on function public.record_procore_audit(jsonb) from public, anon, authenticated;
revoke all on function public.purge_procore_audit() from public, anon, authenticated;
revoke all on function public.delete_procore_audit_for_company(bigint) from public, anon, authenticated;
grant execute on function public.record_procore_audit(jsonb) to service_role;
grant execute on function public.purge_procore_audit() to service_role;
grant execute on function public.delete_procore_audit_for_company(bigint) to service_role;
