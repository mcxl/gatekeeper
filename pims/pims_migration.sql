-- ============================================================
-- PIMS Migration — Safe Method / Gatekeeper
-- Run in Supabase SQL editor
-- ============================================================

-- Audit sessions (one row per PIMS import)
CREATE TABLE IF NOT EXISTS pims_audits (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_ref       text NOT NULL,                          -- e.g. "Unitas-20260226"
    site_name       text NOT NULL,
    site_address    text,
    principal_contractor text,
    audit_date      date NOT NULL,
    auditor         text,
    imported_at     timestamptz DEFAULT now(),
    imported_by     uuid REFERENCES auth.users(id),
    notes           text
);

-- pims_staging: incoming observations pending review
CREATE TABLE IF NOT EXISTS public.pims_staging (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id                  uuid REFERENCES public.pims_audits(id),
    seq_no                    integer,
    observation_date          date,
    observation_text          text,
    filename                  text,
    photo_url                 text,
    photo_base64              text,
    submitted_by              text,
    device_info               text,
    enriched                  boolean DEFAULT false,
    enriched_at               timestamptz,
    conformance_status        text,
    ccvs_code                 text,
    ccvs_category             text,
    ccvs_confidence           text,
    action_required           boolean DEFAULT false,
    action_description        text,
    responsible               text,
    due_category              text DEFAULT 'N/A',
    monitoring_note           text,
    observation_text_enriched text,
    legal_reference           text,
    review_status             text DEFAULT 'Pending',
    submitted_at              timestamptz DEFAULT now()
);

-- Unique seq_no per audit
CREATE UNIQUE INDEX IF NOT EXISTS idx_staging_audit_seq
    ON public.pims_staging(audit_id, seq_no);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_staging_audit_id
    ON public.pims_staging(audit_id);
CREATE INDEX IF NOT EXISTS idx_staging_review_status
    ON public.pims_staging(review_status);
CREATE INDEX IF NOT EXISTS idx_staging_submitted_at
    ON public.pims_staging(submitted_at DESC);

-- RLS (basic)
ALTER TABLE public.pims_staging ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all_staging" ON public.pims_staging;
CREATE POLICY "service_role_all_staging" ON public.pims_staging
    FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_read_staging" ON public.pims_staging;
CREATE POLICY "anon_read_staging" ON public.pims_staging
    FOR SELECT TO anon USING (true);

-- One row per PIMS observation
CREATE TABLE IF NOT EXISTS pims_observations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id            uuid NOT NULL REFERENCES pims_audits(id) ON DELETE CASCADE,
    seq_no              integer NOT NULL,
    photo_id            text,
    filename            text,
    observation_date    date,
    observation_text    text NOT NULL,

    -- Enrichment fields (applied by Claude, confirmed by user)
    conformance_status  text CHECK (conformance_status IN ('Compliant','Conditional','NCR','Info')),
    ccvs_code           text,
    ccvs_category       text,
    action_required     boolean DEFAULT false,
    action_description  text,
    responsible         text,
    due_category        text CHECK (due_category IN ('Immediate','Next audit','Ongoing','N/A')),
    monitoring_note     text,

    -- Close-out tracking
    closeout_status     text DEFAULT 'N/A' CHECK (closeout_status IN ('Open','In Progress','Closed','N/A')),
    closed_date         date,
    closed_by           text,
    closeout_notes      text,

    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

-- Index for fast dashboard queries
CREATE INDEX IF NOT EXISTS idx_pims_obs_audit      ON pims_observations(audit_id);
CREATE INDEX IF NOT EXISTS idx_pims_obs_status     ON pims_observations(conformance_status);
CREATE INDEX IF NOT EXISTS idx_pims_obs_ccvs       ON pims_observations(ccvs_code);
CREATE INDEX IF NOT EXISTS idx_pims_obs_closeout   ON pims_observations(closeout_status);
CREATE INDEX IF NOT EXISTS idx_pims_audits_site    ON pims_audits(site_name);
CREATE INDEX IF NOT EXISTS idx_pims_audits_date    ON pims_audits(audit_date);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION pims_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pims_obs_updated_at ON pims_observations;
CREATE TRIGGER pims_obs_updated_at
    BEFORE UPDATE ON pims_observations
    FOR EACH ROW EXECUTE FUNCTION pims_set_updated_at();

-- ============================================================
-- Row Level Security
-- Enable RLS — standalone HTML uses anon key, reads all rows
-- ============================================================

ALTER TABLE pims_audits       ENABLE ROW LEVEL SECURITY;
ALTER TABLE pims_observations ENABLE ROW LEVEL SECURITY;

-- Allow anon reads (dashboard is public-read within your org)
CREATE POLICY "pims_audits_read"       ON pims_audits       FOR SELECT USING (true);
CREATE POLICY "pims_observations_read" ON pims_observations FOR SELECT USING (true);

-- Allow authenticated updates (close-out panel)
CREATE POLICY "pims_observations_update" ON pims_observations
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Allow authenticated inserts (import script)
CREATE POLICY "pims_audits_insert"       ON pims_audits       FOR INSERT WITH CHECK (true);
CREATE POLICY "pims_observations_insert" ON pims_observations FOR INSERT WITH CHECK (true);
