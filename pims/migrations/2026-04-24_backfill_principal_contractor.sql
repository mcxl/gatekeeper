-- Backfill pims_audits.principal_contractor ahead of Phase H Commit 3's
-- strict-422 on unknown contractor. Phase 0-G shipped without this column
-- populated; without backfill, every audit-report request would 422 once
-- the new gate lands.
--
-- Real audit (RPD-SSA, 33 approved observations) -> Robertson's Remedial
-- and Painting. Three scaffold audits (0 observations each) get a
-- 'TBD - test audit' placeholder purely for data hygiene; they would 409
-- (no approved observations) before the 422 gate ever triggers, so the
-- value is not functionally important but stops the column looking
-- abandoned on inspection.
--
-- APPLIED to prod Supabase 2026-04-24 via MCP ahead of code land. This
-- file is the reproducible record; re-running it is idempotent because
-- of the NULL/empty guard.

UPDATE public.pims_audits
SET principal_contractor = 'Robertson''s Remedial and Painting'
WHERE id = 'e719c30e-dcab-47bd-b415-ac5fa63ccb42'
  AND (principal_contractor IS NULL OR TRIM(principal_contractor) = '');

UPDATE public.pims_audits
SET principal_contractor = 'TBD - test audit'
WHERE id IN (
  '4ebcf18b-bc83-4d83-8b05-89a3a0a48e80',
  '6dfdce03-211c-47cb-9dca-71669eff1536',
  'e15194d2-b954-452d-9ee0-38f66d8acc58'
)
  AND (principal_contractor IS NULL OR TRIM(principal_contractor) = '');
