-- ============================================================
-- PIMS Migration - Safe Method / Gatekeeper
-- Run in Supabase SQL editor for a fresh client project.
-- Matches live RPD schema as of 2026-04-21.
--
-- Going-forward policy: this file is the source of truth for the
-- PIMS schema. All schema changes MUST land here first (or as a
-- numbered file in supabase/migrations/) and then be applied via
-- `apply_migration`. Applying DDL through the Supabase dashboard
-- or raw MCP execute_sql without a committed file produces drift.
-- ============================================================

-- ---- Extensions ------------------------------------------------
-- pgcrypto: gen_random_uuid() for uuid primary keys.
-- uuid-ossp: kept for backward compatibility with any installer
-- who relies on it. Supabase projects usually have both enabled
-- by default; CREATE EXTENSION IF NOT EXISTS is a no-op if so.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---- Shared trigger function ----------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- ============================================================
-- sites: master register of client job sites
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sites (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_code      text UNIQUE,
    address_raw       text NOT NULL,
    street_address    text,
    suburb            text,
    state             text DEFAULT 'NSW',
    postcode          text,
    -- Intentionally no default: set client_name per-install, do not
    -- inherit a hard-coded value from another client's schema.
    client_name       text,
    site_contact      text,
    strata_plan       text,
    building_class    text,
    project_value     numeric,
    active            boolean DEFAULT true,
    first_audit_date  date,
    last_audit_date   date,
    audit_count       integer DEFAULT 0,
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sites_active ON public.sites(active);
CREATE INDEX IF NOT EXISTS idx_sites_suburb ON public.sites(suburb);

DROP TRIGGER IF EXISTS trg_sites_updated_at ON public.sites;
CREATE TRIGGER trg_sites_updated_at
    BEFORE UPDATE ON public.sites
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- pims_audits: one row per audit session
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pims_audits (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_ref            text NOT NULL UNIQUE,
    site_name            text NOT NULL,
    site_address         text,
    principal_contractor text,
    audit_date           date NOT NULL,
    auditor              text,
    imported_at          timestamptz DEFAULT now(),
    imported_by          uuid REFERENCES auth.users(id),
    notes                text
);

CREATE INDEX IF NOT EXISTS idx_pims_audits_site ON public.pims_audits(site_name);
CREATE INDEX IF NOT EXISTS idx_pims_audits_date ON public.pims_audits(audit_date);

-- ============================================================
-- pims_staging: raw field captures pending review/enrichment
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pims_staging (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id                  uuid REFERENCES public.pims_audits(id) ON DELETE CASCADE,
    seq_no                    integer,
    photo_id                  text,
    photo_url                 text,
    filename                  text,
    observation_date          date,
    observation_text          text NOT NULL,
    site_address              text,
    submitted_at              timestamptz DEFAULT now(),
    submitted_by              text,
    device_info               text,

    -- Enrichment (Haiku)
    enriched                  boolean DEFAULT false,
    enriched_at               timestamptz,
    conformance_status        text CHECK (conformance_status IN ('Compliant','Conditional','NCR','Info')),
    ccvs_code                 text,
    ccvs_category             text,
    ccvs_confidence           text CHECK (ccvs_confidence IN ('High','Medium','Low')),
    action_required           boolean DEFAULT false,
    action_description        text,
    responsible               text,
    due_category              text CHECK (due_category IN ('Immediate','Next audit','Ongoing','N/A')),
    monitoring_note           text,
    observation_text_enriched text,
    legal_reference           text,
    recommendation            text,

    -- Review workflow
    review_status             text DEFAULT 'Pending'
                              CHECK (review_status IN ('Pending','Approved','Rejected')),
    reviewed_at               timestamptz,
    reviewed_by               text,
    review_notes              text
);

CREATE INDEX IF NOT EXISTS idx_staging_audit    ON public.pims_staging(audit_id);
CREATE INDEX IF NOT EXISTS idx_staging_status   ON public.pims_staging(review_status);
CREATE INDEX IF NOT EXISTS idx_staging_enriched ON public.pims_staging(enriched);

-- ============================================================
-- pims_observations: approved/live audit observations
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pims_observations (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    staging_id                uuid UNIQUE
                              REFERENCES public.pims_staging(id) ON DELETE SET NULL,
    audit_id                  uuid REFERENCES public.pims_audits(id) ON DELETE SET NULL,
    site_id                   uuid REFERENCES public.sites(id) ON DELETE SET NULL,
    seq_no                    integer,
    audit_date                date,
    observation_date          date,
    observation_text          text NOT NULL,
    observation_text_enriched text,
    site_address              text,
    filename                  text,
    photo_url                 text,
    photo_refs                text,
    submitted_by              text,
    device_info               text,

    -- Enrichment
    enriched                  boolean NOT NULL DEFAULT true,
    enriched_at               timestamptz,
    conformance_status        text CHECK (conformance_status IN ('Compliant','Conditional','NCR','Info')),
    ccvs_code                 text,
    ccvs_category             text,
    ccvs_confidence           text CHECK (ccvs_confidence IN ('High','Medium','Low')),
    action_required           boolean NOT NULL DEFAULT false,
    action_description        text,
    responsible               text,
    due_category              text CHECK (due_category IN ('Immediate','Next audit','Ongoing','N/A')),
    monitoring_note           text,
    legal_reference           text,
    legal_ref                 text,
    recommendation            text,
    prepared_by               text,

    -- Ingest provenance
    staging                   boolean DEFAULT true,
    needs_review              boolean DEFAULT false,
    source_pdf                text,
    imported_at               timestamptz DEFAULT now(),

    -- Review workflow
    review_status             text NOT NULL DEFAULT 'Approved'
                              CHECK (review_status IN ('Pending','Approved','Rejected')),
    approved_by               text,
    approved_at               timestamptz NOT NULL DEFAULT now(),

    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pims_obs_audit_id        ON public.pims_observations(audit_id);
CREATE INDEX IF NOT EXISTS idx_pims_obs_conformance     ON public.pims_observations(conformance_status);
CREATE INDEX IF NOT EXISTS idx_pims_obs_ccvs_code       ON public.pims_observations(ccvs_code);
CREATE INDEX IF NOT EXISTS idx_pims_obs_approved_at     ON public.pims_observations(approved_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_site_id     ON public.pims_observations(site_id);
CREATE INDEX IF NOT EXISTS idx_observations_site_address ON public.pims_observations(site_address);
CREATE INDEX IF NOT EXISTS idx_observations_staging     ON public.pims_observations(staging);
CREATE INDEX IF NOT EXISTS idx_pims_obs_staging_id      ON public.pims_observations(staging_id);

-- Partial unique index: a single staging row can only be approved once.
CREATE UNIQUE INDEX IF NOT EXISTS idx_pims_obs_staging_approved
    ON public.pims_observations(staging_id)
    WHERE review_status = 'Approved';

DROP TRIGGER IF EXISTS trg_pims_obs_updated_at ON public.pims_observations;
CREATE TRIGGER trg_pims_obs_updated_at
    BEFORE UPDATE ON public.pims_observations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- Row Level Security
-- The backend talks to Supabase using a service_role key which
-- bypasses RLS. The dashboard HTML is shipped with the anon key
-- (needs SELECT + UPDATE for live editing, INSERT for capture).
-- ============================================================

ALTER TABLE public.sites              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pims_audits        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pims_staging       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pims_observations  ENABLE ROW LEVEL SECURITY;

-- sites: anon read-only (dashboard needs site list); writes via service role.
DROP POLICY IF EXISTS sites_anon_read ON public.sites;
CREATE POLICY sites_anon_read ON public.sites
    FOR SELECT TO anon USING (true);

-- pims_audits: anon read/insert (Snap shortcut uses anon via backend, but
-- service role is the actual writer in production - these policies are
-- the safety net for any direct client-side usage).
DROP POLICY IF EXISTS pims_audits_anon_read   ON public.pims_audits;
CREATE POLICY pims_audits_anon_read ON public.pims_audits
    FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS pims_audits_anon_insert ON public.pims_audits;
CREATE POLICY pims_audits_anon_insert ON public.pims_audits
    FOR INSERT TO anon WITH CHECK (true);

-- pims_staging: anon full read+insert+update so the dashboard can submit
-- field captures and update review_status directly. DELETE is restricted
-- to service_role (routed through /pims/staging/{id}/delete).
DROP POLICY IF EXISTS pims_staging_anon_read   ON public.pims_staging;
CREATE POLICY pims_staging_anon_read ON public.pims_staging
    FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS pims_staging_anon_insert ON public.pims_staging;
CREATE POLICY pims_staging_anon_insert ON public.pims_staging
    FOR INSERT TO anon WITH CHECK (true);
DROP POLICY IF EXISTS pims_staging_anon_update ON public.pims_staging;
CREATE POLICY pims_staging_anon_update ON public.pims_staging
    FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- pims_observations: anon read/insert/update. DELETE via service role.
DROP POLICY IF EXISTS pims_observations_anon_read   ON public.pims_observations;
CREATE POLICY pims_observations_anon_read ON public.pims_observations
    FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS pims_observations_anon_insert ON public.pims_observations;
CREATE POLICY pims_observations_anon_insert ON public.pims_observations
    FOR INSERT TO anon WITH CHECK (true);
DROP POLICY IF EXISTS pims_observations_anon_update ON public.pims_observations;
CREATE POLICY pims_observations_anon_update ON public.pims_observations
    FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- Note: service_role automatically bypasses RLS on all tables. An
-- explicit service_role policy is not required and is deliberately
-- omitted to keep the file minimal.

-- ============================================================
-- Post-migration: remind PostgREST to refresh its schema cache.
-- Supabase does this automatically via DDL event triggers, but the
-- NOTIFY is idempotent and useful for manual re-runs.
-- ============================================================
NOTIFY pgrst, 'reload schema';
