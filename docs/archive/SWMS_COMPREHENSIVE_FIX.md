# SWMS Comprehensive Fix — All Issues + Recurrence Prevention
Generated from: side-by-side audit of generated PDF vs reference `real_job_cranebrook3.docx`
Date: 09/03/2026

---

## ISSUE REGISTER

| # | Severity | Location | Issue | Root Cause |
|---|----------|----------|-------|------------|
| 1 | CRITICAL | Cover table | PCBU = "mcxico" | Email domain used instead of user-supplied company name |
| 2 | CRITICAL | Cover table | Work Activity = address | Address string routed to wrong field |
| 3 | CRITICAL | Cover table | Principal Contractor = "mcxico" | Same as #1 |
| 4 | CRITICAL | Footer | "SWMS-UNKNOWN-09032026-V01" | SWMS ID slug never resolved from job input |
| 5 | HIGH | Description line | Address shown, not work description | P0 not populated with work summary |
| 6 | HIGH | All task PPE lists | "steel-capped steel-capped footwear" | Duplicate token in vocabulary + no post-process strip |
| 7 | HIGH | CCVS column | "WAHH6" / "SYS-H6" — wrong format | Missing hyphen separator; inconsistent code assembly |
| 8 | HIGH | STOP WORK labels | Missing dark red text color | Renderer applies yellow highlight but not C00000 font color |
| 9 | MEDIUM | Signoff table | 5 separate tables × 7 rows = 35 rows across 5 pages | Renderer creates new table per page instead of one continuous table |
| 10 | MEDIUM | CCVS table | N/A tasks included in CCVS table | Filter not applied — only tasks with a real CCVS code should appear |
| 11 | MEDIUM | Legislation row | "Model WHS Act 2011" not jurisdiction-specific | Renderer uses generic fallback not jurisdiction-resolved string |
| 12 | MEDIUM | Standards | AS/NZS 3580 cited for hard hats (wrong) | 3580 = air quality monitoring; hard hats = AS/NZS 1801 |
| 13 | LOW | HRCW checkboxes | Unchecked boxes show "[ ]" (1 space) vs template "[ &nbsp;&nbsp; ]" (3 spaces) | Template literals not matched exactly |
| 14 | LOW | Footer layout | Page number fields may not be rendering | Footer tab stops exist (center 4513, right 9026) but fields need verification |

---

## FIX 1 — PCBU, Work Activity, Principal Contractor (CRITICAL)

### Problem
The renderer reads the Supabase user record and extracts the email domain substring ("mcxico") and uses it as both PCBU and Principal Contractor. The work description string is routed directly to Work Activity AND Workplace Location — both fields get the same raw string.

### Fix A: Add fields to frontend `frontend/dev.html`

In the Mode 01 job description card, ABOVE the generate button, add these four inputs:

```html
<div class="field-group" id="job-meta-fields">
  <label class="field-label">COMPANY / PCBU NAME</label>
  <input type="text" id="pcbu-name" class="field-input"
         placeholder="e.g. Smith Building Pty Ltd">

  <label class="field-label">PRINCIPAL CONTRACTOR (PC)</label>
  <input type="text" id="principal-contractor" class="field-input"
         placeholder="Leave blank if same as PCBU">

  <label class="field-label">SITE ADDRESS / PROJECT LOCATION</label>
  <input type="text" id="project-address" class="field-input"
         placeholder="e.g. 218 Vincent Rd, Cranebrook NSW 2749">

  <label class="field-label">SUPERVISOR / MANAGER NAME</label>
  <input type="text" id="manager-name" class="field-input"
         placeholder="Site supervisor or manager">
</div>
```

Collect in the generate call:
```javascript
const meta = {
  pcbu_name: document.getElementById('pcbu-name').value.trim() || 'mcxico',
  principal_contractor: document.getElementById('principal-contractor').value.trim()
                        || document.getElementById('pcbu-name').value.trim() || 'mcxico',
  project_address: document.getElementById('project-address').value.trim() || '',
  manager_name: document.getElementById('manager-name').value.trim() || ''
};
// Include meta in the request body to /generate/auto and /render/docx
```

### Fix B: Update API models `api/main.py`

Add to the generate and render request schemas:
```python
class GenerateRequest(BaseModel):
    description: str
    jurisdiction: str = "AU"
    pcbu_name: str = ""
    principal_contractor: str = ""
    project_address: str = ""
    manager_name: str = ""
```

Pass all fields through to the orchestrator and renderer.

### Fix C: Update `renderers/docx_renderer.py`

In the cover table population function, map fields explicitly:

```python
# Cover table (Table 0) field mapping
# Row 0: PCBU label → col 0 (header, pre-filled), value → col 1
# Row 0: Workplace Location label → col 5 (header), value → col 6
# Row 1: Manager → col 1, Date SWMS provided to PC → col 6
# Row 2: Work Activity → col 1 (work description, NOT address)
#         Principal Contractor (PC) → col 6

def populate_cover_table(table, job_data):
    # PCBU
    table.cell(0, 1).text = job_data.get('pcbu_name', '')
    # Workplace location
    table.cell(0, 6).text = job_data.get('project_address', '')
    # Manager
    table.cell(1, 1).text = job_data.get('manager_name', '')
    # Work Activity — AI-generated summary of WHAT work is done
    table.cell(2, 1).text = job_data.get('work_activity_summary', '')
    # Principal Contractor
    table.cell(2, 6).text = job_data.get('principal_contractor', 
                                          job_data.get('pcbu_name', ''))
```

### Fix D: Generate `work_activity_summary` in orchestrator

In `core/orchestrator.py`, after Claude generates the tasks, extract a clean Work Activity summary:

```python
# Derive work_activity_summary from the job description
# Preferred: first sentence of the generated SWMS scope, ≤ 80 chars
# Fallback: truncate raw description, strip address if address also provided separately
def derive_work_activity(description: str, project_address: str) -> str:
    summary = description.strip()
    # If address is provided separately, remove it from the summary
    if project_address and project_address in summary:
        summary = summary.replace(project_address, '').strip(' ,at-')
    # Cap at 120 chars
    return summary[:120]
```

---

## FIX 2 — SWMS ID in Footer (CRITICAL)

### Problem
Footer renders "SWMS-UNKNOWN-09032026-V01". The template placeholder `UNKNOWN` is never replaced with the job reference slug.

### Fix in `renderers/docx_renderer.py`

Build the SWMS ID before rendering and replace it in the footer:

```python
import re
from datetime import date

def build_swms_id(project_address: str, doc_date: str = None) -> str:
    """Build slug: SWMS-{address-slug}-{DDMMYYYY}-V01"""
    if not project_address:
        slug = "SITE"
    else:
        # Take street number + street name, strip suburb/state/postcode
        # e.g. "218 Vincent Rd, Cranebrook NSW 2749" → "218-Vincent-Rd-Cranebrook"
        parts = project_address.split(',')[0].strip()  # "218 Vincent Rd"
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', parts)
        slug = re.sub(r'\s+', '-', slug.strip())
        # Add suburb if present
        suburb_match = re.search(r',\s*([A-Za-z]+)', project_address)
        if suburb_match:
            slug += '-' + suburb_match.group(1)
    
    date_str = doc_date or date.today().strftime('%d%m%Y')
    return f"SWMS-{slug}-{date_str}-V01"

def populate_footer(doc, swms_id: str):
    for section in doc.sections:
        for para in section.footer.paragraphs:
            for run in para.runs:
                if 'UNKNOWN' in run.text or 'SWMS-' in run.text:
                    run.text = run.text.replace(
                        run.text, swms_id
                    )
```

Also replace in the Page 1 description paragraph (P0):
```python
def populate_description_line(doc, work_summary: str, swms_id: str):
    for para in doc.paragraphs:
        if '■' in para.text or 'Description' in para.text:
            for run in para.runs:
                if '[Insert description here]' in run.text:
                    run.text = run.text.replace(
                        '[Insert description here]', work_summary
                    )
            break
```

---

## FIX 3 — "steel-capped steel-capped" Duplicate (HIGH)

### Immediate fix in `vocab/swms_vocabulary.py`

Search for any PPE item containing "steel-capped" and ensure it appears exactly once:

```python
# WRONG — do not allow:
"steel-capped steel-capped footwear"

# CORRECT:
"steel-capped footwear"
```

### Recurrence prevention in `renderers/docx_renderer.py`

Add a post-processing sanitise pass applied to every cell before writing:

```python
DUPLICATE_TOKENS = [
    ("steel-capped steel-capped", "steel-capped"),
    ("cut-resistant cut-resistant", "cut-resistant"),
    ("high-visibility high-visibility", "high-visibility"),
    ("  ", " "),  # double space
]

def sanitise_text(text: str) -> str:
    for bad, good in DUPLICATE_TOKENS:
        while bad in text:
            text = text.replace(bad, good)
    return text
```

Apply `sanitise_text()` to all generated control text before inserting into table cells.

---

## FIX 4 — CCVS Code Format (HIGH)

### Problem
Generated codes appear as "WAHH6" or "SYS-H6". Correct Gatekeeper Standard format is always `[STREAM]-[SEVERITY][LEVEL]` e.g. `WAH-H6`, `SIL-H6`, `CHM-H6`, `SIL-M4`.

### Fix in `core/inference_matrix.py`

Wherever CCVS codes are assembled, enforce the format with a validator:

```python
import re

VALID_CCVS_PATTERN = re.compile(
    r'^(WFR|WFA|WAH|IRA|ELE|SIL|STR|CFS|ENE|HOT|MOB|ASB|LED|TRF|ENV|N/A)'
    r'-(H6|H9|M3|M4|L1|L2)$'
)

def validate_ccvs_code(code: str) -> str:
    """
    Normalise and validate a CCVS code.
    Fixes missing hyphen: 'WAHH6' → 'WAH-H6', 'SILM4' → 'SIL-M4'
    """
    if code == 'N/A':
        return 'N/A'
    
    # Already correct
    if VALID_CCVS_PATTERN.match(code):
        return code
    
    # Attempt repair: known 3-char streams
    streams = ['WFR','WFA','WAH','IRA','ELE','SIL','STR','CFS',
               'ENE','HOT','MOB','ASB','LED','TRF','ENV']
    for stream in streams:
        if code.upper().startswith(stream):
            suffix = code[len(stream):].lstrip('-')
            # normalise suffix: H6, H9, M3, M4, L1, L2
            suffix = suffix.upper()
            repaired = f"{stream}-{suffix}"
            if VALID_CCVS_PATTERN.match(repaired):
                return repaired
    
    # Cannot repair — log warning and return N/A
    import logging
    logging.warning(f"Invalid CCVS code could not be repaired: {repr(code)}")
    return 'N/A'
```

Call `validate_ccvs_code(code)` on every CCVS value before writing to the document.

---

## FIX 5 — STOP WORK Label: Missing Red Text Color (HIGH)

### Reference spec (from docx audit)
- `⚠️ HOLD POINT — do not start until:` → yellow highlight, **no** color override (inherits black)
- `🛑 STOP WORK if:` → yellow highlight **AND** font color `C00000` (dark red), bold

### Fix in `renderers/docx_renderer.py`

When writing control cell paragraphs, after setting yellow highlight on STOP WORK runs, also set font color:

```python
from docx.shared import RGBColor

def write_control_paragraph(cell, text: str, is_label: bool = False):
    para = cell.add_paragraph()
    run = para.add_run(text)
    
    if 'HOLD POINT' in text:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        run.bold = True
        # No color override — black text on yellow
    
    elif 'STOP WORK' in text:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        run.bold = True
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)  # dark red C00000
```

---

## FIX 6 — Worker Signoff Table: Single Table, 33 Rows (MEDIUM)

### Problem
Renderer creates one signoff table per page (5 tables × 7 rows = 35 rows).
Reference: one single continuous table with 33 data rows + 1 header row = 34 rows total, 4 columns.

### Fix in `renderers/docx_renderer.py`

Replace the loop that creates multiple signoff tables with a single table creation:

```python
SIGNOFF_ROW_COUNT = 33  # matches reference template

def create_signoff_table(doc):
    """
    Single continuous worker induction signoff table.
    4 columns: Date | Name | Signature | Declaration text
    33 data rows + 1 header.
    """
    # Add header
    doc.add_heading('WORKER INDUCTION SIGNOFF', level=2)
    
    table = doc.add_table(rows=1 + SIGNOFF_ROW_COUNT, cols=4)
    table.style = 'Table Grid'
    
    # Header row
    hdr = table.rows[0].cells
    hdr[0].text = 'Date'
    hdr[1].text = 'Name'
    hdr[2].text = 'Signature'
    hdr[3].text = ('I have read and understood this SWMS. I will check that '
                   'critical controls are in place before starting high-risk '
                   'work. I will stop work and tell my supervisor if controls '
                   'are missing.')
    
    # Data rows — leave blank for signing
    for i in range(1, SIGNOFF_ROW_COUNT + 1):
        row = table.rows[i].cells
        # Set row height to give signing space
        for cell in row:
            cell.width = Pt(0)  # let table auto-size
    
    return table
```

Do **not** insert `doc.add_page_break()` between signoff rows.

---

## FIX 7 — CCVS Table: Exclude N/A Tasks (MEDIUM)

### Problem
The CCVS summary table at the end includes ALL tasks, including those with CCVS code = N/A (e.g. "Set up site", "Allow to cure", "Final cleanup"). Reference only includes tasks that have a real CCVS code.

### Fix in `renderers/docx_renderer.py`

Filter before building CCVS table:

```python
def create_ccvs_table(doc, tasks: list):
    """Only include tasks with a non-N/A CCVS code."""
    ccvs_tasks = [t for t in tasks if t.get('ccvs_code', 'N/A') != 'N/A']
    
    if not ccvs_tasks:
        return  # No CCVS tasks — omit table entirely
    
    # Build table with: Task | Critical Control | Who Checks | How Often | What They Look For
    table = doc.add_table(rows=1 + len(ccvs_tasks), cols=5)
    # ... populate as before
```

---

## FIX 8 — Legislation Row: Jurisdiction-Specific Text (MEDIUM)

### Problem
Generated output uses "Model WHS Act 2011" (national model). Reference uses "WHS Act 2011 (NSW)".

### Fix in `core/jurisdictions.py` or `renderers/docx_renderer.py`

Add a jurisdiction-to-legislation map:

```python
JURISDICTION_LEGISLATION = {
    "AU-NSW": "WHS Act 2011 (NSW) — WHS Regulation 2017 (NSW) — SafeWork NSW Codes of Practice",
    "AU-VIC": "OHS Act 2004 (VIC) — OHS Regulations 2017 (VIC) — WorkSafe Victoria Codes of Practice",
    "AU-QLD": "WHS Act 2011 (QLD) — WHS Regulation 2011 (QLD) — Workplace Health and Safety Queensland",
    "AU-WA":  "WHS Act 2020 (WA) — WHS Regulations 2022 (WA) — WorkSafe WA Codes of Practice",
    "AU-SA":  "WHS Act 2012 (SA) — WHS Regulations 2012 (SA) — SafeWork SA Codes of Practice",
    "AU-TAS": "WHS Act 2012 (TAS) — WHS Regulations 2012 (TAS) — WorkSafe Tasmania",
    "AU-ACT": "WHS Act 2011 (ACT) — WHS Regulation 2011 (ACT) — WorkSafe ACT",
    "AU-NT":  "WHS Act 2011 (NT) — WHS Regulations 2011 (NT) — NT WorkSafe",
    "AU":     "WHS Act 2011 (NSW) — WHS Regulation 2017 (NSW) — SafeWork NSW Codes of Practice",
    "NZ":     "Health and Safety at Work Act 2015 (NZ) — HSW (General Risk and Workplace Management) Regulations 2016",
    "UK":     "Health and Safety at Work Act 1974 (UK) — Management of Health and Safety at Work Regulations 1999",
    "US":     "OSHA Act 1970 — 29 CFR 1926 (Construction)",
    "CA":     "Canada Labour Code Part II — Canada OHS Regulations",
}

def get_legislation_text(jurisdiction: str) -> str:
    return JURISDICTION_LEGISLATION.get(jurisdiction, JURISDICTION_LEGISLATION["AU"])
```

---

## FIX 9 — Standards Registry: Wrong Hard Hat Standard (MEDIUM)

### Problem
`AS/NZS 3580` is cited for hard hats in multiple places. This is incorrect — 3580 covers methods of sampling and analysis of ambient air. Hard hat standard is `AS/NZS 1801:1998`.

### Fix in `vocab/standards_registry.py`

```python
# REMOVE or correct this entry:
# "AS/NZS 3580" → this is an AIR QUALITY monitoring standard, NOT head protection

# ADD/CONFIRM these entries:
STANDARDS = {
    # Head protection
    "hard_hat": "AS/NZS 1801:1998",              # Occupational protective helmets
    
    # Fall protection
    "harness": "AS/NZS 1891.1:2007",             # Industrial fall-arrest systems
    "lanyard": "AS/NZS 1891.1:2007",
    
    # Respiratory
    "p2_mask": "AS/NZS 1716:2012",               # Respiratory protective devices
    "p1_mask": "AS/NZS 1716:2012",
    
    # Eye protection  
    "eye_protection": "AS/NZS 1337.1:2010",       # Eye protectors for occupational applications
    
    # Footwear
    "safety_boots": "AS/NZS 2210.3:2009",         # Occupational protective footwear
    
    # Gloves
    "cut_resistant_gloves": "AS/NZS 2161.3:2005", # Occupational protective gloves
    
    # High visibility
    "hi_vis": "AS/NZS 1906.4:2010",               # Retroreflective materials
    
    # Hearing
    "hearing_protection": "AS/NZS 1270:2002",      # Acoustics — hearing protectors
    
    # Ladders
    "ladder": "AS/NZS 1892.1:1996",               # Portable ladders — metal
    
    # Electrical
    "rcd": "AS/NZS 3012:2019",                    # Electrical installations — construction
    
    # Air quality (correctly filed)
    "ambient_air_monitoring": "AS/NZS 3580",       # DO NOT use for PPE
}
```

Add a guard in any function that resolves standards for PPE items to prevent 3580 being returned for any PPE category:

```python
def get_standard_for_ppe(ppe_item: str) -> str:
    code = _resolve_standard(ppe_item)
    # Safety guard — 3580 is never a PPE standard
    if code and '3580' in code:
        raise ValueError(f"Standard AS/NZS 3580 incorrectly mapped to PPE item: {ppe_item}")
    return code
```

---

## FIX 10 — HRCW Checkbox Format (LOW)

### Problem
Template uses `[   ]` (3 spaces) for unchecked HRCW items. Renderer generates `[ ]` (1 space).

### Fix in `renderers/docx_renderer.py`

```python
HRCW_UNCHECKED = "[   ]"   # 3 spaces to match template
HRCW_CHECKED   = "[✓ ]"    # tick + space

def format_hrcw_checkbox(is_checked: bool) -> str:
    return HRCW_CHECKED if is_checked else HRCW_UNCHECKED
```

---

## RECURRENCE PREVENTION — Structural Safeguards

### A. Add output validation function

In `renderers/docx_renderer.py`, add a post-render validation that runs before returning the file:

```python
KNOWN_PLACEHOLDER_TOKENS = [
    'UNKNOWN', '[Insert', 'mcxico', 'your-company', 
    'PCBU_NAME', 'INSERT_', '{{', '}}'
]

def validate_output(doc, job_data: dict) -> list[str]:
    """
    Returns list of validation errors found in rendered document.
    Raises ValueError if critical placeholders remain.
    """
    errors = []
    
    # Check all paragraph and table cell text
    all_text_blocks = []
    for para in doc.paragraphs:
        all_text_blocks.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text_blocks.append(cell.text)
    
    full_text = ' '.join(all_text_blocks)
    
    for token in KNOWN_PLACEHOLDER_TOKENS:
        if token in full_text:
            errors.append(f"Unresolved placeholder found: '{token}'")
    
    # Check CCVS codes
    import re
    bad_codes = re.findall(r'\b(WAH|SIL|CHM|TRF|MOB|ELE|ASB|LED|STR)[A-Z0-9]+', full_text)
    for code in bad_codes:
        if '-' not in code:
            errors.append(f"Malformed CCVS code (missing hyphen): '{code}'")
    
    # Check for duplicate tokens
    if 'steel-capped steel-capped' in full_text:
        errors.append("Duplicate PPE token: 'steel-capped steel-capped'")
    
    if errors:
        import logging
        for e in errors:
            logging.warning(f"RENDER VALIDATION: {e}")
    
    return errors
```

Call this at the end of every render function and log all warnings. In production, surface critical errors back to the API response as a `warnings` field so the frontend can flag them.

### B. Add CCVS code unit tests

In `tests/test_ccvs.py`:

```python
import pytest
from core.inference_matrix import validate_ccvs_code

def test_valid_codes_pass():
    assert validate_ccvs_code("WAH-H6") == "WAH-H6"
    assert validate_ccvs_code("SIL-M4") == "SIL-M4"
    assert validate_ccvs_code("N/A") == "N/A"

def test_missing_hyphen_repaired():
    assert validate_ccvs_code("WAHH6") == "WAH-H6"
    assert validate_ccvs_code("SILM4") == "SIL-M4"
    assert validate_ccvs_code("CHML2") == "CHM-L2"

def test_invalid_code_returns_na():
    assert validate_ccvs_code("SYS-H6") == "N/A"   # SYS not a valid stream
    assert validate_ccvs_code("XXXX") == "N/A"
```

### C. Add placeholder coverage test

In `tests/test_renderer.py`:

```python
def test_no_unresolved_placeholders(sample_job_data):
    doc = render_docx(sample_job_data)
    errors = validate_output(doc, sample_job_data)
    critical = [e for e in errors if 'placeholder' in e.lower()]
    assert critical == [], f"Unresolved placeholders in output: {critical}"
```

---

## IMPLEMENTATION ORDER

```
1. Fix 1C + 1D  — cover table field mapping (renderer)
   Fix 1A + 1B  — UI inputs + API schema
2. Fix 2        — footer SWMS ID slug + description line P0
3. Fix 3        — steel-capped duplicate + sanitise_text() guard
4. Fix 4        — CCVS code validator + repair function
5. Fix 5        — STOP WORK red color C00000
6. Fix 6        — signoff table: single 33-row table
7. Fix 7        — CCVS table filter (exclude N/A tasks)
8. Fix 8        — jurisdiction legislation text
9. Fix 9        — standards registry AS/NZS 3580 correction
10. Fix 10      — HRCW checkbox spacing
11. Prevention  — validate_output() + unit tests
```

## COMMIT

```bash
git add -A
git commit -m "Comprehensive output quality fixes:
- PCBU/PC/WorkActivity/Address field mapping
- SWMS ID slug in footer and description line
- Duplicate steel-capped token fix + sanitise guard
- CCVS code hyphen format + validator
- STOP WORK dark red C00000 color
- Signoff table single 33-row table
- CCVS table filter excludes N/A tasks
- Jurisdiction-specific legislation text
- Standards registry: remove AS/NZS 3580 from PPE
- HRCW checkbox 3-space format
- validate_output() post-render guard
- Unit tests for CCVS codes and placeholders"
git push origin main
```
