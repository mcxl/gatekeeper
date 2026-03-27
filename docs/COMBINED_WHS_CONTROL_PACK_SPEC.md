# Combined WHS Control Pack - Product Specification

## Status: SPECIFICATION ONLY - Prototype/spec-confirm first, not yet approved for implementation

---

## 1. Purpose

A combined WHS control pack is a single project-level document that brings together the HRCW register, SWMS matrix, hold point schedule, and project risk assessment into one structured deliverable. It sits above individual trade-package SWMSs and provides the framework that a consultant prepares for project-level WHS control planning and review across a multi-trade project.

This is a **separate product mode** from the standalone SWMS and standalone RA. It is not an extension of either.

## 2. Target User

- Primary user: safety/WHS consultant
- Secondary stakeholders: principal contractor, PCBU safety manager, project manager, reviewer

This mode should be designed first for consultant-led preparation and review, not for direct field/task-level SWMS authoring.

## 2A. Locked Product Decisions

The following decisions are now locked for the first version of this mode:
- product path: prototype/spec-confirm first, then build if the remaining answers are strong
- primary user: consultant
- primary input: uploaded scope/specification documents
- first output shape: one combined reviewable output
- relationship to existing products: standalone SWMS and standalone RA remain separate products

## 3. When to Use

- At project setup, before trade-package SWMSs are prepared
- When the scope involves multiple trade packages with different HRCW categories
- When a consultant or principal contractor needs to define hold points and SWMS requirements for all subcontractors
- When the project involves authority interfaces (Sydney Water, Transport for NSW, etc.) that impose their own hold points
- When uploaded scope/specification documents contain enough project context to assemble a project-level control pack

The standalone SWMS remains the correct product for single-trade, single-scope work. The standalone RA remains correct for project-level hazard assessment without the SWMS matrix or full control-pack structure.

## 4. Input Model

Primary input for the first version:
- uploaded scope/specification documents

Expected first-flow shape:
1. user uploads scope/specification documents
2. system extracts structured project context
3. extracted context is reviewed/confirmed where needed
4. combined control pack is generated as one reviewable output

Open detail still remaining:
- whether extraction review should be mandatory before generation
- whether user-entered supplementary fields should be required before generation

## 5. Section Structure

Based on the Withers Road benchmark document (`SD_Group_Withers_Road_WHS_Control_Document_Rev01.docx`):

### Section 1: Document Information
- Project name, site address, PCBU, client, applicable legislation
- Document version, date, prepared by

### Section 2: Construction Methodology and Scope Summary
- Concise project scope description
- Construction sequence / staging overview
- Key interfaces (authorities, utilities, traffic)

### Section 3: SWMS Review Benchmark Note
- How to use this document as a benchmark when reviewing subcontractor SWMSs
- Review criteria (project specificity, hazard identification, control adequacy, legislative alignment, practical usability)

### Section 4: HRCW Register
- All 17 WHS Reg Schedule 1 categories
- Each assessed as YES / CONDITIONAL / NO
- For YES/CONDITIONAL: which trade packages trigger it, risk description, SWMS requirement
- Derived from: `_build_ra_hrcw_register()` already implemented

### Section 5: SWMS Matrix
- Required SWMSs by trade package
- Each row: trade package name, HRCW references, SWMS title, submitted by, reviewed/accepted by, required before (condition)
- This is NEW - not currently produced by any pipeline

### Section 6: Hold Point Schedule
- Mandatory stops in the construction programme
- Each row: HP reference, hold point name, trade package, condition to be met, authorised by, evidence required
- Derived from: RA hold-point logic already implemented for civil infrastructure + occupied buildings

### Section 7: Project Risk Assessment (Risk Register)
- Activities presented in construction sequence
- Grouped by trade package / activity phase
- Each row: reference, activity/hazard, HRCW category, initial risk, controls (minimum standard), residual risk, responsible
- Derived from: `_build_hazard_list()` with phase grouping already implemented

### Section 8: Footer / Document Control
- Document reference, revision, jurisdiction, page numbering

## 6. Data Contract

The combined pack renderer would consume:

```python
{
    "project_meta": {
        "project_name": str,
        "site_address": str,
        "pcbu": str,
        "client": str,
        "jurisdiction": str,
        "version": str,
        "date": str,
        "prepared_by": str,
    },
    "scope_summary": str,           # Construction methodology text extracted/reviewed from uploaded docs
    "ra_classification": {
        "job_type": str,
        "building_context": str,
        "occupancy_context": str,
        "scope_modifiers": list[str],
    },
    "hrcw_register": list[dict],    # From _build_ra_hrcw_register()
    "swms_matrix": list[dict],      # NEW - trade packages with SWMS requirements
    "hold_points": list[dict],      # From RA supplementary sections logic
    "risk_register": list[dict],    # From _build_hazard_list() with phase grouping
    "inference": dict,              # Full inference dict
    "review_meta": {
        "source_documents": list[dict],
        "reviewed_by": str | None,
        "review_status": str,
        "open_items": list[str],
    },
}
```

The `swms_matrix` is the only major data structure that does not yet exist. The review metadata contract for this mode will also need to be defined explicitly rather than inherited implicitly from current flows.

## 7. Renderer Expectations

- One combined reviewable output first
- Preferred first implementation shape: one combined `.docx` plus review metadata/state
- Use a dedicated template
- Portrait for most sections; landscape for risk register table where needed
- Professional black-and-white formatting with blue header accents
- Each section as a distinct table or structured content block
- Page numbering, footer with document reference
- HRCW register as a formal table
- Hold point schedule as a formal table
- Risk register grouped by trade package or activity group

## 8. Benchmark Alignment Criteria

The output should be evaluated against the Withers Road benchmark document on:

1. **HRCW register completeness** - all 17 categories assessed with correct YES/CONDITIONAL/NO
2. **Trade package mapping** - correct SWMS requirements per trade
3. **Hold point specificity** - conditions, authorised-by, evidence fields populated
4. **Risk register grouping** - activities in construction sequence, grouped by trade or activity
5. **Scope summary accuracy** - reflects the stated project description honestly
6. **Missing information discipline** - conditional items clearly flagged, not asserted as definite
7. **Authority interface** - Sydney Water, TfNSW, or equivalent hold points where applicable
8. **Reviewability** - one combined output can be reviewed coherently before issue or downstream use

## 9. Open Questions

1. **SWMS matrix generation**: How are trade packages identified?
   - From the extracted description (deterministic keyword mapping)?
   - From the HRCW register (each triggered category implies a trade)?
   - From explicit user confirmation after extraction?

2. **Risk register depth**: Should controls be:
   - Benchmark-level summaries (one line per control, minimum standard)?
   - Medium-depth grouped controls?
   - Full SWMS-level detail (not recommended for first version)?

3. **Relationship to standalone products**: This is now mostly decided:
   - It should not replace standalone RA or standalone SWMS
   - It should sit above them as a separate product mode
   - Open detail remaining: when should it be offered by default vs optionally?

4. **Template**: Should the combined pack:
   - Use a new dedicated template?
   - Extend the current RA template?
   - Use a completely different document structure?

5. **Review workflow shape**:
   - Should review happen after extraction but before generation?
   - Should review happen after generation only?
   - Should there be both an extraction-review step and a final document-review step?

6. **Scope boundary**: What is NOT included?
   - Individual trade-package SWMSs (those remain separate)
   - Detailed task-level controls (those are in SWMSs)
   - Site-specific induction content
   - Emergency response plans

## 10. Prerequisites Before Implementation

1. Standalone SWMS and standalone RA must remain stable
2. Benchmark document structure must remain the target reference for this mode
3. Product decision on trade package identification (open question #1)
4. Product decision on risk register depth and review workflow shape (open questions #2 and #5)
5. Template design approved before renderer work begins
6. Stable contracts defined for input, output, review, and benchmark/result behavior

## 11. Estimated Scope

| Component | Effort | Dependencies |
|-----------|--------|-------------|
| SWMS matrix data structure | Medium | Trade package identification logic |
| Combined pack renderer | Large | New template + section render logic |
| Trade package classifier | Medium | Trade package identification decision |
| Extraction/review flow | Medium | Uploaded document flow + review contract |
| Integration into frontend | Medium | New route, form, and generation/review flow |
| Testing / regression | Medium | New reference case needed |

This is the largest new product mode since the original SWMS generator. It should not be started incrementally - it needs a design phase before implementation.
