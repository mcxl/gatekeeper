# Combined WHS Control Pack — Contract Definitions

## Status: Contract definition only — not yet approved for implementation

---

## 1. Input Schema

### 1.1 Source Documents

The primary input is one or more uploaded documents from which project context is extracted.

**Accepted source types:**
- Scope of works (PDF, DOCX)
- Project specification (PDF, DOCX)
- Tender schedule / subcontract schedule (PDF, DOCX)
- Existing project risk assessment or SWMS (PDF, DOCX)
- Site plans or drawings (PDF, PNG, JPG) — text/annotation extraction only
- Project brief or description (TXT, DOCX)

**Source metadata captured per document:**

```
source_documents: [
    {
        filename: str,
        file_type: str,          # "scope" | "specification" | "tender" | "swms" | "plan" | "brief"
        file_size_bytes: int,
        char_count: int,         # extracted text length
        upload_timestamp: str,
    }
]
```

### 1.2 Extracted Project Fields

Fields extracted from uploaded documents by the extraction pipeline (reusing `/intake/extract` logic).

**Required fields** (must be present or explicitly flagged as missing before generation):

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `project_name` | str | Extracted or user-entered | Short project title |
| `site_address` | str | Extracted or user-entered | Physical site location |
| `pcbu_name` | str | Extracted or user-entered | Principal contractor or PCBU |
| `client` | str | Extracted or user-entered | Client / principal |
| `jurisdiction` | str | Detected or user-selected | AU, NZ, UK, US, CA |
| `description` | str | Extracted — drives all inference | Full scope description, minimum 20 words |

**Optional fields** (improve output quality if present):

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `principal_contractor` | str | Extracted | If different from PCBU |
| `project_manager` | str | Extracted or user-entered | For document prepared-by |
| `construction_stages` | list[str] | Extracted | Stage names if identifiable |
| `trade_packages` | list[str] | Extracted or user-confirmed | Trade package names |
| `authority_interfaces` | list[str] | Extracted | e.g. Sydney Water, TfNSW |
| `project_value` | str | Extracted | For notification threshold assessment |
| `project_duration` | str | Extracted | For staging and hold point timing |
| `access_method` | str | Extracted | Primary access (scaffold, EWP, etc.) |
| `building_type` | str | Extracted | Existing, new, mixed |
| `occupancy` | str | Extracted | Occupied, unoccupied, mixed |

**Confidence per field:**

Each extracted field carries a confidence marker from extraction:

```
field_confidence: {
    "project_name": "high" | "medium" | "low" | "absent",
    "site_address": "high" | "medium" | "low" | "absent",
    ...
}
```

Fields marked `absent` must be flagged in the output as requiring user input before issue.

### 1.3 Fields Requiring User Confirmation

Before generation, the following should be reviewed by the user:

- `description` — drives all inference; must be accurate
- `trade_packages` — if extracted, user confirms or edits the list
- `jurisdiction` — auto-detected but user can override
- Any field marked `low` or `absent` confidence

### 1.4 Missing Information Handling

Fields that are missing or low-confidence at generation time:

- Render with placeholder: `[To be confirmed]`
- Add to `open_items` list in review metadata
- Do not fabricate values — use the placeholder pattern consistently
- Missing `description` blocks generation entirely (same as current SWMS/RA)

### 1.5 Authority / Interface Fields

Where the scope indicates authority interfaces, capture:

```
authority_interfaces: [
    {
        authority: str,          # "Sydney Water", "Transport for NSW", "Ausgrid"
        interface_type: str,     # "asset_protection", "hold_point", "permit", "notification"
        description: str,        # "Sydney Water asset relocation within road corridor"
        confirmed: bool,         # whether user has confirmed this interface exists
    }
]
```

These feed into hold point generation and the HRCW register.

---

## 2. Output Schema

### 2.1 Top-Level Output

```
{
    "document_type": "combined_whs_control_pack",
    "version": str,
    "generated_at": str,           # ISO timestamp

    "project_meta": { ... },       # Section 1: Document Information
    "scope_summary": str,          # Section 2: Methodology/scope text
    "review_benchmark_note": str,  # Section 3: How to use as SWMS review benchmark
    "hrcw_register": [ ... ],      # Section 4: 17-category HRCW assessment
    "swms_matrix": [ ... ],        # Section 5: Trade package SWMS requirements
    "hold_points": [ ... ],        # Section 6: Mandatory stops
    "risk_register": [ ... ],      # Section 7: Grouped risk entries
    "review_meta": { ... },        # Review state and open items

    "ra_classification": { ... },  # Classification used for inference
    "inference": { ... },          # Full inference dict (retained for traceability)
}
```

### 2.2 HRCW Register Entries

```
hrcw_register: [
    {
        ref: str,                  # "H01" through "H17"
        name: str,                 # WHS Reg Schedule 1 category name
        status: str,               # "YES" | "CONDITIONAL" | "NO"
        reason: str,               # Why this status was assigned
        packages: list[str],       # Trade packages that trigger this category
        risk_description: str,     # Brief risk description for this project
        swms_required: str,        # "YES" | "CONDITIONAL" | "NO" with note
    }
]
```

### 2.3 SWMS Matrix Entries

```
swms_matrix: [
    {
        trade_package: str,        # "Traffic Management", "Sydney Water Relocation"
        hrcw_refs: list[str],      # ["H14", "H15"]
        swms_title: str,           # Recommended SWMS title
        submitted_by: str,         # "[Insert subcontractor]" placeholder
        reviewed_by: str,          # "SD Group Site Manager" or role
        required_before: str,      # "Before any works commence in road corridor"
    }
]
```

### 2.4 Hold Point Entries

```
hold_points: [
    {
        ref: str,                  # "HP-01"
        name: str,                 # "Traffic Management Accepted Before Works"
        trade_packages: list[str], # Which packages this applies to
        condition: str,            # What must be met before proceeding
        authorised_by: str,        # Role or person who signs off
        evidence_required: str,    # What record must be on site
    }
]
```

### 2.5 Risk Register Entries

```
risk_register: [
    {
        group: str,                # "Traffic Management", "Service Location"
        ref: str,                  # "TM-01", "SL-01"
        activity: str,             # Activity / hazard description
        hrcw_category: str,        # "H14 — Traffic corridor" or ""
        initial_risk: str,         # "High (3)" — L x C
        controls: str,             # Minimum standard controls (summary)
        residual_risk: str,        # "Medium (2)"
        responsible: str,          # "All trade packages" or specific
    }
]
```

Risk register entries are grouped by `group` field. Groups appear in construction sequence. Standing hazards (plant separation, silica, heat, manual handling) appear as a final group applicable to all phases.

---

## 3. Review Schema

### 3.1 Review Metadata

```
review_meta: {
    source_documents: list[dict],  # From input — what was uploaded
    reviewed_by: str | null,       # Name of reviewer (set after review)
    reviewed_at: str | null,       # ISO timestamp of review completion
    review_status: str,            # "draft" | "under_review" | "reviewed" | "issued"
    open_items: list[str],         # Items requiring confirmation before issue
    confidence_summary: {
        fields_confirmed: int,
        fields_inferred: int,
        fields_missing: int,
    },
}
```

### 3.2 Review Status Values

| Status | Meaning |
|--------|---------|
| `draft` | Generated but not yet reviewed by a competent person |
| `under_review` | Assigned to a reviewer, not yet completed |
| `reviewed` | Reviewed and accepted by a named person |
| `issued` | Formally issued for project use |

All generated documents start at `draft`. The system does not automatically advance status — a human reviewer must explicitly mark the document as reviewed.

### 3.3 What the Reviewer Confirms

The reviewer is expected to confirm:

1. **Scope accuracy** — does the scope summary reflect the actual project?
2. **HRCW register** — are the YES/CONDITIONAL/NO assessments correct for this project?
3. **Trade packages** — are the right packages identified? Are any missing?
4. **Hold points** — are the conditions and authorisation correct?
5. **Risk register** — are the hazards relevant and are the controls adequate as minimum standards?
6. **Open items** — have all missing-information items been resolved or accepted?

### 3.4 Open Items

Open items are generated automatically from:

- Fields with `absent` or `low` confidence
- HRCW categories marked `CONDITIONAL`
- Hazards with `if_applicable` or `requires_verification` confidence
- Authority interfaces not yet confirmed
- Trade packages extracted but not user-confirmed

Each open item has:

```
{
    item: str,                     # Description of what needs confirmation
    source: str,                   # "extraction" | "hrcw_register" | "risk_register" | "authority"
    resolved: bool,                # Set to true when reviewer confirms
}
```

### 3.5 What Must Be Confirmed Before Issue

The document should not advance to `issued` status while:

- Any required field is `absent` and unresolved
- The `reviewed_by` field is empty
- Any open item marked as blocking is unresolved

The system should display a clear checklist of unresolved items when the reviewer attempts to issue.

---

## 4. Benchmark / Result Schema

### 4.1 How We Assess Benchmark Alignment

Each generated combined pack is assessed against the benchmark document (Withers Road Rev01) on these dimensions:

### 4.2 Completeness Checks

| Check | Pass condition |
|-------|---------------|
| HRCW register has 17 entries | All Schedule 1 categories present |
| Each HRCW entry has status + reason | No empty status fields |
| SWMS matrix has at least 1 entry | At least one trade package identified |
| Hold points present | At least 2 hold points for any civil/multi-trade project |
| Risk register has entries | At least 5 risk entries for a multi-trade scope |
| Scope summary is non-empty | Description text present |
| All required project meta fields populated or placeholdered | No silently missing fields |

### 4.3 Correctness / Classification Checks

| Check | Pass condition |
|-------|---------------|
| Job type correctly classified | Matches scope description intent |
| HRCW YES categories match scope | Triggered categories are genuinely implied by the description |
| HRCW NO categories are correct | Suppressed categories are genuinely not applicable |
| HRCW CONDITIONAL categories are honest | Not asserted as YES when evidence is insufficient |
| Hold points match trade packages | Each hold point references a real trade package |
| Risk register groups match scope | Activity groups reflect stated work, not generic padding |

### 4.4 Reviewability Checks

| Check | Pass condition |
|-------|---------------|
| Document renders as a single coherent output | All sections present in correct order |
| Open items listed clearly | Reviewer can see what needs confirmation |
| Conditional items flagged | Not buried — visible in assumptions or open items |
| Placeholders used for missing fields | `[To be confirmed]` not blank |
| Review status starts at `draft` | Not pre-issued |

### 4.5 Missing Information Discipline

| Check | Pass condition |
|-------|---------------|
| No fabricated field values | Missing fields use placeholders, not guesses |
| No over-called HRCW | Categories not triggered by the description are NO, not CONDITIONAL |
| CONDITIONAL is used honestly | Only where the description provides partial evidence |
| Open items count matches missing/conditional items | Nothing silently dropped |

### 4.6 Product Shape Alignment

| Check | Pass condition |
|-------|---------------|
| Section order matches benchmark | Doc info → scope → HRCW → SWMS matrix → hold points → risk register |
| HRCW register is a formal table | Not inline text or bullets |
| Hold points have condition + authorised-by + evidence | Not just a name |
| Risk register is grouped by trade/activity | Not a flat list |
| SWMS matrix shows trade → HRCW → SWMS title mapping | Not just a list of SWMS names |

---

## 5. Remaining Decisions After Contract Definition

These contracts are defined but the following decisions remain open before implementation:

### Decision 1: Trade Package Identification Method

**Options:**
- A: Deterministic keyword mapping from description to trade packages (fast, may miss packages)
- B: HRCW-derived (each triggered HRCW implies a trade package — good coverage, may over-generate)
- C: Extraction + user confirmation (most accurate, requires review step)

**Recommendation:** Option C for first version — extract candidate packages, let user confirm. Fall back to B if user skips confirmation.

### Decision 2: Risk Register Depth

**Options:**
- A: One-line summary controls per hazard (benchmark style — "minimum standard")
- B: Medium depth — 2-3 controls per hazard with hierarchy labels
- C: Full SWMS-level detail (not recommended for control pack)

**Recommendation:** Option A for first version — matches the benchmark document. Individual SWMSs provide the detail.

### Decision 3: Review Workflow Shape

**Options:**
- A: Extract → generate → review (one review step after generation)
- B: Extract → review extraction → generate → review output (two review steps)
- C: Extract → review extraction → generate (review only at extraction, trust generation)

**Recommendation:** Option B for consultant use — consultants will want to confirm extracted scope before generation, then review the output before issue. But Option A is acceptable for first prototype.
