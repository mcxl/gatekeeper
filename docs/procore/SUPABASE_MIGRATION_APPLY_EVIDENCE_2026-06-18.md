# Supabase Migration Apply Evidence - 2026-06-18

Purpose: non-secret certification evidence for the Procore Stage 3 migration apply and metadata-only verification.

Scope: Supabase project `rpd-pims` / `nebdpofqglfyfyqqodni`. This transcript contains only schema metadata, migration identifiers, function metadata, and privilege booleans. It contains no tokens, service keys, customer data, webhook payloads, SWMS text, or synthetic smoke rows.

Runtime smoke status: **not run**. The runtime smoke remains an explicit-approval checkpoint because it writes synthetic delivery/audit rows.

## Migration History

Source: Supabase MCP `_list_migrations`, project `nebdpofqglfyfyqqodni`.

Relevant result rows:

```json
[
  {"version": "20260618025557", "name": "007_procore_webhook_deliveries"},
  {"version": "20260618025643", "name": "008_procore_audit"}
]
```

## Table And RLS Metadata

Read-only SQL:

```sql
select n.nspname as schema_name, c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where (n.nspname, c.relname) in (
  ('private','procore_webhook_deliveries'),
  ('private','procore_audit')
)
and c.relkind = 'r'
order by 1,2;
```

Result:

```json
[
  {"schema_name": "private", "table_name": "procore_audit", "rls_enabled": true},
  {"schema_name": "private", "table_name": "procore_webhook_deliveries", "rls_enabled": true}
]
```

## Public RPC Metadata And Execute Grants

Read-only SQL:

```sql
select n.nspname as schema_name, p.proname as function_name,
       pg_get_function_identity_arguments(p.oid) as args,
       pg_get_function_result(p.oid) as result_type,
       p.prosecdef as security_definer,
       p.proconfig as config,
       has_function_privilege('service_role', p.oid, 'EXECUTE') as service_role_execute,
       has_function_privilege('anon', p.oid, 'EXECUTE') as anon_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') as authenticated_execute
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where (n.nspname, p.proname) in (
  ('public','reserve_procore_webhook_delivery'),
  ('public','record_procore_audit'),
  ('public','purge_procore_audit'),
  ('public','delete_procore_audit_for_company')
)
order by schema_name, function_name;
```

Relevant result rows:

```json
[
  {
    "schema_name": "public",
    "function_name": "delete_procore_audit_for_company",
    "args": "p_company_id bigint",
    "result_type": "integer",
    "security_definer": true,
    "config": ["search_path=private, public"],
    "service_role_execute": true,
    "anon_execute": false,
    "authenticated_execute": false
  },
  {
    "schema_name": "public",
    "function_name": "purge_procore_audit",
    "args": "",
    "result_type": "integer",
    "security_definer": true,
    "config": ["search_path=private, public"],
    "service_role_execute": true,
    "anon_execute": false,
    "authenticated_execute": false
  },
  {
    "schema_name": "public",
    "function_name": "record_procore_audit",
    "args": "p_record jsonb",
    "result_type": "bigint",
    "security_definer": true,
    "config": ["search_path=private, public"],
    "service_role_execute": true,
    "anon_execute": false,
    "authenticated_execute": false
  },
  {
    "schema_name": "public",
    "function_name": "reserve_procore_webhook_delivery",
    "args": "p_delivery_key text, p_correlation_id text",
    "result_type": "boolean",
    "security_definer": true,
    "config": ["search_path=private, public"],
    "service_role_execute": true,
    "anon_execute": false,
    "authenticated_execute": false
  }
]
```

## Audit Trigger Metadata

Read-only SQL:

```sql
select event_object_schema, event_object_table, trigger_name,
       action_timing, event_manipulation, action_statement
from information_schema.triggers
where event_object_schema = 'private'
  and event_object_table in ('procore_webhook_deliveries','procore_audit')
order by event_object_table, trigger_name, event_manipulation;
```

Result:

```json
[
  {
    "event_object_schema": "private",
    "event_object_table": "procore_audit",
    "trigger_name": "no_delete_procore_audit",
    "action_timing": "BEFORE",
    "event_manipulation": "DELETE",
    "action_statement": "EXECUTE FUNCTION private.prevent_procore_audit_mutation()"
  },
  {
    "event_object_schema": "private",
    "event_object_table": "procore_audit",
    "trigger_name": "no_update_procore_audit",
    "action_timing": "BEFORE",
    "event_manipulation": "UPDATE",
    "action_statement": "EXECUTE FUNCTION private.prevent_procore_audit_mutation()"
  }
]
```

## Private Schema Direct Privileges

Read-only SQL:

```sql
select role_name,
       has_schema_privilege(role_name, 'private', 'USAGE') as private_usage,
       has_schema_privilege(role_name, 'private', 'CREATE') as private_create
from (values ('service_role'), ('anon'), ('authenticated'), ('postgres')) roles(role_name)
order by role_name;
```

Result:

```json
[
  {"role_name": "anon", "private_usage": false, "private_create": false},
  {"role_name": "authenticated", "private_usage": false, "private_create": false},
  {"role_name": "postgres", "private_usage": true, "private_create": true},
  {"role_name": "service_role", "private_usage": false, "private_create": false}
]
```

Interpretation: application access is through the public `SECURITY DEFINER` RPCs, not direct private schema access. The private trigger function is not a public API surface.
