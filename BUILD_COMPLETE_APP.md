# COMPLETE BUILD — app.html + Dashboard + All Three Modes
# Simple SWMS Platform
# Replaces dev.html entirely

---

## SUMMARY OF WHAT TO BUILD

1. `frontend/dashboard.html` — post-login landing page, SWMS or RA selector
2. `frontend/app.html` — full SWMS tool replacing dev.html
3. `api/upload_routes.py` — Mode 02/03 upload endpoints (file + photo)
4. `core/document_extractor.py` — PDF/DOCX/TXT/image extraction
5. `core/swms_analyser.py` — gap analysis + scope extraction prompts
6. Update `api/main.py` — register upload router, add dashboard + app routes
7. `requirements.txt` — add pdfplumber

---

## PAGE FLOW

```
/app  →  dashboard.html   (auth check → SWMS or RA selector)
          └── SWMS  →  /swms  →  app.html  (three mode tabs)
          └── RA    →  /ra    →  TBD (separate spec)
```

---

## FILE 1 — `frontend/dashboard.html`

Full page. Black background, Simple SWMS branding.
Auth check on load — redirect to /app login if no token.

Layout:
- Header: Simple SWMS logo + user email top right + logout button
- Centre: "What would you like to create?"
- Two large cards side by side:

  CARD 1 — SWMS
  Icon: 📋
  Label: Safe Work Method Statement
  Subtext: Generate a compliant SWMS for any construction task
  Button: CREATE SWMS → navigates to /swms

  CARD 2 — Risk Assessment
  Icon: ⚠️
  Label: Risk Assessment
  Subtext: Standalone risk assessment document
  Button: CREATE RA → navigates to /ra (show "coming soon" toast for now)

Styling: match existing Simple SWMS brand
- Background: #000000
- Cards: #111111 border #222222
- Button accent: #f59e0b (amber — existing brand)
- Font: Outfit (body) Fraunces (display headings)

```html
<!-- dashboard.html skeleton — Claude Code fills in full implementation -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Simple SWMS — Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@700&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
</head>
<body>
  <!-- Auth check script runs first — redirects to /app if no token -->
  <!-- Header with logo + user email + logout -->
  <!-- Two selector cards: SWMS and RA -->
  <!-- RA card shows "Coming Soon" toast on click for now -->
</body>
</html>
```

---

## FILE 2 — `frontend/app.html`

### Auth + routing
- Check token on load — redirect to /app if missing or expired
- Page served at route /swms

### Header
- Same as dashboard header: logo + user email + logout
- Back link: ← Dashboard (returns to /app)

### Mode tabs
Three tabs across the top of the form area:

```
[ Manual ]  [ Upgrade SWMS ]  [ Scope of Works or Specification ]
```

- Default active tab: Manual
- Tab switch shows/hides upload section only
- Direct Fields form is ALWAYS visible regardless of tab

### Upload section (Mode 02 and 03 only — hidden in Manual)

Single button: **"UPLOAD OR TAKE PHOTO"**

On click — show two options as a small popup/sheet:
  - 📁 Upload file  (accepts .pdf, .docx, .doc, .txt)
  - 📷 Take photo / Upload image  (accepts .jpg, .jpeg, .png, .heic)

Both options allow MULTIPLE files/photos.

For Mode 02 label: "Upload your existing SWMS — we'll identify gaps and upgrade it"
For Mode 03 label: "Upload your Scope of Works or Specification document"

After selection:
- Show file chips (filename or "Photo 1", "Photo 2" etc.) with × to remove
- Show "ANALYSE" button
- On analyse: send files to appropriate endpoint, pre-fill Direct Fields with result
- Show status: "Analysing... / X gaps found / Scope extracted"
- If Mode 02: show collapsible gap list above Direct Fields

### Direct Fields form (ALWAYS visible, shared across all modes)

All fields optional. Placeholder text in italic where shown.
Order matches document spec exactly:

```
YOUR COMPANY OR BUSINESS NAME
[text input]
placeholder: "e.g. Smith Building Pty Ltd"
maps to: PCBU

YOUR NAME
[text input]
placeholder: "Your full name"
maps to: Manager

JOB SITE ADDRESS
[text input]
placeholder: "e.g. 218 Vincent Rd, Cranebrook NSW 2749"
maps to: Workplace Location + project_address

JOB DESCRIPTION
[textarea — 4 rows]
placeholder: "Describe the work being carried out"
maps to: Description (P0) + feeds Work Activity AI generation

PRINCIPAL CONTRACTOR
[text input]
helper text shown below in grey: "Who is the builder you are sending this to?"
maps to: PC

PERSON RESPONSIBLE FOR COMPLIANCE
[text input]
helper text: "Name of supervisor or team leader"
maps to: Supervisor / Person responsible for ensuring compliance

PERSON RESPONSIBLE FOR REVIEWING
[text input]
helper text: "Name of project manager"
maps to: Reviewer / Person responsible for reviewing SWMS

DATE
[date picker — defaults to today's date]
maps to: Date SWMS provided to PC + Date received + Review date

HOW WILL THE SWMS BE REVIEWED?
[multi-select checkbox list]
Items (each is a checkbox):
  □ Before any change is made to the way the construction work is carried out
  □ Before a new system of work is introduced
  □ Before the place where the work is being carried out is changed
  □ If a new hazard is identified
  □ If new information about a hazard becomes available
  □ If a notifiable incident occurs in relation to construction work
  □ If a control measure does not control the risk
  □ A request for a review is received from a health and safety representative
  □ When legislation or codes of practice change, new work methods, products, or equipment are introduced
  □ Minimum 12-monthly review

Default behaviour: if user selects NOTHING and hits generate,
auto-select these three:
  ✓ If a control measure does not control the risk
  ✓ When legislation or codes of practice change, new work methods, products, or equipment are introduced
  ✓ Minimum 12-monthly review

Output format — always leads with:
"This SWMS will be reviewed: [selected items joined with em dash —]"
```

### Jurisdiction selector
Small dropdown below the form (existing — keep as is):
AU / NZ / UK / US / CA

### Format selector
Word / PDF / Both (existing — keep as is)

### Generate button
"GENERATE SWMS" — full width, amber

### Status panel
Below generate button — shows progress, errors, download links (existing pattern)

---

## FILE 3 — `core/document_extractor.py`

```python
"""
document_extractor.py
Extracts clean text from uploaded files and photos.
Supports: PDF, DOCX, DOC, TXT, JPG, PNG, HEIC
"""

import io
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from uploaded file or image.
    Images use Claude Vision API.
    Documents use pdfplumber / python-docx.
    """
    ext = Path(filename).suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        return _extract_image(file_bytes, ext, filename)
    elif ext == '.pdf':
        return _extract_pdf(file_bytes)
    elif ext in ('.docx', '.doc'):
        return _extract_docx(file_bytes)
    elif ext == '.txt':
        return file_bytes.decode('utf-8', errors='replace')
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Upload PDF, Word (.docx), text file, or photo (JPG/PNG)."
        )


def _extract_image(file_bytes: bytes, ext: str, filename: str) -> str:
    """
    Extract text from photo using Claude Vision API.
    Used for photos of printed documents, handwritten scopes, old SWMS.
    """
    import anthropic

    # Map extension to media type
    media_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.heic': 'image/jpeg',  # convert HEIC to JPEG before sending if needed
    }
    media_type = media_type_map.get(ext, 'image/jpeg')

    # Encode to base64
    image_data = base64.standard_b64encode(file_bytes).decode('utf-8')

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "This is a photo of a construction document — "
                            "either a Scope of Works, Specification, or Safe Work "
                            "Method Statement (SWMS). "
                            "Extract ALL text visible in this image exactly as written. "
                            "Preserve headings, lists, and table content. "
                            "If the image is blurry or partially obscured, extract "
                            "what is legible and note '[illegible]' where text cannot "
                            "be read. Return only the extracted text, no commentary."
                        )
                    }
                ]
            }
        ]
    )

    extracted = response.content[0].text.strip()
    if not extracted:
        raise ValueError(
            f"No text could be extracted from {filename}. "
            "Check the photo is clear and well-lit."
        )
    logger.info(f"Vision extraction: {len(extracted)} chars from {filename}")
    return extracted


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        result = '\n'.join(text_parts).strip()
        if not result:
            raise ValueError(
                "No text could be extracted from this PDF. "
                "The file may be scanned — try taking a photo instead."
            )
        return result
    except ImportError:
        raise RuntimeError("pdfplumber not installed. Add to requirements.txt.")
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Could not read PDF: {str(e)}")


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                )
                if row_text:
                    parts.append(row_text)
        result = '\n'.join(parts).strip()
        if not result:
            raise ValueError("Document appears to be empty.")
        return result
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        raise ValueError(f"Could not read Word document: {str(e)}")


def extract_multiple(files: list[tuple[bytes, str]]) -> str:
    """
    Extract and combine text from multiple files/photos.
    Used when user uploads multiple photos of a multi-page document.
    files: list of (file_bytes, filename) tuples
    """
    parts = []
    for i, (file_bytes, filename) in enumerate(files, 1):
        try:
            text = extract_text(file_bytes, filename)
            parts.append(f"--- Page/File {i}: {filename} ---\n{text}")
        except Exception as e:
            parts.append(f"--- Page/File {i}: {filename} --- [Error: {str(e)}]")
    return '\n\n'.join(parts)


def truncate_for_prompt(text: str, max_chars: int = 12000) -> str:
    """Truncate text to fit prompt limits, keeping start and end."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + "\n\n[... document truncated for processing ...]\n\n"
        + text[-half:]
    )
```

---

## FILE 4 — `core/swms_analyser.py`

```python
"""
swms_analyser.py
Mode 02: Analyse existing SWMS against Gatekeeper Standard.
Mode 03: Extract scope from Scope of Works / Specification.
"""

import json
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)
client = AsyncAnthropic()


def _parse_json_response(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith('```'):
        parts = text.split('```')
        text = parts[1] if len(parts) > 1 else text
        if text.startswith('json'):
            text = text[4:]
    return json.loads(text.strip())


ANALYSE_PROMPT = """You are a WHS Safety adviser reviewing a Safe Work Method Statement 
against the Gatekeeper Standard for Australian construction.

UPLOADED SWMS TEXT:
{swms_text}

Analyse this SWMS and return a JSON object with exactly this structure:

{{
  "pcbu_name": "company name found in document, or empty string",
  "project_address": "site address found in document, or empty string",
  "manager_name": "manager or supervisor name found, or empty string",
  "principal_contractor": "PC name found, or empty string",
  "jurisdiction": "AU",
  "work_activity_summary": "one sentence — what work is being done",
  "description": "detailed rewritten job description capturing all tasks, 
                  trade types, location context, HRCW categories, materials 
                  and equipment — written to generate a full new SWMS from",
  "gaps": [
    "each string is one compliance gap — missing controls, missing permits,
     missing PPE items, missing HRCW tick, inadequate risk rating, missing 
     hold point, missing STOP WORK trigger, missing CCVS code, etc."
  ],
  "hrcw_categories": ["list of applicable HRCW categories"],
  "existing_tasks": ["list of task names found in the uploaded SWMS"]
}}

Be thorough on gaps — this is a compliance tool.
Return only valid JSON, no preamble.
"""


SCOPE_EXTRACT_PROMPT = """You are a WHS Safety adviser reading a Scope of Works or 
Specification document for an Australian construction project.

DOCUMENT TEXT:
{doc_text}

Extract the work scope and return a JSON object with exactly this structure:

{{
  "pcbu_name": "company name if found, else empty string",
  "project_address": "site address if found, else empty string",
  "manager_name": "project manager or supervisor if found, else empty string",
  "principal_contractor": "principal contractor if found, else empty string",
  "jurisdiction": "AU",
  "work_activity_summary": "one sentence — what construction work is being done",
  "description": "detailed job description capturing: all trade types and work 
                  activities, access methods (scaffold/EWP/ladder), materials 
                  and chemicals, location context (heights/confined spaces/traffic/
                  underground services), specific hazards mentioned. Write as if 
                  describing the job to generate a SWMS — be specific.",
  "hrcw_categories": ["list of HRCW categories that appear to apply"]
}}

Focus on WHAT work is being done, not commercial or contractual terms.
Return only valid JSON, no preamble.
"""


async def analyse_existing_swms(swms_text: str) -> dict:
    """Mode 02: Analyse uploaded SWMS, return gap analysis + job data."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": ANALYSE_PROMPT.format(swms_text=swms_text[:12000])
            }]
        )
        return _parse_json_response(response.content[0].text)
    except Exception as e:
        logger.error(f"SWMS analysis error: {e}")
        raise RuntimeError(f"Could not analyse SWMS: {str(e)}")


async def extract_scope_from_document(doc_text: str) -> dict:
    """Mode 03: Extract work scope from Scope of Works / Specification."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": SCOPE_EXTRACT_PROMPT.format(doc_text=doc_text[:12000])
            }]
        )
        return _parse_json_response(response.content[0].text)
    except Exception as e:
        logger.error(f"Scope extraction error: {e}")
        raise RuntimeError(f"Could not extract scope: {str(e)}")
```

---

## FILE 5 — `api/upload_routes.py`

```python
"""
upload_routes.py
Endpoints for Mode 02 (existing SWMS) and Mode 03 (scope of works).
Accepts files (PDF/DOCX/TXT) and images (JPG/PNG) including multiple files.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List

from core.auth import get_current_user
from core.document_extractor import (
    extract_text, extract_multiple, truncate_for_prompt,
    IMAGE_EXTENSIONS, DOC_EXTENSIONS
)
from core.swms_analyser import analyse_existing_swms, extract_scope_from_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB per file
MAX_FILES = 10                       # max photos/files per upload
ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS


def validate_files(files: List[UploadFile]):
    from pathlib import Path
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' — unsupported type. "
                       f"Upload PDF, DOCX, TXT, JPG, or PNG."
            )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES} files per upload."
        )


def build_job_data(result: dict) -> dict:
    """Extract job_data fields from analyser result."""
    return {
        "description": result.get("description", ""),
        "work_activity_summary": result.get("work_activity_summary", ""),
        "pcbu_name": result.get("pcbu_name", ""),
        "principal_contractor": result.get("principal_contractor", ""),
        "project_address": result.get("project_address", ""),
        "manager_name": result.get("manager_name", ""),
        "jurisdiction": result.get("jurisdiction", "AU"),
    }


@router.post("/analyse-swms")
async def analyse_swms(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 02: Upload existing SWMS (file or photos).
    Returns gap analysis + pre-filled job_data for Direct Fields form.
    """
    validate_files(files)

    file_tuples = []
    for file in files:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds 10MB limit."
            )
        file_tuples.append((contents, file.filename))

    try:
        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_prompt(raw_text)
        result = await analyse_existing_swms(truncated)

        return JSONResponse({
            "mode": "02",
            "file_count": len(files),
            "char_count": len(raw_text),
            "gaps": result.get("gaps", []),
            "existing_tasks": result.get("existing_tasks", []),
            "hrcw_categories": result.get("hrcw_categories", []),
            "job_data": build_job_data(result)
        })

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"analyse-swms error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-scope")
async def extract_scope(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 03: Upload Scope of Works / Specification (file or photos).
    Returns extracted job_data for Direct Fields form.
    """
    validate_files(files)

    file_tuples = []
    for file in files:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds 10MB limit."
            )
        file_tuples.append((contents, file.filename))

    try:
        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_prompt(raw_text)
        result = await extract_scope_from_document(truncated)

        return JSONResponse({
            "mode": "03",
            "file_count": len(files),
            "char_count": len(raw_text),
            "hrcw_categories": result.get("hrcw_categories", []),
            "job_data": build_job_data(result)
        })

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"extract-scope error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## FILE 6 — `api/main.py` updates

Add these routes and register the upload router:

```python
from api.upload_routes import router as upload_router
app.include_router(upload_router)

# Dashboard route — post-login landing page
@app.get("/dashboard")
async def dashboard():
    return FileResponse("frontend/dashboard.html")

# SWMS tool — replaces /app (old dev.html)
@app.get("/swms")
async def swms_app():
    return FileResponse("frontend/app.html")

# Keep /app pointing to dashboard now
@app.get("/app")
async def app_redirect():
    return FileResponse("frontend/dashboard.html")

# RA placeholder
@app.get("/ra")
async def ra_app():
    # Return dashboard for now — RA spec TBD
    return FileResponse("frontend/dashboard.html")
```

---

## FILE 7 — `frontend/app.html` JavaScript behaviour

### Review frequency logic

```javascript
const REVIEW_DEFAULT = [
  "If a control measure does not control the risk",
  "When legislation or codes of practice change, new work methods, products, or equipment are introduced",
  "Minimum 12-monthly review"
];

const REVIEW_OPTIONS = [
  "Before any change is made to the way the construction work is carried out",
  "Before a new system of work is introduced",
  "Before the place where the work is being carried out is changed",
  "If a new hazard is identified",
  "If new information about a hazard becomes available",
  "If a notifiable incident occurs in relation to construction work",
  "If a control measure does not control the risk",
  "A request for a review is received from a health and safety representative",
  "When legislation or codes of practice change, new work methods, products, or equipment are introduced",
  "Minimum 12-monthly review"
];

function getReviewText() {
  const checked = REVIEW_OPTIONS.filter((_, i) =>
    document.getElementById(`review-${i}`).checked
  );
  const selected = checked.length > 0 ? checked : REVIEW_DEFAULT;
  return "This SWMS will be reviewed: " + selected.join(" — ");
}
```

### Direct Fields → generate payload

```javascript
function buildPayload() {
  const today = new Date().toLocaleDateString('en-AU', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  });

  return {
    description:           getField('job-description')    || '',
    pcbu_name:             getField('pcbu-name')          || '',
    manager_name:          getField('your-name')          || '',
    project_address:       getField('site-address')       || '',
    principal_contractor:  getField('principal-contractor')|| '',
    supervisor_name:       getField('compliance-person')  || '',
    reviewer_name:         getField('review-person')      || '',
    swms_date:             getField('swms-date')          || today,
    review_frequency:      getReviewText(),
    jurisdiction:          getField('jurisdiction')       || 'AU',
    format:                getSelectedFormat()            || 'docx',
  };
}

function getField(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}
```

### Upload button behaviour

```javascript
// Single button → shows inline options
function showUploadOptions(mode) {
  // Toggle a small options panel below the button showing:
  // [📁 Upload file]  [📷 Take photo / Upload image]
}

// File input — accepts docs
function setupDocUpload(mode) {
  const input = document.createElement('input');
  input.type = 'file';
  input.multiple = true;
  input.accept = '.pdf,.docx,.doc,.txt';
  input.onchange = (e) => handleFilesSelected(e.target.files, mode);
  input.click();
}

// Photo input — accepts images, opens camera on mobile
function setupPhotoUpload(mode) {
  const input = document.createElement('input');
  input.type = 'file';
  input.multiple = true;
  input.accept = 'image/*';
  // capture="environment" opens rear camera on mobile
  input.setAttribute('capture', 'environment');
  input.onchange = (e) => handleFilesSelected(e.target.files, mode);
  input.click();
}

// Track selected files across both inputs
let selectedFiles = { '02': [], '03': [] };

function handleFilesSelected(fileList, mode) {
  const files = Array.from(fileList);
  selectedFiles[mode] = [...selectedFiles[mode], ...files];
  renderFileChips(mode);
}

function renderFileChips(mode) {
  const container = document.getElementById(`file-chips-${mode}`);
  container.innerHTML = '';
  selectedFiles[mode].forEach((file, i) => {
    const chip = document.createElement('span');
    chip.className = 'file-chip';
    const isImage = file.type.startsWith('image/');
    chip.innerHTML = `${isImage ? '📷' : '📄'} ${file.name} 
                      <button onclick="removeFile('${mode}', ${i})">×</button>`;
    container.appendChild(chip);
  });
  // Show analyse button if files present
  const btn = document.getElementById(`btn-analyse-${mode}`);
  if (btn) btn.style.display = selectedFiles[mode].length > 0 ? 'block' : 'none';
}

function removeFile(mode, index) {
  selectedFiles[mode].splice(index, 1);
  renderFileChips(mode);
}

async function runAnalysis(mode) {
  const files = selectedFiles[mode];
  if (!files.length) return;

  const endpoint = mode === '02' ? '/upload/analyse-swms' : '/upload/extract-scope';
  const formData = new FormData();
  files.forEach(f => formData.append('files', f));

  showStatus('Analysing document...', 'loading');

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Analysis failed');
    }
    const result = await res.json();
    prefillDirectFields(result.job_data);

    if (mode === '02' && result.gaps?.length) {
      showGaps(result.gaps);
      showStatus(`Analysis complete — ${result.gaps.length} gaps identified. Review fields and generate.`, 'success');
    } else {
      showStatus('Scope extracted. Review fields and generate.', 'success');
    }

  } catch (err) {
    showStatus(`Error: ${err.message}`, 'error');
  }
}

function prefillDirectFields(jobData) {
  // Only pre-fill if field is currently empty — don't overwrite user input
  if (jobData.pcbu_name)            setIfEmpty('pcbu-name', jobData.pcbu_name);
  if (jobData.manager_name)         setIfEmpty('your-name', jobData.manager_name);
  if (jobData.project_address)      setIfEmpty('site-address', jobData.project_address);
  if (jobData.description)          setIfEmpty('job-description', jobData.description);
  if (jobData.principal_contractor) setIfEmpty('principal-contractor', jobData.principal_contractor);
}

function setIfEmpty(id, value) {
  const el = document.getElementById(id);
  if (el && !el.value.trim()) el.value = value;
}
```

---

## FILE 8 — `requirements.txt`

Add:
```
pdfplumber==0.11.0
```

---

## PLACEHOLDER FALLBACK BEHAVIOUR

When a field is left empty and the SWMS is generated:
- All empty fields must render as italic placeholder text in the docx output
- Map in `renderers/docx_renderer.py`:

```python
FIELD_PLACEHOLDERS = {
    'pcbu_name':            '[Insert PCBU here]',
    'manager_name':         '[Insert Manager name here]',
    'project_address':      '[Insert Site Address Here]',
    'description':          '[Insert description here]',
    'principal_contractor': '[Insert Principal Contractor Name Here]',
    'supervisor_name':      '[Insert Supervisor name here]',
    'reviewer_name':        '[Insert Manager name here]',
    'work_activity':        '[Insert work activity here]',
    'swms_date':            None,  # use today's date — never placeholder
}

def resolve_field(value: str, field_key: str) -> tuple[str, bool]:
    """
    Returns (text_to_render, is_placeholder).
    Caller applies italic formatting if is_placeholder is True.
    """
    if value and value.strip():
        return value.strip(), False
    if field_key == 'swms_date':
        from datetime import date
        return date.today().strftime('%d/%m/%Y'), False
    placeholder = FIELD_PLACEHOLDERS.get(field_key, '[Insert here]')
    return placeholder, True
```

Apply italic run formatting when `is_placeholder` is True.

---

## IMPLEMENTATION ORDER FOR CLAUDE CODE

```
1. Create core/document_extractor.py
2. Create core/swms_analyser.py
3. Create api/upload_routes.py
4. Update api/main.py (register router, add routes)
5. Create frontend/dashboard.html
6. Create frontend/app.html (full implementation)
   - Mode tabs: Manual / Upgrade SWMS / Scope of Works or Specification
   - Direct Fields form (always visible)
   - Upload section (Mode 02 + 03 only)
   - Upload button → file or photo options
   - Multi-file support with file chips
   - Review frequency checkboxes with default fallback
   - Date defaults to today
   - Gaps panel for Mode 02
7. Update renderers/docx_renderer.py — placeholder fallback + italic
8. Update requirements.txt — add pdfplumber
9. Test locally then commit
```

---

## COMMIT

```bash
git add -A
git commit -m "Build app.html + dashboard + Mode 02/03 with upload + photo capture

- dashboard.html: post-login SWMS/RA selector
- app.html: replaces dev.html — three mode tabs, direct fields form
- Mode 02: upload existing SWMS (file or multi-photo) → gap analysis → pre-fill
- Mode 03: upload scope of works (file or multi-photo) → extract → pre-fill
- document_extractor.py: PDF/DOCX/TXT + Claude Vision for photos
- swms_analyser.py: gap analysis + scope extraction prompts
- upload_routes.py: /upload/analyse-swms + /upload/extract-scope
- Direct fields: all optional, italic placeholder fallback, date defaults today
- Review frequency: multi-select, auto-defaults to 3 items if none selected
- pdfplumber added to requirements.txt"
git push origin main
```

---

## NOTES

- RA card on dashboard shows "Coming Soon" toast — no /ra route needed yet
- `capture="environment"` on the photo input opens rear camera on mobile
  automatically — no extra code needed
- The existing generateSWMS() function in dev.html should be ported to 
  app.html and updated to accept buildPayload() output directly
- dev.html can be kept in the repo but the /app route now serves dashboard.html
- getToken() reads from localStorage key 'access_token' — confirm this matches
  existing auth implementation before wiring up upload fetch calls
