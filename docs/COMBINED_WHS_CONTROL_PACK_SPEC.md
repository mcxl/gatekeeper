# Combined WHS Control Pack — Product Specification

## Status: SPECIFICATION ONLY — Not yet approved for implementation

---

## 1. Purpose

A combined WHS control pack is a single project-level document that brings together the HRCW register, SWMS matrix, hold point schedule, and project risk assessment into one structured deliverable. It sits above individual trade-package SWMSs and provides the framework that a principal contractor or PCBU uses to manage WHS across a multi-trade project.

This is a **separate product mode** from the standalone SWMS and standalone RA. It is not an extension of either.

## 2. Target User

- Principal contractors managing multi-trade construction projects
- PCBU safety managers who need a project-level WHS overview before individual SWMSs are written
- Safety consultants preparing project-level WHS documentation as a pre-construction deliverable

## 3. When to Use

- At project setup, before trade-package SWMSs are prepared
- When the scope involves multiple trade packages with different HRCW categories
- When a principal contractor needs to define hold points and SWMS requirements for all subcontractors
- When the project involves authority interfaces (Sydney Water, Transport for NSW, etc.) that impose their own hold points

The standalone SWMS remains the correct product for single-trade, single-scope work. The standalone RA remains correct for project-level hazard assessment without the SWMS matrix or hold point schedule.

## 4. Section Structure

Based on the Withers Road benchmark document (SD_Group_Withers_Road_WHS_Control_Document_Rev01.docx):

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
- This is NEW — not currently produced by any pipeline

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

## 5. Data Contract

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
    "scope_summary": str,           # Construction methodology text
    "ra_classification": {          # From classify_ra_scope() or classify_swms_scope()
        "job_type": str,
        "building_context": str,
        "occupancy_context": str,
        "scope_modifiers": list[str],
    },
    "hrcw_register": list[dict],    # From _build_ra_hrcw_register()
    "swms_matrix": list[dict],      # NEW — trade packages with SWMS requirements
    "hold_points": list[dict],      # From RA supplementary sections logic
    "risk_register": list[dict],    # From _build_hazard_list() with phase grouping
    "inference": dict,              # Full inference dict
}
```

The `swms_matrix` is the only data structure that does not yet exist. All other sections can be derived from the current RA pipeline output.

## 6. Renderer Expectations

- Single .docx output using a dedicated template
- Portrait for most sections; landscape for risk register table (same as current RA)
- Professional black-and-white formatting with blue header accents
- Each section as a distinct table or structured content block
- Page numbering, footer with document reference
- HRCW register as a 7-column table (ref, category, triggered, packages, risk description, SWMS required)
- Hold point schedule as a 6-column table
- Risk register as a 7-column table grouped by trade package with phase headers

## 7. Benchmark Alignment Criteria

The output should be evaluated against the Withers Road benchmark document on:

1. **HRCW register completeness** — all 17 categories assessed with correct YES/CONDITIONAL/NO
2. **Trade package mapping** — correct SWMS requirements per trade
3. **Hold point specificity** — conditions, authorised-by, evidence fields populated
4. **Risk register grouping** — activities in construction sequence, grouped by trade
5. **Scope summary accuracy** — reflects the stated project description honestly
6. **Missing information discipline** — conditional items clearly flagged, not asserted as definite
7. **Authority interface** — Sydney Water, TfNSW, or equivalent hold points where applicable

## 8. Open Questions

1. **Input method**: Should the combined pack be generated from:
   - A single project description (like the current RA)?
   - A structured multi-field input (project name, trades, scope per trade)?
   - An uploaded scope document with extraction?

2. **SWMS matrix generation**: How are trade packages identified?
   - From the description (deterministic keyword mapping)?
   - From the HRCW register (each triggered category implies a trade)?
   - From explicit user input?

3. **Risk register depth**: Should controls be:
   - Benchmark-level summaries (one line per control, minimum standard)?
   - Full SWMS-level detail (multiple controls per hazard)?
   - The benchmark uses summary controls — "minimum standard" wording

4. **Relationship to standalone products**: Should the combined pack:
   - Replace the standalone RA for multi-trade projects?
   - Be offered alongside it?
   - Be the default for civil/infrastructure jobs?

5. **Template**: Should the combined pack:
   - Use a new dedicated template?
   - Extend the current RA template?
   - Use a completely different document structure?

6. **Scope boundary**: What is NOT included?
   - Individual trade-package SWMSs (those remain separate)
   - Detailed task-level controls (those are in SWMSs)
   - Site-specific induction content
   - Emergency response plans

## 9. Prerequisites Before Implementation

1. Standalone SWMS and standalone RA must be stable (currently: yes)
2. Benchmark document structure must be confirmed as the target (currently: Withers Road Rev01)
3. Product decision on input method (open question #1)
4. Product decision on trade package identification (open question #2)
5. Template design approved before renderer work begins

## 10. Estimated Scope

| Component | Effort | Dependencies |
|-----------|--------|-------------|
| SWMS matrix data structure | Medium | Trade package identification logic |
| Combined pack renderer | Large | New template + 8-section render logic |
| Trade package classifier | Medium | Input method decision |
| Integration into frontend | Medium | New route, form, and generation flow |
| Testing / regression | Medium | New reference case needed |

This is the largest new product mode since the original SWMS generator. It should not be started incrementally — it needs a design phase before implementation.
