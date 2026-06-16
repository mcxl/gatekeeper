# Procore Stage 3 Certification Readiness — Adversarial Review of Option B

**Reviewer:** Claude (read-only planning pass, no code changed)
**Date:** 2026-06-17
**Scope:** Does Option B set the correct path for Procore Section III Certification Assessment?
**Stance:** Challenge by default. Every claim carries `file:line` evidence or is marked `unverified`.

---

## 0. Evidence-integrity note (read this first)

Before trusting the plan, two things must be corrected because they undermine the "every claim has file:line evidence" rule the master prompt itself sets:

1. **Both webhook routes are still live.** The legacy route is registered, not disabled:
   - `api/main.py:67` — `from api.procore import router as procore_router`
   - `api/main.py:157` — `app.include_router(procore_router, prefix="/procore")`
   So today the production app exposes **two** Procore webhook routes (`/procore/webhook` and `/v1/procore/webhook`). Action 05 is still a *proposal*; nothing has been disabled.

2. **The action notes' line citations are partly stale against current HEAD.** Examples:
   - action_03 cites `core/procore/webhook_handler.py:103` for `_IDEMPOTENCY_STORE: set[str] = set()`; the actual symbol is at **line 27** (line 103 is `def is_duplicate`).
   - action_01 cites `core/procore/webhook_handler.py:147-148` as `path.write_text(json.dumps(record, indent=2), ...)`; the real code is `f.write(json.dumps(record, ensure_ascii=False) + "\n")` (`webhook_handler.py:147-148`).
   The *conclusions* of those notes are still correct, but Procore reviewers read literally. Re-pin every `file:line` against HEAD before any of this is rendered into a diagram or submission.

This does not change the verdict, but it means **Workstream 1 (feasibility honesty cleanup) is a real prerequisite, not a formality.**

---

## 1. Verdict — **ACCEPT WITH CHANGES**

Option B is directionally correct: webhook hardening alone is not certifiable, and the certification-readiness workstreams (OAuth, retention, audit, SBOM, diagrams, demo, support/SLA) are the right superset. But it is **not yet a plan a Procore reviewer would pass**, for three reasons:

1. **It still treats certification as additive to a spike.** Two live routes (`api/main.py:157`), an unverified write-back endpoint (`core/procore/api_client.py:88`), an unverified signature header (`api/main.py:1315`), and local JSONL retention (`webhook_handler.py:24-27`, `review_store.py:17-27`) are not "items to add to"; they are **active contradictions of commitments already made to Procore** (the application promised "no customer data retained" — `PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:133,148`). Certification fails on contradiction, not on missing features.

2. **The PM/SM Project Rule Pack is being treated as a V1 certification workstream.** It should not be a *certification* gate at all. It is a product differentiator that can ship after certification. Loading it into the certification critical path adds scope, a new data model, and a new retention surface precisely where you most need to *shrink* the retained-data story. Recommend **V1.1, behind certification.** (Detail in §4.)

3. **Several load-bearing facts are still `unverified` and cannot be made true by us** — the Procore signature/auth scheme, the write-back resource, and the OAuth grant type all require Procore confirmation. A plan that schedules implementation before those confirmations will churn. These must become **explicit Procore-support questions at the top of the plan**, gating the dependent workstreams.

**Bottom line:** ACCEPT the direction. CHANGE the sequencing (honesty cleanup + Procore confirmations *first*), and DEFER the Project Rule Pack out of the certification critical path.

---

## 2. Certification Readiness Matrix

Owner key: **ENG** (build), **ALAN** (decision/policy), **PROCORE** (external confirmation needed), **CTO** (artifact drafting).
Phase key: **P0** go-live blocker · **P1** certification design · **P2** product quality · **P3** post-cert.

| Cert requirement | Current evidence | Current gap | Required artifact / implementation | Owner | Phase | Risk if omitted |
|---|---|---|---|---|---|---|
| Workflow diagram | `PROCORE_TECHNICAL_FEASIBILITY_REPORT.md:123-132` (CRUD table, has `[CONFIRM]` rows) | Reflects 2 routes; rows unverified | One-route diagram from a `[VERIFIED]` table | CTO | P1 | Reviewer cross-checks vs code; mismatch = reject |
| Integration mapping diagram | none found | Missing | Object-mapping diagram (Submittal→review→write-back) | CTO | P1 | Required artifact absent |
| Demo video | none found | Missing | Script + sandbox recording of config→event→review→comment | CTO/ENG | P1 | Mandatory; blocks invite |
| Developer app/listing URL | Railway URL `…baafa.up.railway.app` (`report:75`) | Not a Procore app listing | Marketplace/developer app entry | ALAN | P1 | Required field |
| Procore APIs used | `api_client.py:56-103` (attachment GET, comment POST) | Comment path unverified | Final API list w/ versions | ENG/PROCORE | P1 | Inaccurate list = reject |
| Read/write payload summary | `webhook_handler.py:118-133`, `api_client.py:90-94` | Not documented for submission | Payload summary doc | CTO | P1 | Required |
| API exchange frequency | none | Missing | "Per submittal event; 1 read + 1 write" statement | CTO | P1 | Required field |
| API call-volume estimate | pilot gates `report:182-188` | No volume math | Volume estimate (events/day × calls) | ALAN | P1 | Required field |
| Rate-limit handling | none in `core/procore/` | **No 429/backoff anywhere** (`ACTION_PLAN.md:20`) | Retry/backoff matrix + code | ENG | P0/P1 | Silent failure under load |
| 401/429/5xx/timeout handling | `api_client.py:71` `raise_for_status()` only | No structured handling | Error-handling matrix | ENG | P1 | Reviewer asks explicitly |
| OAuth grant type | static token `api_client.py:27,36` | No OAuth flow | Decide Auth Code vs Client Credentials/DMSA (§6) | ALAN/PROCORE | P1 | Static token likely not certifiable |
| OAuth scopes / DMSA perms | none | Missing | Least-privilege scope list | ALAN/PROCORE | P1 | Required field |
| Refresh-token handling | none | Missing | Refresh + rotation design | ENG | P1 | Required field |
| Token storage controls | env var `api_client.py:27` | Plain env, no rotation policy | Secret-store + rotation policy | ENG/ALAN | P1 | Security review fail |
| Data retention | local JSONL `webhook_handler.py:24-27`, `review_store.py:17-27`, `main.py:1330,1410,1413` | Contradicts "no retention" claim | Explicit retention model (§5) | ALAN/ENG | P0/P1 | **Direct contradiction of app record** |
| Customer deletion path | none | Missing | Deletion trigger + process | ALAN | P1 | Required field |
| Production access roles | none documented | Missing | RBAC/access doc | ALAN | P1 | Required field |
| Access review cadence | none | Missing | Quarterly access-review policy | ALAN | P1 | Required field |
| Employee departure revocation | none | Missing | Offboarding/revocation protocol | ALAN | P1 | Required field |
| Audit logs | JSONL logs `webhook_handler.py:136-165` (mutable files) | Not tamper-resistant | Immutable audit model (Supabase, §5) | ENG | P1 | Audit requirement fail |
| Audit retention + tamper protection | immutability precedent exists `004_job_states_immutable.sql:16-40` (per action_03) | Not applied to Procore audit | Reuse immutability trigger pattern | ENG | P1 | Required |
| SBOM / vuln scanning | CI = flake8+pytest only (`ci.yml:37-41`); no pip-audit/safety/cyclonedx (verified absent) | Missing entirely | Add `pip-audit`/SBOM step + evidence | ENG | P1 | Required field |
| Security accreditation | none | Missing | Honest "no formal accreditation; controls X/Y/Z" answer | ALAN | P1 | Required field |
| Pen-test | none | Missing | Pen-test status answer (likely "planned") | ALAN | P1 | Required field |
| Webhook namespace | submittals only `main.py:1337` | OK but undocumented | State namespace = Submittals | CTO | P1 | Minor |
| Webhook auth/signature validation | optional HMAC `main.py:1314-1320`, header `X-Procore-Signature` **unverified** (action_02) | Fail-open + wrong/unconfirmed header | Fail-closed + Procore-confirmed scheme | ENG/PROCORE | P0 | **Security reject** |
| Webhook retry/failure handling | in-memory idempotency `webhook_handler.py:27,103-109` | Non-durable; lost on restart | Durable idempotency (action_03) | ENG | P0 | Duplicate side-effects |
| Support / SLA | none | Missing | Support channel + SLA statement | ALAN | P1 | Required field |
| Customer validation / company_id | sandbox requested `report:151` | No validated customer | Pilot/validation plan | ALAN | P1 | Required field |

---

## 3. Architecture Corrections

Target architecture (from the brief) is **directionally right** and should be adopted as the single canonical shape. Corrections, by priority:

### P0 — go-live blockers (must land before any sandbox demo to Procore)
1. **Collapse to one route.** Disable legacy `/procore` registration (`api/main.py:67,157`). Keep `api/procore.py` on disk for tests (action_05). *Two live routes is an automatic "which is the integration?" reject.*
2. **Fail-closed webhook auth.** `/v1` currently skips verification when the secret is empty (`api/main.py:1314`). Must reject with 401 before any side effect (action_01). Note: today the **first side effect (`log_payload`, `api/main.py:1330`) runs even on the duplicate/no-secret path** — ordering is wrong regardless of the secret.
3. **Resolve the signature scheme with Procore before coding it.** `X-Procore-Signature` (`main.py:1315`) and legacy `procore-signature` (`api/procore.py:222`) are both `unverified`; public docs show configured `Authorization: Bearer` (`destination_headers`) instead (action_02). **Do not ship either header until Procore confirms.** This is a Procore question, not an eng task.
4. **Durable idempotency before logging/fetch/review.** In-memory set (`webhook_handler.py:27,103-109`) is lost on Railway restart and is checked *after* `log_payload` (`main.py:1330` before `:1333`). Move a durable reservation (Supabase, action_03) to the first step after auth.
5. **Async 202.** `/v1` does fetch→review→store→compare→comment synchronously then returns (`main.py:1367-1459`) — against Procore's 5s timeout guidance (action_04). Port the existing `BackgroundTasks` shape (`api/procore.py:263-265`) to `/v1`.
6. **Gate live write-back until the resource is confirmed.** `post_submittal_comment` posts to `/projects/{id}/submittal_logs/{id}/comments` (`api_client.py:88`) — `submittal_logs` is deprecated and that comment path is `unverified` (action_06). Keep write-back behind a flag until Procore confirms surface.

### P1 — certification design decisions
- OAuth grant + token storage + refresh (§6).
- Retention/audit model (§5).
- 429/backoff around Anthropic and Procore calls (none exists today — `ACTION_PLAN.md:20`).
- SBOM/vuln scan in CI (`ci.yml` has none).
- Diagrams, payload summary, API list, demo, support/SLA.

### P2 — product quality
- Quality-gated advisory comment contract (`ReviewArtifactV1` etc.).
- Two-tier PM/SM comment **only after** the write-back surface is confirmed (action_06 §"Two-Tier").
- Project Rule Pack V1 (§4) — product value, not a cert gate.

### P3 — post-certification hygiene
- Delete deprecated flat `core/procore_*.py` modules once unreferenced (`ACTION_PLAN.md:99`).
- Split `api/main.py` routers (it is 2028 lines).
- Reconcile concurrency number (3/5/11 drift, `ACTION_PLAN.md:21`).

**One correction to the target diagram itself:** insert an explicit **"verified Procore resource" gate** before write-back and a **"durable status row update"** after the async job (so failures are visible post-202, per action_04 open question). Otherwise the shape is sound.

---

## 4. PM/SM Project Rule Pack — Design Review

**Is it valuable for certification?** No — not as a *certification* requirement. Procore certifies the integration's security, data handling, and platform fit, not the sophistication of your review criteria. **It is valuable as a product differentiator**, and a *small* version actually helps the data-handling story (it lets you store findings-by-criterion instead of raw SWMS text).

**Is it too much for V1 (certification)?** Yes. It introduces a new data model, ingestion paths (checklist/risk-register upload + extraction), an approval workflow, and a new retention surface — all in the workstream where you most need to minimise retained data. Putting it on the certification critical path increases reject risk.

**Smallest certifiable slice (what V1 *should* carry):** the engine **already loads a per-project rule pack** — `api/main.py:1348-1359` reads `src/data/procore_rule_packs/project_{id}.json` and returns `no_rule_pack` if absent, and `run_prescreen_review` already emits `rule_pack_version` and `project_specific_mismatches` (`prescreen_reviewer.py:483-485`). So V1 keeps a **static, hand-authored, versioned JSON rule pack per project** (no upload/extraction UI, no approval workflow). That is enough to *evidence* "reviewed against project-specific criteria" without the heavy machinery.

**Recommendation: Project Rule Pack ingestion/approval = V1.1, behind certification.** Static versioned JSON pack = part of V1 (already built).

**Storage/versioning (when built):** version per project; immutable versions (new version, never mutate); store the *pack version + criteria IDs checked + state*, not the source documents. Criterion schema from the brief (`brief:157-173`) is sound; add `baseline_protected: bool` so baseline checks can be flagged un-overridable.

**Appearance in the Procore comment:** each finding cites `criterion_id` + `source_ref` + expected vs observed (brief example at `brief:201-216` is the right shape). Keep baseline findings in a separate, clearly-labelled block.

**Human overrides:** log override as a new immutable audit row (`override_by`, `role`, `reason`, `timestamp`, `criterion_id`) — never edit the original finding.

**Preventing customer criteria from weakening baseline WHS checks (critical):** enforce in code, not policy. Baseline checks run in a **separate, non-configurable pass** whose results are merged *after* the customer pass and cannot be suppressed by a rule pack. Mark baseline findings `baseline_protected=true`; the merge step rejects any rule-pack directive that would downgrade/hide a protected finding. The current `_assess_project_review_status` / suppression logic (`prescreen_reviewer.py:455-457,481`) must be audited to confirm rule packs cannot suppress baseline structural findings.

---

## 5. Data Retention & Audit Model

**Current reality (cannot claim "no data retained"):** local JSONL files persist Procore-derived data:
- payload log + review log: `core/procore/webhook_handler.py:24-27,136-165`
- full review artifacts (incl. document hash, findings, mismatches, status): `core/procore/review_store.py:17-27`, written at `api/main.py:1410,1413`
- artifact contents: `prescreen_reviewer.py:466-495`

This **directly contradicts** the application commitment "no customer data retained" (`report:133,148`). Honesty cleanup must fix the *claim* or the *storage* — recommend fixing both: store minimal metadata, and present a precise data-flow answer (not "no retention").

**Cleanest certifiable model:**

| | Decision |
|---|---|
| **Stored** | event id/ULID, payload SHA-256, project/company id, rule-pack version, criteria IDs + state, finding summaries (no raw SWMS), status recommendation, write-back metadata, correlation id, audit/override rows |
| **Not stored** | raw SWMS text, full Procore document content, tokens/secrets, full payload bodies |
| **Where** | Supabase (Postgres), not local JSONL on the Railway container |
| **Retention** | findings/audit: fixed window (recommend 12 months, ALAN to set); idempotency rows: ≥12-hour Procore retry window + margin (recommend 30 days) |
| **Deletion trigger** | customer request → delete by company_id/project_id; automatic purge past retention window |
| **Customer deletion process** | documented request channel → ENG-run deletion script → confirmation |
| **Audit immutability** | reuse existing pattern: `supabase/migrations/004_job_states_immutable.sql` no-update/no-delete triggers (per action_03 citation) applied to a `procore_audit` table |

**Local JSONL persistence must be REMOVED (or gated off in production), not merely supplemented.** Files on an ephemeral Railway container are both a retention-claim liability and not durable for audit — the worst of both. Replace with Supabase tables that have explicit retention + immutability.

**Also resolve ZDR:** the review engine sends document content to the Anthropic API; the "no retention" answer depends on the Anthropic Zero-Data-Retention agreement, which is an **open action item** (`report:135,169`; `ACTION_PLAN.md:113`). Lock this before any data-handling claim is submitted.

---

## 6. OAuth / Auth Recommendation

**Current:** static `PROCORE_ACCESS_TOKEN` env var (`api_client.py:27,36-48`); `is_live_configured()` checks token+client_id (`:51-53`). No refresh flow.

**Is the static token certifiable?** **No.** A long-lived static access token with no refresh/rotation will fail the token-storage and access-control questions. It must be replaced.

**Recommendation: Client Credentials / Data Management Service Account (DMSA) as the primary grant**, because this is a **server-to-server, headless webhook integration** with no per-user interactive context at review time — Safe Method acts as a service against the customer's project. DMSA gives an installable, least-privilege, company-scoped service identity, which is exactly what Procore's platform team expects for this pattern.
- **Authorization Code** is only needed if/when a human must individually authorise (e.g. an interactive admin install/config UI). If the install/config step is interactive, use Auth Code **for install only**, then operate via DMSA/client-credentials. Decide based on the actual install UX.
- **Verify with Procore** which grant they require for a marketplace webhook integration — this is `unverified` and grant choice is a Procore-gated decision (master prompt lists the OAuth grant-selection docs).

**Refresh:** client-credentials tokens are short-lived and re-minted (no refresh token); if Auth Code is used for install, store and rotate the refresh token. Either way, **no static token in env for production.**

**Token storage:** secret manager / Supabase secured table with restricted access — never plain env on the app container; rotation policy documented.

**Least-privilege scopes:** request only Submittals read + the confirmed comment/response write scope. Do not request company-wide admin. Final scope list pends the write-back surface decision (§7).

---

## 7. Write-Back Resource Recommendation — **UNRESOLVED (Procore confirmation required)**

Per action_06, current code posts to `/projects/{id}/submittal_logs/{id}/comments` (`api_client.py:88`), but:
- `submittal_logs` is **deprecated**; docs say use `submittals`.
- No public `submittal_logs/{id}/comments` path found.
- No public `submittals/{id}/comments` path found.
- `submittal_responses` exists but using it for review output is a product/API decision, not a verified fact.

**I will not invent an endpoint.** Status: **unresolved.** Required confirmation from Procore (`techpartners@procore.com`):
1. Is the SWMS review result meant to be a submittal **comment**, **response**, **workflow action**, **correspondence item**, or **observation**?
2. Exact REST path + API version.
3. Recipient/visibility/role-direction support (needed for any PM/SM tiering).
4. Whether comments can be posted on revised/closed submittals.

Until confirmed: keep write-back behind a flag, ship read-only review for the sandbox demo if necessary, and present the write-back as "pending Procore resource confirmation" rather than claiming it works.

---

## 8. Tests & Evidence Plan

**Unit / engine**
- `validate_signature` true/false (`webhook_handler.py:76-85`) — already partially covered.
- `run_prescreen_review` golden output (status vocabulary never "approved/compliant" — `webhook_handler.py:30-44`).
- Baseline-protection: rule pack cannot suppress a `baseline_protected` finding.

**Request-level (`/v1`)**
- Fail-closed: no secret → 401, and **assert `log_payload`/`fetch_attachment`/`run_prescreen_review`/`post_submittal_comment` not called** (action_01 test guard; current request tests at `tests/test_procore_webhook.py:342,358-389`).
- Bad signature → 401; valid → 202.
- Legacy route disabled → `POST /procore/webhook` returns 404 (action_05 guard).

**Migration / RLS**
- `procore_webhook_deliveries` + `procore_audit` migrations apply; immutability triggers reject UPDATE/DELETE; RLS reviewed via Supabase security advisors.

**Idempotency / async**
- Duplicate `delivery_id` → single processing, second returns 200/202 without side effects, survives a simulated restart (durable store).
- 202 returns fast; background job updates a durable status row; failure path visible post-202.

**Rate-limit / error handling**
- 429 from Anthropic and Procore → backoff/retry, graceful degrade, no raw error surfaced.
- 401/5xx/timeout from Procore fetch/write → mapped to safe states.

**Evidence artifacts**
- Procore sandbox demo script: configure webhook → submit SWMS in Submittals → observe 202 → observe advisory comment.
- Screenshots/video of the above.
- SBOM output + `pip-audit` clean run in CI.
- Golden review-output fixtures for the demo SWMS.

---

## 9. Final Phase Plan (sequenced)

0. **Feasibility honesty cleanup** — re-pin all `file:line` to HEAD; correct diagrams/CRUD to one route; remove "no retention" claim; mark unverified endpoint/header/grant as open. *(Prereq; cheap; unblocks accuracy.)*
1. **Send Procore confirmation questions** — signature/auth scheme, write-back resource, OAuth grant. *(External; parallelisable; gates 3 & 7.)*
2. **P0 route/auth/idempotency/async hardening** — disable legacy route; fail-closed auth (scheme TBD by #1); durable idempotency; async 202; gate write-back. *(>3 files — checkpoint per CLAUDE.md.)*
3. **OAuth + token model** — implement confirmed grant; secret storage; refresh/rotation.
4. **Minimal audit/retention model** — Supabase tables, immutability triggers, retention windows, deletion path; remove/gate local JSONL.
5. **Quality-gated advisory comment** — `ReviewArtifactV1`/`StoredAuditArtifactV1`/`ProcoreAdvisoryCommentV1`; golden tests.
6. **Static Project Rule Pack hardening (V1)** — keep JSON packs versioned + baseline protection; defer ingestion/approval UI to **V1.1**.
7. **Certification artifact pack** — diagrams, API list, payload summary, rate-limit matrix, SBOM, support/SLA, customer validation.
8. **Sandbox demo + evidence capture** — recorded end-to-end run.
9. **Post-cert cleanup (P3)** — delete flat modules, split routers, reconcile concurrency.

---

## 10. Red Flags (blunt)

1. **Two live webhook routes** (`api/main.py:67,157`) — automatic "which is the integration?" reject. Not yet fixed.
2. **Fail-open auth** (`api/main.py:1314`) — unsigned/no-secret requests trigger side effects (`log_payload` at `:1330`). Security reject.
3. **Signature header is unverified and probably wrong** (`X-Procore-Signature`, `main.py:1315`) — public docs say `Authorization: Bearer`. Do not claim HMAC validation.
4. **Write-back endpoint unverified + deprecated** (`api_client.py:88`, `submittal_logs`). Do not claim it works.
5. **"No data retained" is currently false** — local JSONL persists payloads/reviews/artifacts (`webhook_handler.py:24-27`, `review_store.py:17-27`) and contradicts the app record (`report:133,148`). Biggest probe area.
6. **Static access token, no rotation/refresh** (`api_client.py:27`). Token-storage reject.
7. **No 429/backoff anywhere** (`ACTION_PLAN.md:20`) — silent failure under load.
8. **No SBOM / vuln scan** (`ci.yml:37-41` is flake8+pytest only; pip-audit/safety/cyclonedx absent). Required field empty.
9. **Synchronous processing vs 5s webhook timeout** (`main.py:1367-1459`). Dropped deliveries.
10. **In-memory idempotency lost on restart** (`webhook_handler.py:27`). Duplicate side effects.
11. **ZDR with Anthropic unresolved** (`report:135,169`) — the data-handling answer depends on it.
12. **Project Rule Pack scoped into the certification critical path** — adds a retention surface where you need to shrink one. Move to V1.1.
13. **Stale `file:line` citations in the action notes** — small, but in a submission read literally it reads as carelessness. Re-pin before rendering anything.
</content>
</invoke>
