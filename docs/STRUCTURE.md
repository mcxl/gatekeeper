# Repository Structure

This repo has four active product boundaries:

- `core/` owns shared contracts, orchestration, validation, review logic, and durable product rules.
- `agents/` owns the SWMS generation agent layer: decomposition, risk assessment, control writing, and assembly.
- `renderers/` owns approved output rendering only. Renderers adapt to approved templates and should not redefine product contracts.
- `pims/` owns the PIMS / SSA product surface, including routes, services, scripts, templates, migrations, and audit-report assets.

Supporting areas:

- `api/` owns FastAPI routes and web entrypoints.
- `frontend/` owns static HTML/CSS frontend pages.
- `tests/` owns regression, reference, contract, and fixture-backed checks.
- `docs/` owns governance, decisions, plans, product specs, and durable reference notes.
- `reference-docs/` owns external WHS source material and precedent documents.
- `job_briefs/` owns source job briefs used by benchmark and reference flows.
- `prompts/` owns prompt modules and reusable prompt partials.
- `scripts/` owns operator and maintenance scripts that are not product modules.
- `db/`, `supabase/`, and `pims/migrations/` own database setup and migration assets for their respective surfaces.

Generated files and runtime outputs:

- `src/outputs/`, `output/`, and `outputs/` are runtime/generated output locations, not source folders.
- Durable benchmark expectations should live in `tests/fixtures/`, `tests/reference_jobs/`, or a named governance/spec location under `docs/`.
- Generated DOCX/HTML/JSON validation runs should not be tracked unless a test explicitly depends on them as a fixture.

Product-boundary rule:

- Do not push control-pack requirements into standalone RA or SWMS paths by moving files around. If a cleanup exposes a product-shape mismatch, capture the decision in `docs/decisions/` before changing contracts.
