-- Phase 1 (per docs/pims_site_visit_report_spec.md):
-- Create public.checklist_items as the runtime checklist source for the
-- Site Visit Report pipeline. pims/audit_checklist.xlsx is a one-time
-- SEED input — never read at runtime (spec invariant #2).
--
-- Schema drift on this table is BLOCKING per spec invariant #7. The
-- DO block at the top runs FIRST and aborts the migration loudly if
-- any expected column is missing on a pre-existing table. Adding new
-- columns is permitted (the guard only enforces "expected ⊆ actual").

-- ─────────────────────────────────────────────────────────────────────
-- Drift guard (verbatim from docs/pims_site_visit_report_spec.md:129)
-- ─────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    expected_columns text[] := ARRAY[
        'id', 'category_no', 'category_name', 'item_no',
        'criteria', 'instruction', 'ccvs_category', 'ccvs_code',
        'project_value_tier'
    ];
    col text;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'checklist_items'
    ) THEN
        FOREACH col IN ARRAY expected_columns LOOP
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'checklist_items'
                  AND column_name = col
            ) THEN
                RAISE EXCEPTION
                    'checklist_items schema drift: column "%" missing', col;
            END IF;
        END LOOP;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────
-- Table
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.checklist_items (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Category grouping (e.g. "01" / "Planning and Risk Management")
    category_no         text NOT NULL,
    category_name       text NOT NULL,

    -- Item number within the category (e.g. "01"). Stored as text so
    -- leading zeros and any future "01a" sub-numbering survive.
    item_no             text NOT NULL,

    -- The audit question (e.g. "Is the project risk assessment completed
    -- (WHS Reg cl.34-38)?") and the imperative instruction the auditor
    -- follows on site.
    criteria            text NOT NULL,
    instruction         text NOT NULL,

    -- CCVS taxonomy linkage. Optional because some checklist items don't
    -- map cleanly to a single CCVS code.
    ccvs_category       text,
    ccvs_code           text,

    -- Which $250K tier this row applies to. The xlsx ships two sheets
    -- (one per tier); each becomes a row tagged with its tier. An item
    -- that applies to both tiers gets TWO rows — the seed pipeline
    -- enforces this; the schema does not deduplicate.
    project_value_tier  text NOT NULL
                        CHECK (project_value_tier IN ('high', 'low')),

    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    -- One row per (tier, category_no, item_no) — prevents accidental
    -- duplicate seeding from re-running the import script.
    UNIQUE (project_value_tier, category_no, item_no)
);

-- Frequent runtime filter: "give me every checklist item for this tier,
-- in audit order".
CREATE INDEX IF NOT EXISTS idx_checklist_items_tier_order
    ON public.checklist_items (project_value_tier, category_no, item_no);

-- Updated-at trigger reuses the project-wide pims_set_updated_at()
-- function defined alongside the other PIMS tables.
DROP TRIGGER IF EXISTS trg_checklist_items_updated_at ON public.checklist_items;
CREATE TRIGGER trg_checklist_items_updated_at
    BEFORE UPDATE ON public.checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION public.pims_set_updated_at();

-- ─────────────────────────────────────────────────────────────────────
-- RLS
-- ─────────────────────────────────────────────────────────────────────
-- Reference data, but the backend is the only consumer. Service role
-- bypasses RLS by default; everyone else (anon, authenticated) gets
-- nothing without an explicit policy. No policy is created here on
-- purpose — RLS-enabled with no policy denies all non-bypass access,
-- which is what we want.
ALTER TABLE public.checklist_items ENABLE ROW LEVEL SECURITY;

-- Belt-and-braces: explicitly drop any anon/authenticated policies
-- that may have been added by hand on a pre-existing instance, so the
-- migration converges to "service-role only".
DO $$
DECLARE
    pol record;
BEGIN
    FOR pol IN
        SELECT polname FROM pg_policy
         WHERE polrelid = 'public.checklist_items'::regclass
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.checklist_items', pol.polname);
    END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────
-- Post-condition assertions (run on every migration application)
-- ─────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    missing_count int;
BEGIN
    SELECT COUNT(*) INTO missing_count
      FROM unnest(ARRAY[
          'id', 'category_no', 'category_name', 'item_no',
          'criteria', 'instruction', 'ccvs_category', 'ccvs_code',
          'project_value_tier'
      ]) AS expected(col)
     WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'checklist_items'
          AND column_name = expected.col
     );
    IF missing_count > 0 THEN
        RAISE EXCEPTION
            'checklist_items post-condition failed: % expected columns missing',
            missing_count;
    END IF;
END $$;
