-- 007_procore_webhook_deliveries.sql
-- Durable idempotency for Procore webhook deliveries (T3).
--
-- Hardening (per docs/procore/STAGE3_CERTIFICATION_PLAN_V2.md pre-flight):
--   * the table lives in a PRIVATE schema (not exposed via PostgREST), so it
--     is not readable/writable through the Data API by anon/authenticated;
--   * reservation goes through a SECURITY DEFINER function in `public` whose
--     EXECUTE is granted to `service_role` only (revoked from anon/authenticated);
--   * RLS is enabled on the table as defense-in-depth (the definer function and
--     service_role are the only callers).

create schema if not exists private;

create table if not exists private.procore_webhook_deliveries (
    delivery_key    text primary key,
    correlation_id  text,
    first_seen_at   timestamptz not null default now(),
    last_seen_at    timestamptz not null default now(),
    duplicate_count integer     not null default 0
);

alter table private.procore_webhook_deliveries enable row level security;
-- No policies on purpose: only the SECURITY DEFINER function (owner) and
-- service_role (which bypasses RLS) may touch this table.

create index if not exists idx_procore_webhook_deliveries_first_seen
    on private.procore_webhook_deliveries (first_seen_at desc);

-- Atomic reserve: insert wins -> true (new); unique_violation -> false (dup).
create or replace function public.reserve_procore_webhook_delivery(
    p_delivery_key   text,
    p_correlation_id text default ''
)
returns boolean
language plpgsql
security definer
set search_path = private, public
as $$
begin
    insert into private.procore_webhook_deliveries (delivery_key, correlation_id)
    values (p_delivery_key, p_correlation_id);
    return true;            -- newly reserved -> caller proceeds
exception
    when unique_violation then
        update private.procore_webhook_deliveries
        set last_seen_at    = now(),
            duplicate_count = duplicate_count + 1
        where delivery_key = p_delivery_key;
        return false;        -- duplicate -> caller skips side effects
end;
$$;

-- Least privilege: only the service role may call the reserve RPC.
revoke all on function public.reserve_procore_webhook_delivery(text, text) from public;
revoke all on function public.reserve_procore_webhook_delivery(text, text) from anon, authenticated;
grant execute on function public.reserve_procore_webhook_delivery(text, text) to service_role;
