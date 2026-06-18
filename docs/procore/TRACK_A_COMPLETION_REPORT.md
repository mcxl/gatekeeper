# Procore Track A - Evidence Checkpoint

**Date:** 2026-06-18
**Current `main` HEAD:** `5e258a1` (merged PR #30)
**Source of truth / plan:** `docs/procore/STAGE3_CERTIFICATION_PLAN_V2.md`
**Scope:** Track A plus the confirmation-independent post-review hardening through PR #30 and the verified Supabase migration apply.

This report replaces the older Track A review snapshot that stopped at PR #24/#25 and `1447c27`. It is an evidence checkpoint for Stage 3 certification readiness. It does not claim the Procore-gated items are complete.

---

## 1. Implemented And Verified

### PR #24 - T1/T2/T3/T4/T10 core hardening
- T1: legacy `/procore` route disabled by default behind `PROCORE_LEGACY_ROUTE_ENABLED`; flat modules remain for direct-import tests.
- T2: `/v1/procore/webhook` is fail-closed by default with `PROCORE_AUTH_SCHEME=unverified`; auth runs before parsing, idempotency, logging, fetch, review, or comment.
- T3: durable idempotency reservation is attempted before side effects; fallback key is `sha256:` + raw body hash when no delivery id is available.
- T4: `/v1/procore/webhook` returns fast `202 accepted` and runs the review pipeline in `BackgroundTasks`; failures are recorded and alerted without raising to Procore.
- T10: baseline/structural review runs even when a project rule pack is missing; project-specific criteria only add to the baseline review.

### PR #25 - T5/T6/T9 audit foundation, local-retention reduction, supply-chain gate
- T5: local JSONL persistence for payloads, reviews, and artifacts is gated behind `PROCORE_LOCAL_JSONL_ENABLED=false` by default.
- T6: migrations `007_procore_webhook_deliveries.sql` and `008_procore_audit.sql` define private-schema delivery/audit storage, RLS, service-role RPCs, retention, and deletion support.
- T9: CI now produces an SBOM artifact and runs `pip-audit`; dependency CVEs found during Track A were patched.

### PR #26 - P0 live write-back blocker resolved
- `PROCORE_LIVE_WRITEBACK_ENABLED` now gates live Procore comment write-back and defaults to `false`.
- Even with live credentials and `retrieval_mode == "live_api"`, no comment is posted unless the flag is explicitly `true`.
- The write-back resource/path itself was not changed and remains `UNVERIFIED` pending Procore confirmation.

### PR #27 - migration 008 hardened before apply
- `private.prevent_procore_audit_mutation()` now pins `search_path`.
- Audit retention/customer deletion no longer depends on the migration owner being `postgres` or `audit_admin`; controlled delete functions use a transaction-local guard.
- Migration 008 was applied after PR #30 alongside migration 007.

### PR #28 - PDF/JWT dependency smoke tests
- Added smoke coverage for real PDF extraction and textless-PDF fallback when `pypdf` is installed.
- Added a real ES256 JWT/JWKS decode smoke through `core.auth.get_current_user`.
- This specifically covers the `pypdf`, `cryptography`, and `python-jose[cryptography]` upgrade risk from PR #25.

### PR #29 - metadata-only audit builder and RPC wiring
- Added a metadata-only Procore audit builder and graceful Supabase RPC writer.
- `/v1/procore/webhook` now attempts `record_procore_audit` after review/comment metadata is known.
- Audit payload excludes raw SWMS text, review prose, amendment reasons, comment body, attachment bytes, and full webhook payloads.
- Audit write degrades to no-op when Supabase is unconfigured or migration 008/RPC is absent.
- This is partial T8: audit-row wiring is done; final write-back resource/path is still Procore-gated.

### PR #30 + Supabase migration apply - evidence refresh and live schema state
- PR #30 refreshed the Stage 3 evidence after PRs #26-#29 and was merged at `5e258a1`.
- Supabase project `rpd-pims` / `nebdpofqglfyfyqqodni` now records `20260618025557 / 007_procore_webhook_deliveries` and `20260618025643 / 008_procore_audit` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:5`, `docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:17-18`).
- Verified private tables now exist with RLS enabled: `private.procore_webhook_deliveries` and `private.procore_audit` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:40-44`).
- Verified public RPC execute is allowed for `service_role` and denied for `anon`/`authenticated` on reserve/audit/purge/company-delete RPCs (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:73-119`).
- Verified audit triggers exist: `no_update_procore_audit` and `no_delete_procore_audit` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:137-155`).
- Verified direct `private` schema `USAGE` is denied for `anon`/`authenticated`/`service_role` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:172-178`).
- Supabase runtime smoke has **not** been run yet; it remains an optional explicit-approval checkpoint because it writes synthetic rows (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:7`).

---

## 2. Verification Status

| Check | Latest result |
|---|---|
| `pytest tests/test_procore_webhook.py` | 74 passed after PR #26 |
| `pytest tests/test_procore_audit_migration.py` | 7 passed after PR #27 |
| `pytest tests/test_dependency_smoke.py` | CI passed after PR #28; local Python skipped PDF smokes where `pypdf` was absent |
| `pytest tests/test_procore_audit.py tests/test_procore_webhook.py` | 79 passed before PR #29 |
| Full suite pre-push hook | Passed for PRs #26, #27, #28, #29 |
| GitHub CI | Passed before merging PRs #26, #27, #28, #29 |
| flake8 | Clean on changed files for each PR |
| pip-audit | Clean after dependency bumps from PR #25 |

---

## 3. Current Data-Handling Position

Use the precise claim:

> Procore remains the system of record. Safe Method retains minimal audit metadata only: event/delivery identifiers, company/project identifiers, a document fingerprint/hash generated from extracted SWMS review text, rule-pack/library versions, status fields, finding and hard-fail counts, and write-back metadata. Safe Method does not retain raw SWMS text, full Procore document content, full webhook payload bodies, attachment bytes, finding prose, comment bodies, or OAuth tokens/secrets in the audit record.

Do **not** use an unqualified "no data retained" claim. The correct position is minimal metadata retained in Supabase audit tables, with raw document content processed transiently for review.

---

## 4. Still Open / Gated

### Procore-gated (`UNVERIFIED`)
1. Webhook auth/signature scheme and exact header/algorithm.
2. OAuth/DMSA grant model and least-privilege scopes.
3. Correct write-back resource/path/API version.
4. `delivery_id` / `ulid` payload location in real webhook deliveries.
5. PM/SM directed visibility or two-tier comment support, if required.

### Ops-gated
1. Set production env safely:
   - `PROCORE_REQUIRE_AUTH=true`
   - `PROCORE_AUTH_SCHEME` set only after Procore confirms the scheme
   - `PROCORE_WEBHOOK_SECRET` / configured signing secret
   - `PROCORE_LEGACY_ROUTE_ENABLED=false`
   - `PROCORE_LIVE_WRITEBACK_ENABLED=false` until write-back resource is verified
   - `PROCORE_LOCAL_JSONL_ENABLED=false`
   - `SUPABASE_SERVICE_ROLE_KEY` for durable idempotency/audit
2. Optional Supabase runtime smoke requires explicit approval because it writes synthetic delivery/audit rows.

### Still not complete
1. T7 OAuth/DMSA token model; static `PROCORE_ACCESS_TOKEN` remains a non-certification-ready interim model.
2. Final T8 write-back resource/path replacement and advisory comment quality gate.
3. Anthropic ZDR / data-processing status and final retention windows, if not already confirmed externally.

---

## 5. Current Target Architecture

```
Procore Submittal event
-> /v1/procore/webhook
-> fail-closed scheme-agnostic auth                  [scheme UNVERIFIED]
-> durable idempotency reservation, pre-side-effect  [migrations applied; payload key UNVERIFIED]
-> 202 Accepted
-> async pipeline: fetch -> extract -> review -> compare -> optional comment
   -> live write-back gated off by default
   -> failures recorded + alerted
   -> metadata-only audit RPC attempted through verified Supabase RPC
-> human Safety Manager decides in Procore
```

The confirmation-independent foundation is now in place. The remaining work is deliberately blocked on Procore answers, production env rollout, and any explicitly approved synthetic Supabase runtime smoke, not more speculative implementation.
