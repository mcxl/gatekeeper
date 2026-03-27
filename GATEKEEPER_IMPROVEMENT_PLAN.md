# GATEKEEPER IMPROVEMENT PLAN
# Safe Method SWMS + Risk Assessment Platform
# Version: 2026-03-27 | Supersedes prior plan versions

---

## CURRENT TRUTH

Gatekeeper / Safe Method is no longer just a SWMS generator.
It now has two live document paths in the codebase:
- SWMS generation
- Standalone Risk Assessment generation

The current product reality is:
- SWMS remains the primary, most mature workflow
- Mode 04 upload/extract/generate is a major active path and must be treated as release-critical
- Risk Assessment (RA) is now a real product path and must be planned, tested, and polished as such
- A future combined Unitas-style project WHS control pack is a separate product mode, not a toggle on the current SWMS flow

Guiding principle:
- reliability and document trust come before expansion
- one strict template/render contract per document type
- benchmark-based output, not freeform AI invention

---

## WHAT IS STABLE NOW

### SWMS runtime
- Active SWMS DOCX generation flows through the current `render_swms_document()` path
- Legacy old-template DOCX runtime paths have been neutralised from the main user flows
- Mode 04 reliability work has improved error surfacing, preflight validation, status sequencing, and misleading UI cleanup
- Live dashboard now exposes the RA path instead of treating it as coming soon

### Domain quality
- D001 tilt-up sequence: CLOSED
- D002 superseded unit reference: CLOSED
- D003 wrong HRCW flag tilt-up: CLOSED
- D005 fall hierarchy reference: CLOSED
- D006 plain English task-name coverage: CLOSED
- Reference job warning set: CLOSED to 0 warnings in the latest known baseline

### Risk Assessment path
- `/generate/ra` exists
- `/render/ra`, `/render/ra/pdf`, and `/render/ra/both` exist
- standalone RA renderer exists
- dashboard entry path to `/ra` now exists in the current repo state

---

## RELEASE GATE

A release is not clean unless these flows pass.

### Core release checklist

| Flow | Steps | Pass condition |
|------|-------|---------------|
| 1. Quick Start SWMS | Describe job -> generate -> review -> confirm -> download | Document downloads, task sequence correct, no contradictory status states |
| 2. Upload Document SWMS | Upload scope/source file -> extract -> review -> generate -> download | Extraction fields populate, generation completes, real errors shown on failure |
| 3. Upgrade SWMS | Upload existing SWMS -> analyse gaps -> generate -> download | Gaps identified, new SWMS generated |
| 4. API key auth | POST `/v1/generate/stream` with `X-API-Key` | SSE streams correctly, 200 OK |
| 5. SWMS sequencing | Generate tilt-up or equivalent complex job | Task ordering and major controls remain correct |
| 6. Standalone RA | Dashboard -> `/ra` -> generate -> render -> download | RA flow loads, hazards render, file downloads correctly |
| 7. Failure transparency | Trigger one known failure in extract/render/generate | User sees a meaningful message, not a mystery failure |

### Coverage gaps to close next

| Gap | Risk | Fix |
|-----|------|-----|
| Mode 04 end-to-end automated coverage | High-value live path regresses silently | Add scripted/manual regression checklist and later browser automation |
| RA route and RA document flow | Newly exposed path may drift without tests | Add targeted RA smoke coverage |
| Renderer/template validation | Template swaps and table remaps can silently regress output | Add self-validating renderer/template checks with golden samples |
| API key auth automation | Service path still under-tested | Add auth path test coverage |
| Multi-user generation overlap | Concurrency issues could surface under load | Add lightweight concurrent request verification |

---

## CURRENT PRIORITIES

Priority order reflects fastest user-impact and trust gain.

### Priority 1 — Reliability and trust hardening

1. Real error surfacing everywhere users can fail
2. Remove dead or misleading UI immediately
3. Keep status states mutually exclusive
4. Add preflight validation before expensive actions
5. Tighten server-side validation for direct API paths
6. Standardise filenames, footer text, and download naming across flows
7. Add a clear consultant-review-required note where documents are generated/downloaded

### Priority 2 — SWMS stability and quality

1. Preserve one strict SWMS template/render contract
2. Continue deterministic domain-quality cleanup only where still open
3. Add automated renderer/template validation against known-good outputs
4. Expand targeted integration coverage around review/download and upload/extract/generate
5. Keep output lean, benchmark-based, and project-specific

### Priority 3 — Risk Assessment stabilisation

1. Make `/ra` a first-class, tested path
2. Align RA UI labels, filename conventions, and disclaimers
3. Bring RA renderer closer to the approved benchmark style and structure
4. Add RA-specific release checks before calling the feature stable
5. Separate “standalone RA” from any future “combined WHS control pack” work

### Priority 4 — Commercial and platform readiness

1. Mobile/responsive improvements for real site use
2. Billing/subscription gating only after core reliability is strong
3. Team / organisation accounts
4. SDK / integration packaging only after product behavior is stable enough to expose externally

---

## SWMS IMPROVEMENT TRACK

### A. Reliability and validation
- Add server-side validation to all generation entry points
- Consolidate duplicated normalization logic used across paths
- Retire or remove dead duplicate endpoints once the live path is confirmed stable
- Continue replacing generic frontend errors with exact backend messages where safe

### B. Renderer / template discipline
- Maintain a single approved SWMS template contract for the live SWMS path
- Any template change must be verified structurally before renderer edits
- No redesign-on-the-fly during rendering fixes
- Golden-output validation should become a required quality gate for renderer changes

### C. Output quality
- Continue using deterministic inference and benchmark-based control logic as the floor
- Avoid generic AI padding
- Prefer specific, observable controls and hold points
- Keep consultant review as the final quality gate before issue

---

## RISK ASSESSMENT TRACK

### Phase 1 — Expose and stabilise the existing RA path
- Dashboard route to RA
- RA mode selection on page load
- RA generation/render smoke test
- RA filename, footer, and disclaimer consistency
- RA release checklist entry added

### Phase 2 — RA output alignment
- Align standalone RA output to the approved benchmark examples
- Review cover fields, hazard register structure, review/sign-off wording, footer format, and black-and-white styling
- Add targeted RA regression checks

### Phase 3 — Decide product boundary
Choose clearly between:
- Standalone RA as a separate product mode, or
- A broader project-level control pack mode

Do not blur these in implementation.

---

## FUTURE MODE — COMBINED PROJECT WHS CONTROL PACK

This is a separate initiative from the current SWMS and standalone RA flows.

Target output:
- HRCW Register
- Hold Point Schedule
- Project Risk Assessment / Risk Register
- Short SWMS Review Benchmark Note
- single combined `.docx`

This mode should only begin after:
1. SWMS flow is stable
2. standalone RA flow is stable
3. benchmark rules and output structure are locked
4. release validation for current modes is strong

Do not treat this as a small extension of the current SWMS renderer.
It is a distinct document product.

---

## BENCHMARK / CONTROL LIBRARY

The original “Gold Standard Control Library” idea is still aligned, but it should now be framed as a shared benchmark library rather than only a control-writer enhancement.

Goal:
- approved benchmark controls, hold points, and sequencing guidance that both SWMS and RA generation can lean on

Near-term use:
- improve specificity without inviting freeform AI drift
- reduce recurring inference/content quality gaps
- support lean, repeatable output

This track should follow reliability hardening, not displace it.

---

## COMMERCIAL / PLATFORM TRACKS

These remain valid, but not ahead of trust and runtime stability.

### Mobile responsive UI
- Review/download flows on phone
- camera-roll upload behavior
- practical site usability

### Billing / Stripe
- only after core flows are stable enough that charging users will not amplify support pain

### Team / organisation accounts
- document library
- shared project access
- PM/foreman review flow

### SDK / integration packaging
- only after public behavior and contracts are stable enough to support external consumers

---

## DEFERRED / REVISIT

| Item | Current position |
|------|------------------|
| Large architectural refactors | Avoid during bug-fix and stabilisation periods |
| Single-call architecture | Still deferred |
| Feedback-loop generation | Still deferred |
| Big template migrations without validation harness | Not safe |
| Stream timeout assumption | Revisit as part of reliability hardening |
| Aggressive expansion before tests improve | Not recommended |

---

## DOMAIN BACKLOG

Open known issue:
- D004: crane licence wording should be generalised to the appropriate HRWL for crane class used

Closed / no longer backlog priorities:
- D005 closed
- D006 closed
- previous 6 reference-job warnings closed in the latest known baseline

Continue tracking true domain issues in `KNOWN_ISSUES_DOMAIN.md`.
Do not leave stale items open in multiple planning files.

---

## STRATEGIC CONTEXT

There are now three meaningful strategic paths:

1. **Reliable SWMS product**
- mature the current SWMS workflow
- deepen trust, validation, and benchmark quality

2. **Reliable standalone RA product**
- stabilise the newly exposed RA flow
- make it a first-class path with proper testing and output alignment

3. **Future combined WHS control pack**
- only after the first two are solid
- treat as a distinct product mode, not a hidden extension

Current recommendation:
- stabilise SWMS and RA first
- delay major combined-pack work until the current runtime experience is consistently trustworthy

---

## NEXT IMPLEMENTATION ORDER

1. Reliability / trust hardening still open in the live app
2. SWMS release gate tightening and renderer/template validation
3. RA smoke testing and output alignment
4. D004 domain cleanup
5. Mobile usability improvements
6. Billing and organisation features
7. Combined project WHS control pack discovery/specification

---

## SUCCESS DEFINITION

The product is aligned when:
- user-facing failures are understandable
- dead/misleading UI is removed
- each document mode has one clear contract
- release gates reflect the real live flows
- backlog status matches source reality
- SWMS and RA are treated as separate current products
- future combined-pack work is explicit, not implied
