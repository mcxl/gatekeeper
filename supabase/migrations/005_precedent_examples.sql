-- Migration 005: pims_precedent_examples
-- Historical RPD audit-report precedent corpus used to inform live PIMS
-- enrichment. Idempotent unique key on (source_kind, source_file, source_item_key).
-- source_hash is collision-detection only and does NOT participate in upsert.

CREATE TABLE IF NOT EXISTS public.pims_precedent_examples (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_kind text NOT NULL,
  source_file text NOT NULL,
  source_item_key text NOT NULL,
  source_hash text,
  finding_text text,
  recommendation_text text,
  observation_text text,
  normalized_key text,
  ccvs_code text,
  ccvs_category text,
  section_name text,
  status_normalized text,
  source_observation_id uuid,
  imported_at timestamptz DEFAULT now(),
  usage_count integer DEFAULT 0,
  last_used_at timestamptz,
  CONSTRAINT pims_precedent_examples_unique UNIQUE (source_kind, source_file, source_item_key)
);

CREATE INDEX IF NOT EXISTS idx_pims_precedent_normalized_key ON public.pims_precedent_examples(normalized_key);
CREATE INDEX IF NOT EXISTS idx_pims_precedent_section ON public.pims_precedent_examples(section_name);
CREATE INDEX IF NOT EXISTS idx_pims_precedent_ccvs_code ON public.pims_precedent_examples(ccvs_code);
CREATE INDEX IF NOT EXISTS idx_pims_precedent_ccvs_cat ON public.pims_precedent_examples(ccvs_category);
CREATE INDEX IF NOT EXISTS idx_pims_precedent_status ON public.pims_precedent_examples(status_normalized);

ALTER TABLE public.pims_precedent_examples ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pims_precedent_anon_read ON public.pims_precedent_examples;
CREATE POLICY pims_precedent_anon_read ON public.pims_precedent_examples
    FOR SELECT TO anon USING (true);

NOTIFY pgrst, 'reload schema';
