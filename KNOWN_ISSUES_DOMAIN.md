# Known Domain Issues — Gatekeeper Output Quality
Tracks WHS accuracy issues found in real generated documents.
Each entry: issue, fix applied, test fixture added, date closed.

---

## CLOSED ISSUES

### D001 — Task sequence reversed for tilt-up construction
**Found:** 2026-03-16, expert review of tilt-up SWMS
**Issue:** Decomposer placed "Remove temporary bracing" as task 1
and "Set up site" as last task — backwards for tilt-up.
**Fix:** Trade-specific sequence rules added to decomposer prompt.
**Fixture:** tests/fixtures/07_tiltup_sequence.json
**Status:** ✅ Closed

### D002 — Superseded unit code RIIOHS204A in outputs
**Found:** 2026-03-16, expert review
**Issue:** RIIOHS204A was superseded in 2022. Current equivalent
is RIIOHS204E per the RII Training Package.
**Fix:** Replaced in control_writer.py and inference_matrix.py.
**Fixture:** test_no_superseded_unit_codes() in test_renderer.py
**Status:** ✅ Closed

### D003 — Wrong HRCW flag for new tilt-up construction
**Found:** 2026-03-16, expert review
**Issue:** "Temporary load-bearing support for structural
alterations or repairs" was incorrectly flagged for new-build
tilt-up. That HRCW item applies to alterations/repairs only.
**Fix:** Removed falsework/tilt-up chain map link. Corrected
hrcw_category wording in falsework entry.
**Fixture:** test_tiltup_sequence_fixture() checks tiltup_precast
flag is set (not structural alteration flag).
**Status:** ✅ Closed

---

## OPEN ISSUES

### D004 — C6 crane licence too specific in outputs
**Found:** 2026-03-16, expert review
**Issue:** Control writer generates "C6 licence" for all crane
work. Correct wording is "appropriate HRWL for crane class used."
**Fix:** Pending
**Fixture:** Pending

### D005 — WHS Reg 2017 s.225 fall hierarchy reference inaccurate
**Found:** 2026-03-16, expert review
**Issue:** s.225 is not the correct regulation for fall hierarchy.
The obligation is in Part 4.4, applies wherever there is a risk
of fall — not only above 2m.
**Fix:** Pending
**Fixture:** Pending

### D006 — Plain English pass not applied to task name field
**Found:** 2026-03-16, internal review
**Issue:** "Inspect and rectify defects" appeared as a task name.
Both "inspect" and "rectify" are banned words.
**Fix:** Pending (separate prompt already issued)
**Fixture:** Pending
