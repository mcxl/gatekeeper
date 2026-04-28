-- Add closeout workflow columns referenced by the PIMS dashboard.
-- The frontend PATCHes pims_observations with closeout_status / closed_date /
-- closed_by / closeout_notes, but the columns were never added to the table,
-- causing PostgREST schema-cache errors on save.

ALTER TABLE public.pims_observations
    ADD COLUMN IF NOT EXISTS closeout_status text
        CHECK (closeout_status IN ('Open','In Progress','Closed','N/A')),
    ADD COLUMN IF NOT EXISTS closed_date     date,
    ADD COLUMN IF NOT EXISTS closed_by       text,
    ADD COLUMN IF NOT EXISTS closeout_notes  text;

CREATE INDEX IF NOT EXISTS idx_pims_obs_closeout_status
    ON public.pims_observations(closeout_status);

NOTIFY pgrst, 'reload schema';
