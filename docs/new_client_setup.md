# PIMS — New Client Setup

Canonical new-client onboarding playbook for the PIMS (Photographic
Inspection Management System) platform operated by AuditCo WHS
Consultancy.

**Document location.** Committed in the `gatekeeper` repo at
`docs/new_client_setup.md`. The Cowork project prompt for "PIMS — New
Client Setup" is a copy of this file. **These two must stay in sync** —
if you change one, change the other in the same commit.

**Alignment.** This document is aligned to `pims/routes.py`,
`api/main.py`, `pims/pims_migration.sql`, and
`scripts/new_client.py` at commit **bb89f03** (2026-04-21, scaffold
preflight + v3 step numbers). v3 supersedes v2 (d841b44) because the
scaffold now automates Steps 1 (partly), 3, 4, 5 of v2 into a single
command. See the changelog at the bottom.

---

## How to use this document

The onboarding flow is now 9 steps (was 10), with a single scaffold
command replacing the four synchronized file edits that previously
made up roughly 80% of the manual work and 100% of the drift risk.

When running via the Cowork assistant, the assistant walks you
through one step at a time. When running manually, use the "Self-
check:" line at the end of each step.

**The one command you will run:**

```bash
python scripts/new_client.py \
    --slug abc --short ABC \
    --name "ABC Building Services Pty Ltd" \
    --ref ABC-SSA
```

Optionally with `--supabase-url` and `--supabase-service-key` to print
the bootstrap SQL in-context. See Step 3 for detail.

---

## Information to collect first

Before starting any setup steps, collect these details:

  Client full legal name          e.g. ABC Building Services Pty Ltd
  Client short name (2-4 letters) e.g. ABC
  Client slug (lowercase)         e.g. abc
  Audit reference code            e.g. ABC-SSA
  Client contact name             e.g. John Smith
  Client contact email
  Primary brand colour (hex)      e.g. #003366
  Secondary brand colour (hex)    e.g. #FFFFFF
  OneDrive folder name            e.g. _ABC

**Audit reference code constraint.** The `ObservationRequest` Pydantic
model enforces `audit_ref` match `^[A-Za-z0-9_\-]+$` with
`max_length=100`. Alphanumeric, underscore, or hyphen only. The
scaffold validates this before touching any file, so an invalid ref
aborts with a clean error — but it saves a round trip to know it
upfront.

Do not proceed until you have at minimum:
  - Client full name
  - Client short name
  - Client slug
  - Audit reference code (passes the regex above)

---

## Setup sequence (9 steps — follow in order)

### Step 1 — Create Supabase project and retrieve keys

1. Go to supabase.com and log in
2. Click New project
3. Name it: `pims-[slug]` (e.g. `pims-abc`)
4. Choose region: Sydney (ap-southeast-2)
5. Click Create new project — wait 2 minutes
6. Go to Settings → API
7. Copy and save:
   - Project URL (`https://[id].supabase.co`)
   - anon public key
   - service_role key (keep secret)

**Do not run the migration SQL yet** — that happens in Step 4 after
the scaffold prints the bootstrap payload.

**Self-check:** Do you have the project URL, anon key, and service_role
key saved?

---

### Step 2 — Railway environment variables

1. Go to railway.app → gatekeeper project → web service → Variables tab
2. Generate a token by running in terminal:

    ```bash
    python -c "import secrets; print('pims-[slug]-' + secrets.token_hex(20))"
    ```

3. Add these 4 new variables (click + New Variable for each):

    | Variable name                   | Value                         |
    |---------------------------------|-------------------------------|
    | `PIMS_[CLIENT]_TOKEN`           | the token generated above     |
    | `[CLIENT]_SUPABASE_URL`         | `https://[id].supabase.co`    |
    | `[CLIENT]_SUPABASE_ANON_KEY`    | anon public key               |
    | `[CLIENT]_SUPABASE_SERVICE_KEY` | service_role key              |

    **Naming trap:** URL / anon key / service key use the
    `[CLIENT]_SUPABASE_*` prefix, but the token uses
    `PIMS_[CLIENT]_TOKEN` — the prefix is inverted. The scaffold
    generates code that expects these exact names, so they must
    match.

4. Wait for Railway to restart
5. Check logs for: `Application startup complete`
6. No WARNING lines about missing env vars. The new client's vars are
   not yet referenced by any code (the scaffold runs in Step 3 and the
   deploy happens in Step 5), so Railway has nothing to check against
   them at this point. A warning here would be about an *existing*
   client's vars and means something unrelated — investigate before
   proceeding.

**Do not touch** any existing variables for other clients.

**Self-check:** Is Step 2 complete? All four vars added and spelled
correctly?

---

### Step 3 — Run the scaffold

This single command replaces what used to be v2's Steps 3, 4, and 5
(dashboard HTML, `routes.py` edits, `main.py` edit). The scaffold also
prints the schema bootstrap SQL you will paste in Step 4.

1. Open the VS Code terminal at the `gatekeeper/` root.
2. Run:

    ```bash
    python scripts/new_client.py \
        --slug [slug] \
        --short [CLIENT] \
        --name "[CLIENT_FULL_NAME]" \
        --ref [AUDIT_REF] \
        --supabase-url "https://[id].supabase.co" \
        --supabase-service-key "[service_role key from Step 1]"
    ```

   The `--supabase-*` flags are optional. Without them the scaffold
   prints the single-line `INSERT INTO pims_audits …` and reminds you
   to run the migration separately. With them, it prints the full
   bootstrap SQL (migration file + audit INSERT) ready to paste into
   Supabase. Recommended: pass the flags.

3. Read the scaffold's output. It will:
   - Confirm the audit_ref passed regex validation.
   - List the files modified or created:
     - `pims/routes.py` (env-var block + POST + GET)
     - `api/main.py` (dashboard route)
     - `frontend/pims_dashboard_[slug].html` (branded clone)
   - Print the SQL block you will paste in Step 4.
   - Print a **warning about export/report endpoints** — see below.

**Export/report warning.** The dashboard template references three
URLs — `/pims/report/[slug]`, `/pims/staging/[slug]/xlsx`,
`/pims/staging/[slug]/docx` — that the scaffold remaps to per-slug
variants but does **not** add backend handlers for. If the client
needs PDF reports or XLSX/DOCX staging exports, those handlers must be
added to `pims/routes.py` manually by copying from the RPD
implementations. The initial dashboard works fine without them — the
buttons will 404 until the handlers exist.

**Scaffold safety aborts** (no files touched on abort — `preflight()`
reads every source and verifies every condition before any write):
- `--ref` fails the regex → aborts with a message naming the bad
  value and the pattern.
- An env-var prefix already exists (`[CLIENT]_SUPABASE_URL` in
  `routes.py`) → aborts with `pims/routes.py already references
  [CLIENT]_SUPABASE_URL -- client exists`. Pick a different `--short`
  or remove the earlier registration manually; the scaffold does not
  provide a `--force` override — silently overwriting a registered
  client is the kind of footgun it deliberately refuses.
- A route `/pims-[slug]` already exists in `main.py` → aborts with
  `api/main.py already defines /pims-[slug] route`.
- A dashboard file `frontend/pims_dashboard_[slug].html` already
  exists → aborts with `... already exists; refusing to overwrite`.
- `frontend/pims_dashboard_rpd.html` contains a literal JWT (the
  placeholders were replaced) → aborts with `source template
  frontend/pims_dashboard_rpd.html still contains a legacy JWT
  literal`. Prevents regressing the 2026-04-21 Legacy API key
  incident.

**Line endings:** the scaffold preserves BOM + CRLF on the edited
files, so `git diff` stays small and the commit doesn't rewrite every
line. Relevant on Windows.

**Self-check:** Is Step 3 complete? Did the scaffold exit cleanly and
list three things modified/created (`pims/routes.py`, `api/main.py`,
`frontend/pims_dashboard_[slug].html`)? Did you copy the SQL it
printed?

---

### Step 4 — Apply the schema bootstrap in Supabase

1. Return to your Supabase project (from Step 1) → SQL Editor
2. Paste the SQL the scaffold printed in Step 3 → click Run
3. Go to Table Editor — confirm these four tables exist:
   - `pims_audits`
   - `pims_observations`
   - `pims_staging`
   - `sites`
4. Spot-check the schema by running this in SQL Editor — all four
   booleans must return `true`:

    ```sql
    SELECT
      EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name='pims_observations' AND column_name='staging')          AS has_staging,
      EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name='pims_observations' AND column_name='review_status')    AS has_review_status,
      EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name='pims_staging' AND column_name='site_address')          AS has_site_address,
      EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name='sites' AND column_name='project_code')                 AS has_sites;
    ```

   If any return `false`, the migration did not apply cleanly. Re-run
   the full SQL block and check for errors in the editor output.

**Self-check:** Is Step 4 complete? Did all four spot-check booleans
return true?

---

### Step 5 — Deploy to Railway

1. In the VS Code terminal:

    ```bash
    git status
    git add .
    git commit -m "feat: add [CLIENT_FULL_NAME] dashboard and routes"
    git push
    ```

   `git status` should show three changed files:
   `pims/routes.py`, `api/main.py`, and the new
   `frontend/pims_dashboard_[slug].html`.

2. Go to Railway → Deployments → watch the build log
3. Wait for `Application startup complete`
4. Confirm no WARNING lines about missing env vars. The new code
   deployed in this step reads `[CLIENT]_SUPABASE_URL`,
   `[CLIENT]_SUPABASE_ANON_KEY`, `[CLIENT]_SUPABASE_SERVICE_KEY`, and
   `PIMS_[CLIENT]_TOKEN`. Any warning naming these means a typo in
   Step 2.3 — the variable name on Railway does not match what the
   scaffold wrote into the code. Cross-check and fix on Railway
   (don't touch the code — the scaffold wrote the canonical names).

**Self-check:** Is Step 5 complete? Did Railway deploy cleanly?

---

### Step 6 — Test the dashboard

1. Open in a browser:
   `https://web-production-baafa.up.railway.app/pims-[slug]`
2. Log in with the `PIMS_DASHBOARD_PASSWORD` from Railway
3. Confirm:
   - Dashboard opens without errors
   - Client name appears correctly in the header
   - Three tabs visible: Live Audits, Staging Review, Historical
   - All KPI cards show 0 with "Live audit records only" label

If the dashboard loads but the browser console shows a Supabase auth
error, the `__SUPABASE_URL__` / `__SUPABASE_ANON__` placeholders were
not substituted — open `api/main.py` and verify the scaffold wrote
the env-var names correctly (`[CLIENT]_SUPABASE_URL`,
`[CLIENT]_SUPABASE_ANON_KEY`, not `RPD_SUPABASE_*`).

Export/report buttons (if the dashboard template has them) will 404
until you add the handlers manually — see the Step 3 warning.

**Self-check:** Is Step 6 complete? Is the dashboard working?

---

### Step 7 — Build the iPhone Snap shortcut

Open the Shortcuts app on the iPhone and create a new shortcut named:
`[CLIENT_SHORT_NAME] Snap`.

Build each action in order:

**7.1 — Format Date**
  - Action: Format Date
  - Input: Current Date
  - Format: `yyyy-MM-dd-HH-mm-ss`
  - Variable name: `Timestamp`

**7.2 — Take Photo**
  - Action: Take Photo
  - Camera: Back
  - Count: 1

**7.3 — Save to Photos**
  - Action: Save to Photo Album
  - Input: Photo
  - Album: `[CLIENT_SHORT_NAME] Audits`

**7.4 — Save File**
  - Action: Save File
  - Location: On My iPhone → `[CLIENT_SHORT_NAME] Audits`
  - Subpath: `[Timestamp].jpg`
  - Overwrite: ON
  - Input: Photo

**7.5 — Ask for Text**
  - Action: Ask for Input (or Ask for Text)
  - Prompt: Observation
  - Allow Multiple Lines: ON
  - Variable name: `DictateText`

**7.6 — Encode** (CRITICAL)
  - Action: Encode
  - Input: Photo (tap the field — confirm it says 'Photo', NOT 'File')
  - Encoding: Base64
  - Line Breaks: None
  - Variable name: `Base64 Encoded`

**7.7 — Text block**
  - Action: Text
  - Content: `https://web-production-baafa.up.railway.app/pims/observation/[slug]`

**7.8 — Get Contents of URL** (CRITICAL)
  - Action: Get Contents of URL
  - URL: Text (the variable from 7.7)
  - Method: POST
  - Headers:
    - `Content-Type`: `application/json`
    - `X-PIMS-Token`: value of `PIMS_[CLIENT]_TOKEN` from Railway
  - Request Body: JSON, with these 5 fields:
    - `audit_ref` → `[AUDIT_REF]` (must match `^[A-Za-z0-9_\-]+$`)
    - `observation_text` → `DictateText` variable
    - `observation_date` → `Timestamp` variable
    - `filename` → `Timestamp` variable + `.jpg`
    - `photo_base64` → `Base64 Encoded` variable

**7.9 — Append to File**
  - Action: Append to File
  - Content: `[Timestamp],[Timestamp].jpg,[DictateText]`
  - File: On My iPhone → `[CLIENT_SHORT_NAME] Audits` → `observations`
  - Make New Line: ON

**7.10 — Show Notification**
  - Action: Show Notification
  - Body: `Observation Saved`

Save the shortcut.

---

### Step 8 — Test the Snap shortcut

1. Run the `[CLIENT_SHORT_NAME] Snap` shortcut
2. Take a test photo of anything nearby
3. Type: `Test observation`
4. Wait for the "Observation Saved" notification
5. Go to Railway → Deployments → Logs
6. Look for `POST /pims/observation/[slug]  200 OK`
7. Open the PIMS dashboard
8. Go to Staging Review → Field Captures
9. Confirm the test observation appears with a photo

**If the observation did not appear, diagnose by status code in Railway logs:**

- **503** — Supabase URL or service key env var missing → re-check
  Step 2 naming (remember the inverted `PIMS_[CLIENT]_TOKEN` prefix).
- **401** — token mismatch → re-check `X-PIMS-Token` in shortcut
  7.8 against Railway's `PIMS_[CLIENT]_TOKEN`.
- **422** — invalid payload. Usually `audit_ref` contains disallowed
  characters or exceeds 100 chars. Must match `^[A-Za-z0-9_\-]+$`.
  Fix in shortcut 7.8.
- **No log entry** — wrong URL in shortcut 7.7.
- **Empty photo on dashboard** — Encode step using File not Photo →
  fix 7.6.
- **Photo appears but no CCVS code / conformance status after ~30 s** —
  enrichment did not run. Grep Railway logs for
  `Background enrichment complete for`; absence means `background_tasks`
  was not forwarded in the POST handler. If this happens after the
  scaffold wrote the routes, the scaffold template has regressed —
  file an issue and compare the generated POST handler against the
  one documented in the scaffold's source.

---

### Step 9 — Create the Cowork project

1. Open Cowork
2. Create a new project named: `PIMS — [CLIENT_FULL_NAME]`
3. Open the template in the gatekeeper repo: `docs/client_project_prompt_template.txt`
4. Replace all placeholders with this client's values:
    - `[CLIENT_FULL_NAME]` → full legal name
    - `[CLIENT_SHORT_NAME]` → short name
    - `[CLIENT_SLUG]` → slug
    - `[CLIENT_UPPER]` → upper-case short name
    - `[AUDIT_REF]` → audit reference
    - `[CLIENT_CONTACT_NAME]` → contact name
    - `[SUPABASE_PROJECT_ID]` → Supabase project ID
    - `[CLIENT_PRIMARY_HEX]` → primary colour
5. Paste the completed prompt into the Cowork project system prompt
6. Save the project
7. Test: ask Cowork "What is the dashboard URL for this client?" — it
   should respond with the correct URL.

**Self-check:** Is the Cowork project set up and responding correctly?

---

## Completion

When all 9 steps are confirmed, summarise for the record:

> Setup is complete for `[CLIENT_FULL_NAME]`.
>
>   Dashboard URL:  `https://web-production-baafa.up.railway.app/pims-[slug]`
>   Audit ref:      `[AUDIT_REF]`
>   Snap shortcut:  `[CLIENT_SHORT_NAME] Snap`
>   Supabase:       `https://[id].supabase.co`
>   Cowork project: `PIMS — [CLIENT_FULL_NAME]`
>
> Next steps:
>   1. Share the dashboard URL and login password with the contact
>   2. Schedule the first on-site audit
>   3. Import any historical PDF reports if needed
>   4. If the client needs PDF reports or XLSX/DOCX exports, add the
>      backend handlers — the scaffold wrote the dashboard URLs but
>      flagged the missing handlers
>   5. File the setup notes in: `C:\Users\AlanRichardson\OneDrive - AuditCo\[FOLDER]`

---

## Fallback: manual path without the scaffold

If the scaffold is broken or unavailable (e.g. you're onboarding from
a branch that predates ef73114, or the scaffold hits an unexpected
abort), fall back to the v2 manual path — see the archived v2
document or the scaffold's own source as reference. The operating
principle is unchanged: use the RPD endpoint as the copy-paste source
and match the `_handle_observation` signature exactly.

---

## Operating rules (for the Cowork assistant and human operators alike)

- Always confirm completion of each step before moving to the next.
- Never skip a step — each one depends on the previous.
- If a step fails, diagnose before moving on.
- Never commit or push to GitHub without Alan's confirmation.
- Never touch existing client variables in Railway.
- If a value is unclear, use the RPD example as reference.
- If asked to "skip" a step, warn of the risk first.
- State the current step clearly at all times.
- **If this document, the scaffold, and the code in `pims/routes.py` /
  `api/main.py` disagree, the code wins, then the scaffold, then this
  document.** File the correction in the same commit as any fix.

---

## Changelog

**v3.1 — 2026-04-21, aligned to commit bb89f03 (cross-check fixes):**

- Step 3 abort messages now quote the scaffold's actual strings
  verbatim; removed the fictional `--force` flag reference.
- Fixed off-by-one: scaffold lists three items modified/created, not
  four (Step 3 self-check and Step 5 `git status` count).
- Scaffold's final "still manual" banner now uses v3 step numbers, so
  terminal output matches this document.
- Preflight: the scaffold now reads every source and verifies every
  abort condition before any write, so "no files touched on abort" is
  actually true even when the conflict is in `api/main.py` or the
  template.

**v3 — 2026-04-21, aligned to commit ef73114 (scaffold shipped):**

- **Shape change:** 10 steps → 9 steps. Old Steps 3, 4, 5 (dashboard
  clone, `routes.py` edits, `main.py` edit) collapsed into new Step 3
  (`python scripts/new_client.py …`). Old Step 1 split: project
  creation + key retrieval stays as new Step 1; migration + audit
  INSERT becomes new Step 4.
- **New Step 3 — Run the scaffold:** documents the canonical command,
  required and optional flags, scaffold output, safety aborts
  (invalid `--ref`, double-registration, JWT-contaminated source
  template), and the export-handler warning (dashboard references
  three per-slug export URLs the scaffold does not create backend
  handlers for).
- **Diagnostic added:** Step 8's enrichment-missing path now notes
  that if it happens post-scaffold, the scaffold template itself
  has regressed and should be treated as a code-level bug.
- **Operating rules updated:** precedence when docs, scaffold, and
  code disagree — code > scaffold > doc.
- **Fallback path documented:** the v2 manual path remains valid for
  pre-ef73114 branches or scaffold outages.

**v2 → v3 net effect on operator time:** the synchronized-edit block
that was the main source of drift is gone. Setup time for a new
client drops from ~20 min of careful manual edits to ~30 sec of
scaffold execution, without changing the end result on disk.

**Going-forward drift policy (established in d841b44, still in force):**

- `pims/pims_migration.sql` and `supabase/migrations/` = source of
  truth for schema.
- All schema changes land in a committed file first, then
  `apply_migration`.
- Hotfix-via-MCP allowed only if backported to a committed file the
  same calendar day.
- When route signatures change, the scaffold's templates must be
  updated in the same PR. A CI check diffing scaffold output against
  live RPD's routes would make drift unmissable — worth considering
  as a follow-up.
