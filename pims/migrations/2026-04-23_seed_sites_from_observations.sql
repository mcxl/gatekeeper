-- Seed public.sites from pims_observations and backfill pims_observations.site_id.
--
-- Run on the rpd-pims Supabase project (nebdpofqglfyfyqqodni) on 2026-04-23
-- via the Supabase MCP, in the order below. Captured here for audit trail.
-- This is backfill data, not schema — do not include in automated migration
-- runners that apply pims/pims_migration.sql.
--
-- Context: public.sites was empty, so GET /pims/sites/eligible (which filters
-- active=true AND project_value IS NOT NULL) returned [] and the dashboard
-- audit-report modal showed the "No eligible sites" banner. 919 observations
-- existed but none carried a site_id. Plan approved with amendments (safety
-- check between Step 1 and Step 2, plus a pilot site).

-- ─────────────────────────────────────────────────────────────────────────
-- Dry-run counts (for the audit log; not executed)
-- ─────────────────────────────────────────────────────────────────────────
-- SELECT
--   (SELECT COUNT(DISTINCT site_address) FROM public.pims_observations
--     WHERE site_address IS NOT NULL)              AS distinct_addresses,  -- 28
--   (SELECT COUNT(*) FROM public.pims_observations
--     WHERE site_id IS NULL)                        AS obs_needing_backfill, -- 919
--   (SELECT COUNT(*) FROM public.pims_observations) AS total_obs;           -- 919

-- ─────────────────────────────────────────────────────────────────────────
-- Step 1 — Seed sites from distinct non-null observation addresses
--   Result: 28 rows inserted (one per distinct address), project_value=NULL,
--   client_name=NULL, active=true. Deliberately NULL project_value: no site
--   will be eligible for /sites/eligible until an operator sets it.
-- ─────────────────────────────────────────────────────────────────────────
INSERT INTO public.sites (address_raw, active)
SELECT DISTINCT site_address, true
  FROM public.pims_observations
 WHERE site_address IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM public.sites s WHERE s.address_raw = pims_observations.site_address
   );

-- ─────────────────────────────────────────────────────────────────────────
-- Safety check (must return 0 before Step 2). Any row where an observation
-- already carries a site_id that disagrees with the match-by-address row
-- would indicate data we'd silently overwrite. Confirmed 0 on 2026-04-23.
-- ─────────────────────────────────────────────────────────────────────────
-- SELECT COUNT(*)
--   FROM public.pims_observations o
--   JOIN public.sites s ON s.address_raw = o.site_address
--  WHERE o.site_id IS NOT NULL
--    AND o.site_id <> s.id;   -- expected 0

-- ─────────────────────────────────────────────────────────────────────────
-- Step 2 — Backfill pims_observations.site_id from sites by address match
--   Result: 839 rows updated. The remaining 80 NULL site_id rows all have
--   site_address IS NULL too (unattributable observations); leaving them
--   NULL is correct — they should not be mapped to any site.
-- ─────────────────────────────────────────────────────────────────────────
UPDATE public.pims_observations o
   SET site_id = s.id
  FROM public.sites s
 WHERE o.site_id IS NULL
   AND o.site_address = s.address_raw;

-- ─────────────────────────────────────────────────────────────────────────
-- Step 4 (pilot) — Set project_value on one recognisable site so the
--   audit-report modal is testable live. No other site is eligible until
--   an operator provides its project_value.
-- ─────────────────────────────────────────────────────────────────────────
UPDATE public.sites
   SET project_value = 2500000
 WHERE address_raw = '1208 Pacific Highway Pymble';

-- ─────────────────────────────────────────────────────────────────────────
-- Post-execution verification (not part of the migration, run to confirm):
--   SELECT id, address_raw, project_value FROM public.sites
--    WHERE active = true AND project_value IS NOT NULL
--    ORDER BY address_raw;
-- Expected: exactly 1 row (the pilot), matching /pims/sites/eligible.
-- ─────────────────────────────────────────────────────────────────────────
