# Procore Certification Plan V2 — Evidence Cleanup + Procore Confirmation Pack

**Author:** Claude (read-only planning pass; no code/notes edited, nothing committed)
**Date:** 2026-06-17
**Source of truth:** [STAGE3_CERTIFICATION_REVIEW.md](STAGE3_CERTIFICATION_REVIEW.md) (verdict: ACCEPT WITH CHANGES)
**Rule:** every claim carries `file:line` (verified against current HEAD) or an official docs URL; gaps marked `UNVERIFIED`.

## Status Update - 2026-06-25

This plan has now advanced beyond the original read-only planning state. `main` includes PRs #26-#32, and Supabase migrations 007/008 have been applied and verified:

- **PR #26:** live write-back is gated by `PROCORE_LIVE_WRITEBACK_ENABLED=false` by default.
- **PR #27:** migration 008 is hardened with pinned `search_path` and a controlled delete guard.
- **PR #28:** PDF/JWT dependency smoke coverage exists for the upgraded extraction/auth dependencies.
- **PR #29:** metadata-only Procore audit payload builder and graceful Supabase RPC wiring are implemented.
- **PR #30:** Stage 3 evidence was refreshed after hardening and merged at `5e258a1`.
- **PR #32:** RulePackV1.1 was implemented and merged at `05d20a2`. It provides a closed schema, fail-closed pack loading, deterministic criterion evaluations, stable issue mapping, production draft blocking, and write-back gating on `project_review_status=AVAILABLE`.
- **Supabase apply:** project `rpd-pims` / `nebdpofqglfyfyqqodni` records `20260618025557 / 007_procore_webhook_deliveries` and `20260618025643 / 008_procore_audit` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:5`, `docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:17-18`).
- **Supabase verification:** private tables exist with RLS enabled (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:40-44`); public RPC execute is allowed for `service_role` and denied for `anon`/`authenticated` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:73-119`); audit update/delete triggers exist (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:137-155`); direct `private` schema `USAGE` is denied for `anon`/`authenticated`/`service_role` (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:172-178`).

The remaining blockers are still real: Procore auth/signature scheme, OAuth/DMSA grant/scopes, write-back resource/path/API version, and `delivery_id`/`ulid` payload location remain `UNVERIFIED`; production env rollout remains `OPS-GATED`; Supabase runtime smoke remains optional and requires explicit approval because it writes synthetic rows. RulePackV1.1 is implemented, but a real customer/project pack still requires human-authored criteria, genuine approval provenance, and controlled deployment.

---

## Deliverable 1 — Stale `file:line` Correction Table

Verified against current working tree this session. The six action notes' **conclusions remain valid**; the citations drifted because the notes were authored against an earlier revision. None of these corrections changes a verdict — but they must be re-pinned before any note is rendered into a Procore submission, because reviewers read literally.

> Recommendation: **do not edit the notes yet** (read-only mode). Apply this table as a single docs commit once approved.

| Note | Stale citation | Corrected (HEAD) | Conclusion changes? |
|---|---|---|---|
| 01 | `webhook_handler.py:147-148` = `path.write_text(json.dumps(record, indent=2), ...)` | `webhook_handler.py:147-148` = `with open(_PAYLOAD_LOG, "a"...)` / `f.write(json.dumps(record, ensure_ascii=False) + "\n")` | No — file persistence side-effect still real |
| 01 | `main.py:1330` = `payload_log = log_payload(event)` | `main.py:1330` = `log_payload(event)` (no assignment) | No |
| 01 | tests `test_procore_webhook.py:342,358-363,373-375,382-384,389` | **UNVERIFIED** — not re-opened this pass; re-pin before use | No |
| 02 | `main.py:1315` = `X-Procore-Signature` | `main.py:1315` ✓ correct | No |
| 02 | `api/procore.py:222` = `procore-signature` | `api/procore.py:222` ✓ correct | No |
| 02 | `api/procore.py:221,224-225` (secret + skip log) | `:221` secret ✓; skip-warning is `:224 if not secret:` / `:225 logger.warning(... skipping HMAC ...)` | No |
| 03 | `webhook_handler.py:103` = `_IDEMPOTENCY_STORE: set[str] = set()` | **`webhook_handler.py:27`** (line 103 is `def is_duplicate`) | No |
| 03 | `webhook_handler.py:106,108` | `:106 if delivery_id in _IDEMPOTENCY_STORE` ✓; `:108 _IDEMPOTENCY_STORE.add` ✓ | No |
| 03 | `webhook_handler.py:90` = `delivery_id=str(metadata.get(...) or payload.get(...) or "")` | **`webhook_handler.py:93`** = `delivery_id=metadata.get("delivery_id", "")` — actual code has **no payload-level fallback**; the note's described coalescing does not exist | No (but the delivery_id extraction described is wrong — see note below) |
| 03 | `webhook_handler.py:91-95` (event_type/project/company/resource coalescing) | `parse_event` is `:88-100`; fields read from `payload`/`metadata` without the `or` fallbacks the note shows (`:91-99`) | No |
| 03 | `job_state.py:51-63` posts to `/rest/v1/job_states` | post is `job_state.py:59-63` (`f"{SUPABASE_URL}/rest/v1/job_states"` at `:60`) | No |
| 03 | `004_job_states_immutable.sql:16-25` fn / `:28-40` triggers | fn `:16-26`; DELETE trigger `:28-33`; UPDATE trigger `:36-41` (approx — re-pin exact on edit) | No |
| 04 | `api/procore.py:265` = returns 202 | 202 is at `api/procore.py:267` (JSONResponse spans `:265-269`) | No |
| 04 | `main.py:1410` = `review_log = log_review(event, review_artifact)` | `main.py:1410` = `log_review(review_artifact, event)` (args swapped, no assignment) | No |
| 04 | `main.py:1413` = `stored_artifact = store_artifact(event, review_artifact)` | `main.py:1413` = `store_artifact(review_artifact)` (single arg) | No |
| 04 | `main.py:1429` = `compare_reviews(previous_artifact, review_artifact)` | `main.py:1429` = `compare_reviews(review_artifact, previous, current_swms_text=swms_text)` | No |
| 05 | `main.py:67,157` (legacy route registration) | `:67` import ✓; `:157` `app.include_router(procore_router, prefix="/procore")` ✓ — **still live** | No |
| 05 | `api/procore.py:217` orphan cleanup before HMAC | call is `api/procore.py:218` (`:217` is the comment) | No — pre-auth side-effect still real |
| 05 | `api/procore.py:220-231` HMAC branch | HMAC block is `:221-233` | No |
| 05 | `test_procore_stage2.py:16-18` = `import core.procore_X as procore_X` | `:16 from core.procore_extract import ExtractionResult, extract_and_route, CRITICAL_PAGE_KEYWORDS`; `:17 from core.procore_fetch import ...`; `:18 from core.procore_review import ...` (different import **style**; modules still imported) | No |
| 05 | `test_procore_stage2.py:19` procore_comment / `:165` / `:191` | `:19 from core.procore_comment import _format_pm_message, _format_sm_review, _reason_summary`; `:165 from api.procore import _cleanup_orphaned_jobs` ✓; `:191 from core.procore_comment import post_heartbeat_comment` ✓ | No |
| 06 | `api_client.py:77,82,88,99` | all ✓ correct (`:88` deprecated `submittal_logs/.../comments`) | No |
| 06 | `api_client.py:107-130` = `format_review_as_comment` | `def format_review_as_comment` at `api_client.py:106` | No |
| 06 | `main.py:1442` = `format_review_as_comment(review_artifact, comparison)` | `main.py:1442` = `format_review_as_comment(review_artifact, att.filename)` | No |
| 06 | `core/procore_comment.py:116-117` placeholder + url | `:116` placeholder comment ✓; `:117` `url = f"{PROCORE_API_URL}/submittals/{submittal_id}/comments"` ✓ | No |

**One substantive finding beyond line drift:** action_03 describes a `delivery_id` extraction with payload-level fallbacks (`metadata.get(...) or payload.get(...) or ""`). The **actual** `parse_event` (`webhook_handler.py:88-100`) reads `delivery_id` only from `metadata` (`:93`). So the durable-idempotency design must decide the real key source against actual sandbox payloads — the note over-states current robustness. This is an `UNVERIFIED` payload-shape question for Procore (see Deliverable 2).

---

## Deliverable 2 — Procore Confirmation Email (draft for `techpartners@procore.com`)

> Draft only. Subject and body below; send after Alan's review.

**Subject:** Safe Method × Procore — Technical confirmations for webhook integration (Submittals)

Hi Procore Technology Partner team,

We're preparing the Safe Method integration for Certification Assessment. Our integration is a server-to-server webhook listener on the **Submittals** surface that reads a submitted SWMS attachment, runs an advisory pre-screen, and writes an advisory result back for a human Safety Manager to action in Procore. Before we finalise the workflow diagram and harden the implementation, we'd like to confirm the following so our artifacts match Procore's current platform behaviour rather than our assumptions.

**1. Webhook authentication / signature scheme**
- What is the current, supported way to authenticate inbound webhook deliveries to our endpoint?
- Your public docs describe configurable `destination_headers` (e.g. `Authorization: Bearer <secret>`) on hook creation. Is verifying that configured `Authorization` header the preferred/supported approach? `https://procore.github.io/documentation/webhooks-api`
- Is there any first-party signature header (e.g. an HMAC-SHA256 signature header) we should verify instead of, or in addition to, the `Authorization` header? If so, what is the exact header name and signing algorithm?

**2. Webhook payload + namespace**
- For Submittals, what is the exact event namespace/name we subscribe to (e.g. resource/event-type strings) for a SWMS submission?
- Does the delivery payload include a stable per-delivery identifier (`delivery_id` and/or `ulid`) we can use as a durable idempotency key, and where does it sit in the payload (top-level vs `metadata`)?

**3. Write-back resource (the key open item)**
- What is the intended Procore surface for posting an advisory review result on a submittal? Specifically, should it be a **submittal comment**, a **submittal response**, a **workflow action**, a **correspondence item**, an **observation**, or another surface?
- What is the exact REST path and API version for that write-back? Our current code targets `submittal_logs/{id}/comments`, which appears deprecated in favour of `submittals` — we do not want to ship against a deprecated/incorrect path. `https://developers.procore.com/reference/rest/submittals?version=latest`
- Does that write-back support directed recipients / visibility / role-specific routing (we may show one summary to a PM and a detailed view to a Safety Manager)?
- Can the write-back be posted on revised and/or closed submittals?

**4. OAuth / authentication model**
- For a marketplace, server-to-server webhook integration like this, which OAuth grant do you expect: **Client Credentials / Data Management Service Account (DMSA)**, **Authorization Code**, or both (Auth Code for install, DMSA for runtime)? `https://procore.github.io/documentation/oauth-choose-grant-type`
- Do you support a DMSA/service-account install for this pattern, and what are the least-privilege scopes/permissions required to (a) read a submittal attachment and (b) perform the confirmed write-back?
- For Authorization Code (if required for install), please confirm refresh-token lifetime and rotation expectations.

**5. Rate limits**
- What are the current API rate limits and recommended backoff for our call volume (≈ 1 read + 1 write per submittal event)?

Thank you — once we have these confirmations we'll finalise the workflow/mapping diagrams to match exactly.

Best regards,
Alan Richardson — Safe Method / mcxico — alan.richardson@mcxi.com.au

**Open items this email gates:** signature scheme (Phase 2), write-back resource (Phase 5/2), OAuth grant + scopes (Phase 3), idempotency key source (Phase 2).

---

## Deliverable 3 — Revised Option B Phase Plan

**Sequencing change (refinement 1): two parallel tracks, not a linear gate.** Procore's last turnaround was ~1 month (`PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:33`). Making the Procore confirmation a hard block stalls a month of work that does not need Procore's answers. Only **two** things truly depend on Procore confirmation: the **auth scheme wiring** and the **write-back resource wiring**. Everything else proceeds concurrently.

- **Track A — confirmation-independent (start now):** Phase 0, plus the engineering that does not need Procore answers — T1 (disable legacy route), T3 (durable idempotency, using the derived fallback key below), T4 (async 202), T5 (kill local JSONL), T6 (Supabase audit), T9 (SBOM/CI), and T10 (baseline-review fix).
- **Track B — confirmation-gated:** the *final wiring* of T2 (auth scheme) and T8 (write-back surface) — built behind a pluggable interface now (refinement 2), with only config/endpoint swapped once Procore replies.

Each phase lists objective, key evidence, and exit gate. Per `CLAUDE.md`, any phase touching >3 files runs the checkpoint loop.

- **Phase 0 — Evidence honesty cleanup.** Apply Deliverable 1 corrections to the six notes; correct the feasibility report/CRUD to **one route**; remove the "no data retained" claim; mark signature/write-back/OAuth as `UNVERIFIED`. *Exit:* every note's `file:line` matches HEAD; no unverified claim stated as fact.
- **Phase 1 — Procore confirmation (runs in parallel with Phase 2, does not block Track A).** Send Deliverable 2; log answers. *Exit:* signature scheme, write-back resource, OAuth grant, idempotency key source all confirmed in writing (or explicitly still-open and flagged).
- **Phase 2 — P0 engineering hardening.** Disable legacy route registration (`main.py:67,157`); **scheme-agnostic fail-closed auth** — implement a pluggable `verify(headers, body) -> bool` so Procore's answer changes config, not architecture (replaces optional check at `main.py:1314-1320`); durable idempotency before any side-effect, using a **derived fallback key = SHA-256(raw body)** when no `delivery_id`/`ulid` is present (current code reads `metadata` only, `webhook_handler.py:93`); async 202 (port `BackgroundTasks` from `api/procore.py:263-267`) **with a dead-letter/failure surface + alert** (reuse Slack hook at `api/procore.py:32,87`); replay/forgery mitigations stated (HTTPS-only, secret rotation, idempotency caps blast radius — refinement 3); gate live write-back behind a flag with **once-per-`review_run_id` write idempotency** (refinement 5). *Exit:* one route; unsigned request → 401 with no side-effect; duplicate survives restart; failed async job is visible + alerts; no duplicate advisory comment on retry; 202 returns fast; pytest green.
- **Phase 3 — OAuth / token model.** Implement the confirmed grant (recommend DMSA/client-credentials primary); replace static `PROCORE_ACCESS_TOKEN` (`api_client.py:27`); secret-store + rotation; refresh handling if Auth Code is used. *Exit:* no static token in prod; least-privilege scopes documented.
- **Phase 4 — Minimal audit/retention model.** Supabase tables for deliveries + audit with immutability triggers (reuse `004_job_states_immutable.sql` pattern); retention windows; deletion path; remove/gate local JSONL (`webhook_handler.py:24-27`, `review_store.py:17-27`). *Exit:* no Procore-derived data on local disk in prod; audit rows immutable; retention documented.
- **Phase 5 — Advisory output quality gate.** Define `ReviewArtifactV1` / `StoredAuditArtifactV1` / `ProcoreAdvisoryCommentV1`; deterministic gate (banned approval words per `webhook_handler.py:30-44`, evidence refs, confidence, overclaim); golden tests. *Exit:* gate blocks non-compliant comments; goldens pass.
- **Phase 6 — Certification artifact pack.** Workflow + mapping diagrams, API list, payload summary, rate-limit/error matrix, SBOM/vuln evidence, support/SLA, customer-validation plan. *Exit:* every Section III field has an artifact.
- **Phase 7 — Sandbox demo + evidence capture.** Recorded end-to-end: configure hook → submit SWMS → 202 → advisory write-back. *Exit:* video + screenshots captured.
- **Phase 8 — Future rule-pack ingestion workflow.** Checklist/risk-register upload, criteria extraction, and approval UI remain behind certification. This is separate from the implemented RulePackV1.1 evaluation contract. *Exit:* deferred — see Deliverable 4.

---

## Deliverable 4 — RulePackV1.1 contract vs future ingestion workflow

**Implemented in V1:** RulePackV1.1 is the static, hand-authored project-criteria contract. It is loaded from `src/data/procore_rule_packs/project_{id}.json` (`api/main.py:1371-1375`), validated fail-closed (`core/procore/rule_pack.py:49-78`), and evaluated only when its lifecycle status permits (`core/procore/rule_pack.py:85-145`).

The implemented contract:
- preserves unconditional baseline/structural review;
- requires `baseline_protected=true`;
- records pack version, source basis/type/name, lifecycle status, and approval metadata for active packs;
- limits customer configuration to seven closed, non-executable predicates;
- requires one atomic criterion per requirement;
- emits one result per criterion: `aligned`, `partial`, `missing`, `unclear`, or `unsupported`;
- separates criterion result, evidence sufficiency, extraction quality, evaluation confidence, and human-confirmation state;
- preserves existing comment, audit, and resubmission compatibility through derived amendments and stable `project_rule:{criterion_id}` keys.

**Deferred until after certification:** company checklist/risk-register **upload**, automated criteria **extraction**, and the **human approval UI/workflow**. These are ingestion and governance features, not prerequisites for the static RulePackV1.1 evaluator.

**Why this is better for certification and retention:**
1. **Smaller retained-data surface.** Ingestion would require storing/processing customer checklist + risk-register documents — exactly the kind of customer data the "minimal retention" story needs to avoid during the certification window.
2. **Fewer moving parts to certify.** No upload pipeline, no extraction model, no approval workflow to security-review before the assessment.
3. **Evidences project-specific review.** Canonical `criterion_evaluations` retain criterion ID, requirement, basis, result, evidence references, reason code, and confidence without requiring an upload pipeline.
4. **Baseline protection is explicit.** The schema requires `baseline_protected=true`; project criteria add to the baseline and cannot suppress it.
5. **Unknown logic fails closed.** Unknown predicates fail schema validation, and invalid/inactive packs fall back to baseline-only review.

**Current deployment state:** the pilot fixture is `draft` and test-only. No production project pack is checked in. Production pilot activation requires genuine approval provenance and an operational deployment decision; draft packs cannot evaluate in production.

---

## Deliverable 5 — Corrected Data-Retention Language

> Do **not** use "no data retained." Replace the application's claim (`PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:133,148`) with the following.

**Safe Method — Procore integration data-handling statement (draft):**

> Procore remains the system of record. Safe Method does not create a permanent copy of customer project data. For each SWMS review, Safe Method retains a **minimal audit record** in its managed database (Supabase): the Procore event/delivery identifier, project and company identifiers, a document fingerprint/hash generated from the extracted SWMS review text (not from the full webhook payload), rule-pack/library versions, review status fields, finding and hard-fail counts, write-back metadata, and human-override records. Safe Method **does not retain** the raw SWMS document text, full Procore document content, full webhook payload bodies, finding prose, comment bodies, or any OAuth tokens/secrets in that audit record.
>
> Audit records are stored in a database with append-only (no-update/no-delete) controls and are retained for **[12 months — Alan to confirm]**, after which they are purged. Idempotency/delivery records are retained for **[30 days — Alan to confirm]** (covering Procore's documented retry window) and then purged. Customers may request deletion of their records by company or project identifier; Safe Method will action the request and confirm completion.
>
> SWMS document content is processed transiently by the Anthropic API for the review step. The applicable data-processing terms (including a Zero-Data-Retention arrangement) are **[status — Alan to confirm; ZDR is an open action item, `PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:135,169`]** and must be locked before this statement is submitted.

**Engineering status for this language:** local JSONL persistence is gated off by default (`PROCORE_LOCAL_JSONL_ENABLED=false`), PR #29 added metadata-only audit payload/RPC wiring, and migrations 007/008 are applied and verified in Supabase (`docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:17-18`, `docs/procore/SUPABASE_MIGRATION_APPLY_EVIDENCE_2026-06-18.md:40-44`). The statement is still conditional on confirming final retention/ZDR terms.

---

## Deliverable 6 — Implementation Tickets / Current Status

> Current status after PRs #24-#30 and verified Supabase migration apply. Several confirmation-independent tickets are implemented; the final T2/T7/T8 production wiring still depends on Procore answers and production env rollout.

| ID | Title | Scope (evidence) | Depends on | Acceptance |
|---|---|---|---|---|
| T1 | Disable legacy `/procore` route registration | Implemented in PR #24; legacy route disabled by default behind `PROCORE_LEGACY_ROUTE_ENABLED` | Done | `POST /procore/webhook` returns 404 by default; direct-import legacy tests remain supported |
| T2 | Fail-closed webhook auth (**scheme-agnostic**) | Implemented in PR #24; default `PROCORE_AUTH_SCHEME=unverified` rejects before side effects | Final scheme UNVERIFIED | Candidate HMAC/Bearer verifiers exist; production scheme/header must be set only after Procore confirms |
| T3 | Durable idempotency | Implemented in PR #24; Supabase reserve RPC with raw-body hash fallback; migration 007 applied as `20260618025557` | Real payload key location UNVERIFIED; optional runtime smoke not run | Duplicate processing is guarded; verified RPC exists with service-role execute only |
| T4 | Async 202 + dead-letter/failure surface | Implemented in PR #24; `/v1` returns 202 and runs background pipeline with failure alerting | Done | Failures recorded/alerted; worker/queue can remain a later durability upgrade |
| T5 | Gate local JSONL in production | Implemented in PR #25; `PROCORE_LOCAL_JSONL_ENABLED=false` by default | Done | No local Procore-derived JSONL files in production default |
| T6 | Supabase audit tables w/ immutability + retention | Implemented in PR #25, hardened in PR #27, applied as `20260618025643` | Optional runtime smoke not run; retention windows/ZDR still require final confirmation | Migration 008 has private table, RLS, service-role RPCs, pinned trigger search path, controlled retention/delete guard |
| T7 | OAuth / DMSA token model | Not implemented; static token model remains interim | Procore grant/scopes UNVERIFIED | Replace `PROCORE_ACCESS_TOKEN` with confirmed OAuth/DMSA model before certification |
| T8 | Advisory comment quality gate + write-back idempotency | Partially implemented: PR #26 gated live write-back; PR #29 added metadata-only audit builder/RPC wiring | Write-back resource/path UNVERIFIED | Final endpoint/path, write-back idempotency, and comment quality gate still require Procore confirmation |
| T9 | SBOM / vulnerability scan in CI | Implemented in PR #25; PR #28 added PDF/JWT dependency smoke coverage | Done | CI fails on vulnerable pinned deps; SBOM artifact produced; extraction/auth smoke coverage exists |
| T10 | Baseline review must not be gated by rule pack | Implemented in PR #24 | Done | Missing rule pack still produces baseline structural review with `project_review_status=UNAVAILABLE` |
| T11 | Deterministic RulePackV1.1 contract | Implemented in PR #32 | Customer pack creation/approval remains OPS-GATED | Closed schema; one result per criterion; no executable customer logic; drafts blocked in production; invalid/inactive packs run baseline only |

---

## Residual UNVERIFIED / Explicit-Approval Items (must resolve before submission)

1. Webhook signature/auth scheme — Procore confirmation (D2 Q1).
2. Write-back resource + REST path/version — Procore confirmation (D2 Q3); do **not** invent. Live write-back is safely gated off by default, but the final resource is still `UNVERIFIED`.
3. OAuth grant + DMSA support + scopes — Procore confirmation (D2 Q4).
4. `delivery_id`/`ulid` location in real payloads — Procore confirmation (D2 Q2); current code reads `metadata` only (`webhook_handler.py:93`).
5. `tests/test_procore_webhook.py` line citations in action_01 — not re-opened this pass; re-pin on edit.
6. Anthropic ZDR status — Alan (`report:135,169`).
7. Retention windows (12 mo / 30 day) — Alan to set.
8. Optional Supabase runtime smoke — not run; requires explicit approval because it writes synthetic delivery/audit rows.
9. Production RulePackV1.1 content and approval — no real customer/project pack is deployed; the checked-in pilot fixture remains draft and test-only.

---

## Appendix: Certification Tighteners That Do Not Expand V1 Scope

These are documentation, test, config, and evidence guardrails only — **no new product features**. They make the existing V1 more certifiable without enlarging scope.

### A. Procore Confirmation Register

Single source of truth for the open Procore questions (Deliverable 2). Keep this table updated as answers arrive; each row names the ticket it unblocks.

| Question | Status | Procore answer | Decision impact | Blocking ticket |
|---|---|---|---|---|
| Webhook auth/signature scheme (header name + algorithm) | UNVERIFIED | — | Fixes final auth verifier config | T2 (final wiring) |
| Is configured `Authorization` `destination_headers` the preferred approach? (`https://procore.github.io/documentation/webhooks-api`) | UNVERIFIED | — | Confirms verifier strategy vs HMAC | T2 |
| Write-back resource + REST path + API version | UNVERIFIED | — | Determines write-back endpoint; `submittal_logs/.../comments` (`api_client.py:88`) is deprecated | T8 (final wiring) |
| Which surface: submittal comment / response / workflow action / correspondence / observation | UNVERIFIED | — | Determines write-back object + scopes | T8 |
| OAuth grant / DMSA expectation for marketplace webhook integration (`https://procore.github.io/documentation/oauth-choose-grant-type`) | UNVERIFIED | — | Chooses grant; replaces static token (`api_client.py:27`) | T7 |
| Least-privilege scopes/permissions (read attachment + confirmed write-back) | UNVERIFIED | — | Defines requested scopes | T7 |
| `delivery_id` / `ulid` location in payload (top-level vs `metadata`) | UNVERIFIED | — | Confirms durable idempotency key; current reads `metadata` only (`webhook_handler.py:93`) | T3 |
| PM/SM visibility or recipient support on write-back | UNVERIFIED | — | Enables/defers two-tier comment (action_06) | T8 / V1.1 |

### B. Feature Flags / Kill Switches (operational guardrails)

Proposed env flags. **These are operational guardrails, not substitutes for code correctness** — each ticket must still be correct with the flag in its safe default.

| Flag | Default | Purpose | Related ticket |
|---|---|---|---|
| `PROCORE_LEGACY_ROUTE_ENABLED` | `false` | Re-enable deprecated `/procore` route only for rollback (`main.py:67,157`) | T1 |
| `PROCORE_REQUIRE_AUTH` | `true` | Enforce fail-closed auth; never ship `false` to prod | T2 |
| `PROCORE_AUTH_SCHEME` | `unverified` | Selects pluggable verifier; stays `unverified` until Register row A resolves | T2 |
| `PROCORE_LIVE_WRITEBACK_ENABLED` | `false` | Gates live write-back until resource confirmed (action_06) | T8 |
| `PROCORE_LOCAL_JSONL_ENABLED` | `false` | Disables local JSONL persistence in prod (`webhook_handler.py:136-165`, `review_store.py:22-27`) | T5 |
| `PROCORE_ASYNC_WEBHOOK` | `true` | Routes through async 202 path | T4 |

### C. Demo-Safe Failure Script

Evidence cases. Mark each as **DEMO** (show in the certification video) or **TEST** (automated evidence only).

| Case | Expected behaviour | Where |
|---|---|---|
| Invalid webhook auth | `401`, no side effects (no `log_payload`/fetch/review/comment) | DEMO + TEST |
| Duplicate delivery | second delivery accepted/ignored, no duplicate processing or comment | DEMO + TEST |
| Missing rule pack | baseline/structural review still runs; `project_review_status=UNAVAILABLE` | TEST (mention in DEMO) |
| Weak / no text extraction | escalates to human review (no silent pass) | TEST |
| Write-back disabled (endpoint unverified) | review completes, no write attempted; status notes write-back gated | DEMO + TEST |

Rationale: the DEMO subset proves security + system-of-record posture to Procore; the TEST-only subset is regression evidence that need not appear on video.

### D. No Procore Update/Delete Assertion

Supports the "Procore remains system of record" claim (`PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:133,148`). Add a guard test proving the live Procore path issues **no `PATCH`, `PUT`, or `DELETE`** against Procore customer data — only `GET` (attachment read, `api_client.py:69-70`) and the single confirmed `POST` write-back.

Expected test shape (do **not** implement this pass):
```
# pseudocode — assert HTTP verbs used against Procore
mock httpx; run full /v1 review path with live config
assert every request to PROCORE_API_URL is in {GET, POST}
assert no request method in {PATCH, PUT, DELETE}
assert the only POST targets the confirmed write-back resource
```

### E. API Volume Formula (certification answer draft)

> Per SWMS submittal: 1 webhook delivery received, 1 attachment/file read, 0 or 1 advisory write-back, plus bounded retry overhead. Estimated daily calls = SWMS submissions per customer per day × 2 + retry overhead.

**UNVERIFIED — Alan to plug in customer-volume assumptions** (submissions/customer/day, customer count). Retry overhead bounded by Procore's documented exponential backoff over a ~12h window (action_03/04).

### F. Certification Copy Lint (external-facing docs/decks/demo scripts)

Extends the locked copy rules (`PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:159-160`). Run on every external artifact before submission.

**Ban / require manual review:** `approved`, `compliant`, `certified`, `passed`, `automatic approval`, `no data retained`, `replaces Procore`, `legal advice`, `guarantee`.

**Require (replacement language):** `advisory`, `pre-screen`, `human review required`, `Procore remains system of record`, `minimal audit metadata retained`.

Note: the engine's status vocabulary already bans approval words (`webhook_handler.py:30-44`); this lint extends that discipline to prose artifacts (deck, video script, listing).

### G. Implemented RulePackV1.1 Provenance And Lifecycle

RulePackV1.1 is now implemented for static JSON packs at `src/data/procore_rule_packs/project_{id}.json` (`api/main.py:1371-1375`). The schema requires pack version, project ID, lifecycle status, source basis/type, baseline protection, and at least one atomic criterion (`core/procore/rule_pack_v1_1.json:6-77`). Active packs additionally require genuine `approved_by` and `approved_at` values (`core/procore/rule_pack_v1_1.json:79-89`).

```json
{
  "pack_schema_version": "1.1",
  "project_id": "<int>",
  "pack_version": "<semver or date>",
  "status": "draft | active | superseded | archived",
  "source_basis": "<plain-English basis for these criteria>",
  "source_type": "checklist | risk_register | whs_management_plan | manual | composite",
  "source_name": "<document/register name>",
  "approved_by": "<required only when active>",
  "approved_at": "<required only when active; ISO-8601>",
  "baseline_protected": true,
  "criteria": ["one or more atomic Criterion objects"]
}
```

Draft evaluation requires both `PROCORE_ALLOW_DRAFT_RULE_PACKS=true` and `ENVIRONMENT` set to `development`, `test`, `testing`, or `local` (`core/procore/rule_pack.py:81-82`, `core/procore/rule_pack.py:127-139`). Production defaults fail closed.

---

## Track A Handover — Pre-Flight Block

Add to the top of any Track A implementation session, before creating a branch:

```
# Pre-flight
git status --short          # must be clean of unrelated changes
git branch --show-current   # confirm starting point
# If not on a clean `main`, STOP and report before creating/switching branch.
```

**Supabase RPC hardening (applies to T3, T6):**
- Do **not** create `security definer` functions in exposed/public schemas. Use a private/internal schema, service-role-only access, restricted `EXECUTE`, and RLS where applicable. (action_03's draft RPC is `security definer` in `public` — tighten before applying.) Refs: `https://supabase.com/docs/guides/api/securing-your-api`, `https://supabase.com/docs/guides/database/postgres/row-level-security`.

**Async durability caveat (applies to T4):**
- FastAPI `BackgroundTasks` is **interim** async hardening only. Certification-grade durability depends on the durable reservation + status row (T3/T6) and may later require a real worker/queue. Do not present `BackgroundTasks` alone as the durable processing guarantee.
</content>
