# SDG-SSA Quality Hardening Plan

**Date:** 2026-05-14
**Status:** PROPOSED — awaiting operator approval
**Worktree:** `C:\Users\AlanRichardson\gatekeeper\.claude\worktrees\brave-mestorf-8f2596`
**Branch:** `claude/brave-mestorf-8f2596` (from `main`)

---

## Goal

Apply rpd-ssa-builder's four quality guards (deterministic post-pass, OOXML schema validation, LibreOffice headless smoke, drift checker) plus the `--check` preflight, CHANGELOG discipline, and byte-hash regression to gatekeeper's SSA pipeline. Operator answered **1B / 2**: SDG audits stay in gatekeeper; rpd-ssa-builder's quality patterns are the import.

## Scope

**In scope:**

- Gatekeeper's SSA report-docx output path (`pims/services/ssa_pipeline.py` → `build_ssa_report_docx`), which is shared by RPD and SDG. Hardening SDG necessarily hardens RPD because they share code. State the fact, don't fork it.
- `pims/scripts/run_ssa_pipeline.py` — add `--check` preflight wiring.
- Tests under `tests/test_ssa_pipeline.py` — add deterministic-hash and OOXML schema assertions.

**Out of scope (this plan):**

- Rebranding rpd-ssa-builder; it stays a standalone tool at `G:\My Drive\alan_mcxico\SSA-evidence\SSA rules\`.
- Changing gatekeeper's SDG vs RPD divergence logic (`_BULK_ENDPOINT`, STAGING-NO-BULK-ENDPOINT.txt sentinel).
- Spinning out a separate `sdg-ssa-builder` private GitHub repo. **Recommendation: don't.** Gatekeeper is the active pipeline; a thin wrapper repo would just be the four guards + a CLI — too thin to justify two repos. If split is wanted later, it's a Phase 7 conversation.

## Repo Structure Decision

**Recommended: harden inside gatekeeper.** New subpackage `pims/services/ssa_quality/`:

```
pims/services/ssa_quality/
  __init__.py
  determinism.py        # lifted as-is from rpd-ssa-builder
  oxml_validator.py     # lifted, points at shared %LOCALAPPDATA%\rpd-ssa-validator cache
  libreoffice_smoke.py  # extracted from build_report.py:167-198
  preflight.py          # parameterised port of rpd-ssa-builder src/preflight.py
tools/
  check_ssa_drift.py    # parameterised port of rpd-ssa-builder tools/check_drift.py
docs/
  CHANGELOG-SSA.md      # SSA-scoped changelog, not to clobber any existing root file
```

Wire-ins all live in `pims/services/ssa_pipeline.py` and `pims/scripts/run_ssa_pipeline.py`.

## What Gets Lifted (verified portable)

| Module | Source path | Destination | Self-contained? |
|---|---|---|---|
| Determinism post-pass | `G:\My Drive\alan_mcxico\SSA-evidence\SSA rules\src\determinism.py` (186 lines) | `pims/services/ssa_quality/determinism.py` | **Yes** — stdlib only |
| OOXML validator | `…\SSA rules\src\oxml_validator.py` (200 lines) | `pims/services/ssa_quality/oxml_validator.py` | **Yes** — stdlib only; reuses cached `%LOCALAPPDATA%\rpd-ssa-validator\bin\Release\net8.0\Validate.dll` |
| LibreOffice smoke | `…\SSA rules\build_report.py:167–198` | `pims/services/ssa_quality/libreoffice_smoke.py` | **Yes** — once candidate paths are passed in |
| Drift checker | `…\SSA rules\tools\check_drift.py` (203 lines) | `tools/check_ssa_drift.py` | **Medium** — needs injection of constants instead of importing rpd config |
| `--check` preflight | `…\SSA rules\src\preflight.py` | `pims/services/ssa_quality/preflight.py` | **Medium** — checks are folder-shape and file-presence; need to adapt for SDG/RPD folder naming `YYYY-MM-DD-{RPD,SDG}[-NN]` (per `run_ssa_pipeline.py` line ~102) |

**OOXML validator note:** we do NOT copy the C# project (`_validator/Program.cs`, `Validate.csproj`). The DLL is already built and cached at `%LOCALAPPDATA%\rpd-ssa-validator\bin\Release\net8.0\Validate.dll` by rpd-ssa-builder. Gatekeeper just calls `dotnet <cached-DLL> <docx-path>`. If the cache is missing, fall through to building it via the rpd-ssa-builder source. This avoids duplicating the C# project across two repos.

## Phase Breakdown (checkpoint-driven, ≤3 files per phase)

Each phase: implement → run tests → diff summary → wait for approval → commit. Never push without separate approval.

### Phase 0 — Verify build environment
- Confirm `%LOCALAPPDATA%\rpd-ssa-validator\bin\Release\net8.0\Validate.dll` exists.
- Confirm `C:\Program Files\LibreOffice\program\soffice.exe` exists.
- Confirm `dotnet --version` reports 8.x.
- Run `python -m pytest tests/test_ssa_pipeline.py -q` to capture baseline pass count.
- No code changes. Report results.

### Phase 1 — Determinism post-pass
- Files: `pims/services/ssa_quality/__init__.py`, `pims/services/ssa_quality/determinism.py`, wire in `pims/services/ssa_pipeline.py::build_ssa_report_docx`.
- Test: build a fixture report twice; assert SHA-256 matches.
- Stop condition: hash matches across two builds. If not, debug before proceeding.

### Phase 2 — OOXML schema validator
- Files: `pims/services/ssa_quality/oxml_validator.py`, wire-in in `ssa_pipeline.py` after determinism call.
- Test: pass a known-good fixture; assert exit 0. Pass a deliberately-broken docx; assert non-zero.
- Stop condition: current SSA output validates clean.

### Phase 3 — LibreOffice smoke test
- Files: `pims/services/ssa_quality/libreoffice_smoke.py`, wire-in.
- Test: build → smoke; assert pdf appears in temp dir and is non-empty.
- Timeout: 180s (same as rpd-ssa-builder).

### Phase 4 — `--check` preflight
- Files: `pims/services/ssa_quality/preflight.py`, wire `--check` flag in `pims/scripts/run_ssa_pipeline.py`.
- Test: known-bad folder fails fast; known-good folder passes.

### Phase 5 — Drift checker
- Files: `tools/check_ssa_drift.py`, plus a constants surface (probably a small `pims/services/ssa_quality/contract.py` that names the placeholder tokens, status colours, xlsx headers, font, recipients gatekeeper actually uses).
- Open question: gatekeeper's `ssa_pipeline.py` does token substitution but I haven't yet enumerated its placeholder set the way rpd-ssa-builder's `config.PH_*` does. Phase 5 starts with mapping that surface — possibly 1 read-only investigation commit first.
- Test: drift checker exits 0 on current state.

### Phase 6 — CHANGELOG + byte-hash regression
- Files: `docs/CHANGELOG-SSA.md` (new), `tests/test_ssa_determinism.py` (new fixture-driven hash regression).
- The hash regression test pins the SHA-256 of the fixture build; future drift on output formatting is caught by CI.
- Stop condition: test passes locally.

### Phase 7 — (Optional, gated) Spin out `sdg-ssa-builder` repo
- Only if operator wants visible separation. Recommendation: defer.

## Approval Gates

- After each phase: operator approves the diff before commit.
- No push to `main` (or any branch) without explicit per-push authorisation.
- If any phase touches more than 3 files, pause and re-scope before continuing.

## Stop Conditions

- OOXML validator reports schema errors on current gatekeeper output → stop, surface findings, do not paper over.
- Determinism post-pass fails to make builds byte-identical → stop, diagnose, do not commit half-deterministic output.
- Drift checker turns out to be a poor fit for gatekeeper's token style → drop or rewrite Phase 5; don't force a broken adapter.
- Any phase reveals an architectural decision (e.g., gatekeeper's SDG output needs to be split across two docs) → stop, write the product decision, do not slice further.

## Open Questions (for operator)

1. **Single repo (recommended) vs. separate `sdg-ssa-builder` repo?** Recommend single repo (hardening inside gatekeeper) for the reasons above. Phase 7 is optional.
2. **Determinism scope — docx only, or all three deliverables?** rpd-ssa-builder only deterministically rebuilds the docx because that's its only output. Gatekeeper produces two xlsx files too. xlsx is also a zip-archive with embedded timestamps. Should I extend determinism to xlsx outputs as well? Recommend **yes, but in a later phase** — keep Phase 1 docx-only to match rpd-ssa-builder's exact pattern, then a Phase 1b adds xlsx if desired.
3. **CHANGELOG location.** Recommend `docs/CHANGELOG-SSA.md` to avoid clobbering any existing root-level changelog. Confirm before writing.
4. **Drift checker scope.** Should it check the SDG report template's placeholder set, the xlsx headers in `build_pims_enriched_xlsx`, the staging xlsx headers, or all of the above? Recommend all of the above but split across two passes — template+report first, xlsx headers second.

## Outstanding (separate from this plan)

- Audit folders `2026-05-13_RPD-01` and `2026-05-13_RPD-02` use underscores; rpd-ssa-builder's regex requires hyphens. Rename to `2026-05-13-RPD-01` and `2026-05-13-RPD-02`. Not blocking this plan.

## Next Step

Operator approves this plan (or redirects), then I execute Phase 0 (environment verification, no code changes) and report back.
