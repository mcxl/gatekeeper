## Webhook Receipt
POST /procore/webhook

1. Verify HMAC-SHA256 signature synchronously. Reject 401 if invalid.
2. Extract submittal_id, project_id, document_url from payload.
3. Log actual payload shape — this is the Phase 1B design input.
4. Return 202 Accepted immediately.
5. Enqueue review via FastAPI BackgroundTasks:
   - Post Received heartbeat comment → capture returned comment_id
   - Pass comment_id into retrieval and review pipeline
   - PATCH comment with result on completion or failure

Note: BackgroundTasks bridges Procore's webhook timeout requirement until
Phase 1B introduces a real async queue. Do not use threading or asyncio
directly — BackgroundTasks is sufficient for the synchronous spike.
FastAPI holds the HTTP response open until the handler returns, so
without BackgroundTasks a 15-second review would cause Procore to drop
the connection and mark the webhook as failed.

## Heartbeat Comment — Mandatory Behaviour
Never leave a submittal silent after a webhook fires.

Three-state lifecycle:
1. Received — POST to Procore, capture comment_id from response
   "Safe Method: Review received — processing"

2. Complete — PATCH using stored comment_id
   "Safe Method: Review complete — [N] issues found. [Summary]. Ref: [correlation_id]"

3. Failed — PATCH using stored comment_id
   "Safe Method: Review could not be completed. Manual review required. Ref: [correlation_id]"

comment_id threading requirement:
- The function posting the Received comment must return the comment_id
- comment_id must be passed explicitly to every downstream function
- The result poster must PATCH the existing comment, never create a new one
- If the initial POST fails, log and continue — do not abort the review,
  but note that the result will be posted as a new comment in this edge case

## Hard-gated categories (Stage 2)

The following categories trigger an immediate Aborted heartbeat
without running the review engine:
- tilt-up / tilt_up / precast / tilt up concrete

Aborted comment text:
"Safe Method: This SWMS category (tilt-up/precast) is under
active quality review and cannot be automatically pre-screened
at this time. Manual review is required for this submission.
Ref: [correlation_id]"

Hero category for Stage 2 spike: Excavation (primary),
Scaffolding (fallback).

## Domain issues affecting Stage 2 scope

D007: Tilt-up sequence dependency graph missing.
Pre-Stage 3 fix: DAG sequence validator — CTI design task.
Do not implement without locked CTI spec.

## Excavation DAG validator (final)

Files:
- core/sequence_validator.py — dumb runner
- core/models/dag.py — Pydantic schema, lazy loaded
- core/dag_rules/excavation.json — excavation rules

Lazy validation: validated on first access only.
Malformed JSON fails that category — app continues.

Confidence tiers:
- High: >=0.85
- Medium: 0.65-0.84
- Low: <0.65 (adds manual verification warning)

Truncation: hard fails first, truncate at 3000 chars,
append S3 link if truncated. Hard fails never cut.

Timeout ladder:
- 45s: Slack alert via SLACK_WEBHOOK_URL env var
- 90s: Procore delayed processing comment
- 120s: auto-fail + correlation_id

Chaos engine: local_mock/chaos_engine.py
- Modes: normal, timeout, error
- Fake data only — no real PII
- Test all modes before pointing at Procore sandbox

Stage 3 success gates:
- 50 reviews across 3 pilot PCs
- 0% false negatives on BYDA (text-searchable PDFs)
- 95% recall on BYDA (scanned PDFs)
- SM hard fail override rate <20%
- All 3 SMs active at review 10
- Average review time <3 minutes
- Slack chaos alerts <2 per week
