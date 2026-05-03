-- Migration 006: precedent provenance on pims_staging
-- Tracks which precedent examples informed each enrichment, plus a
-- guard timestamp to prevent double-counting usage on demote/re-approve.

ALTER TABLE public.pims_staging
    ADD COLUMN IF NOT EXISTS precedent_example_ids uuid[],
    ADD COLUMN IF NOT EXISTS precedent_match_summary jsonb,
    ADD COLUMN IF NOT EXISTS precedent_usage_recorded_at timestamptz;

NOTIFY pgrst, 'reload schema';
