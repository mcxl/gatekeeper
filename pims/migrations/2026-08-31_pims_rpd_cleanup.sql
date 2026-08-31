-- PIMS RPD cleanup: project manager mapping for audit projects.
-- This migration is additive and does not delete or alter audit observations.
ALTER TABLE public.pims_audits
  ADD COLUMN IF NOT EXISTS project_manager text;

WITH mapped_managers(normalized_address, manager_name) AS (
  VALUES
    ('1729mountstpyrmont', 'Yas N'),
    ('3943milsonpointrdcremornepoint', 'David O'),
    ('2elizabethbaycreselizabethbay', 'Jim G'),
    ('1329russelstreetlilyfield', 'David O'),
    ('9698hampdenrdrussellea', 'David O / DO')
), candidates AS (
  SELECT
    a.id,
    regexp_replace(lower(coalesce(a.site_address, '')), '[^a-z0-9]+', '', 'g') AS normalized_address,
    regexp_replace(lower(coalesce(a.site_name, '')), '[^a-z0-9]+', '', 'g') AS normalized_name
  FROM public.pims_audits AS a
)
UPDATE public.pims_audits AS a
SET project_manager = m.manager_name
FROM candidates AS c
JOIN mapped_managers AS m ON m.normalized_address IN (c.normalized_address, c.normalized_name)
WHERE a.id = c.id
  AND (a.project_manager IS NULL OR btrim(a.project_manager) = '');

CREATE INDEX IF NOT EXISTS idx_pims_audits_project_manager
  ON public.pims_audits(project_manager);
