# RPD Job SWMS Build Workflow

## Example: 18 Danks Street, Waterloo — Remedial Painting

This shows exactly how a job-specific SWMS is created from `RPD_MASTER_SWMS_TEMPLATE_V1.docx`.

---

## STEP 1 — Header Population

Fill Table 0 with job details. All fields that say `[Insert...]` get real values:

| Field | Master Template | → Job SWMS |
|-------|----------------|------------|
| Site | `[Insert Site Address Here]` | `18 Danks Street, Waterloo NSW 2017` |
| Works Manager | `[Insert Project Manager Here]` | `[Actual name]` |
| Work Activity | `[Insert Description Here]` | `Remedial repairs including crack stitching, sealant replacement, exterior/interior painting, and associated high-access works` |
| PC | `Robertson's Remedial and Painting Pty Ltd` | `Robertson's Remedial and Painting Pty Ltd` (or actual PC if subcontracting) |
| Date | `[Insert Date Here]` | `23/02/2026` |
| HRCW boxes | Tick per scope | `[✓] Risk of a person falling more than 2 metres` + `[✓] Work in an area with movement of powered mobile plant` |

---

## STEP 2 — Task Selection

**All 20 master tasks remain in every job SWMS.** No rows are deleted and no renumbering occurs. If a task does not apply to a particular job, it stays in the document — the worker simply skips it on site. This ensures every job SWMS has the same structure, same task numbers, and same layout for PC audit consistency.

### Danks St Task Applicability

| Master Task | Applies to Danks St? | Site-Specific Notes |
|-------------|---------------------|---------------------|
| 1. Site Induction, Daily Sign-In and SWMS Induction | ✅ Yes | — |
| 2. Emergency Response | ✅ Yes | Site address, muster point, IRA/EWP rescue details |
| 3. Residents and Public Interface | ✅ Yes | Occupied strata building |
| 4. High Access — Ladder Use | ✅ Yes | Short-duration interior tasks |
| 5. Scaffold — Erect, Use, and Dismantle | ❌ Not this job | Stays in document |
| 6. Industrial Rope Access | ✅ Yes | Exterior rope access |
| 7. Work-Positioning System — Fall Restraint | ❌ Not this job | Stays in document |
| 8. EWP Operation — Boom and Scissor Lift | ✅ Yes | Exterior boom lift |
| 9. Jackhammering, Cutting, Grinding — Silica Dust | ✅ Yes | Spalling repairs, crack stitching |
| 10. Manual Handling | ✅ Yes | General |
| 11. Housekeeping and Waste Management | ✅ Yes | General |
| 12. Balcony Security (Occupied Residential) | ✅ Yes | Balcony dust seals, resident notification |
| 13. Hazardous Chemicals — Paints, Solvents, Coatings | ✅ Yes | Multiple products on site |
| 14. High-Pressure Water Cleaning | ✅ Yes | Pre-paint pressure wash |
| 15. Surface Preparation — Non-Silica-Lead | ✅ Yes | Interior/exterior prep |
| 16. Sealant Replacement and Recaulking | ✅ Yes | Expansion joints and window perimeters |
| 17. Exterior and Interior Painting — Brush and Roller | ✅ Yes | Core scope |
| 18. Lead Paint Assessment and 6-Step Encapsulation | ✅ Yes | Pre-1970 building |
| 19. Painting — NON-FRIABLE Asbestos Cement Sheet | ❌ Not this job | Stays in document |
| 20. Hot and Dangerous Weather | ✅ Yes | Outdoor work |

---

## STEP 3 — Site-Specific Additions

Small additions appended to control cells with `[SITE SPECIFIC]` prefix. **Core master text stays untouched.**

### Example additions for 18 Danks St:

**Task 2 — Emergency Response** (Master row 2)
Append to end of control cell:
```
[SITE SPECIFIC] Site address: 18 Danks Street, Waterloo NSW 2017
[SITE SPECIFIC] Muster point: Danks Street footpath — briefed at daily toolbox
[SITE SPECIFIC] IRA rescue: Level 2/3 technician lowers via pre-rigged rescue system
[SITE SPECIFIC] EWP rescue: ground override controls — location briefed daily
```

**Task 3 — Residents and Public Interface** (Master row 3)
Append to end of control cell:
```
[SITE SPECIFIC] Strata manager: [Name] — notified 48hrs before each work phase
[SITE SPECIFIC] Resident access: balcony clearing required before exterior work on each elevation
```

**Task 6 — Silica Dust** (Master row 9)
Append to end of control cell:
```
[SITE SPECIFIC] Concrete spalling repairs to balconies and soffits — jackhammer to sound base
[SITE SPECIFIC] Crack stitching: horizontal slots 25–35mm deep — depth stop set, services scan before cutting
[SITE SPECIFIC] Products: Fosroc Nitoprime Zincrich, Nitobond HAR, Renderox HB40, WHO-60 grout
```

**Task 9 — Balcony Security** (Master row 12)
Append to end of control cell:
```
[SITE SPECIFIC] Balcony dust seals installed before grinding/cutting on adjacent balconies
[SITE SPECIFIC] Residents notified 48hrs before balcony access required — written notice via strata
```

**Task 10 — Hazardous Chemicals** (Master row 13)
Append to end of control cell:
```
[SITE SPECIFIC] Products on site: Dulux Acratex Green Render Sealer, Dulux Weathershield X10, 
Dulux 1-Step Acrylic Primer, Dulux Aquanamel, Emer-proof Silane Clear Sealer, 
Parchem Fosroc Nitoseal MS300, Fosroc Nitoprime Zincrich
```

**Task 14 — Exterior and Interior Painting** (Master row 17)
Append to end of control cell:
```
[SITE SPECIFIC] Exterior system: Dulux Acratex Green Render Sealer + 2x Dulux Weathershield X10
[SITE SPECIFIC] Interior joinery: 1x Dulux 1-Step + 2x Dulux Aquanamel (3-coat enamel)
[SITE SPECIFIC] Unpainted surfaces: 2x Emer-proof Silane Clear Sealer
[SITE SPECIFIC] Colours verified against architectural specification before application
```

**Task 15 — Lead Paint Assessment** (Master row 18)
Append to end of control cell:
```
[SITE SPECIFIC] Building circa [year] — lead assessment completed for all exterior painted surfaces
[SITE SPECIFIC] Results: [documented on site / no lead detected / lead detected — encapsulation only]
```

---

## STEP 4 — Requirements Table Update

Table 5 requirements updated for job-specific plant, products, and permits:

| Row | Addition |
|-----|----------|
| Plant | Add: `Petrol-driven pressure washer. Industrial rope access equipment (IRATA).` |
| Hazardous substances | Add specific product names from job scope |
| Permits | Add: `IRATA/ARAA rope access certification` if rope access in scope |

---

## STEP 5 — HRCW Checkboxes

Tick the relevant High Risk Construction Work boxes in Table 0 rows 3–8 based on actual scope.

---

## What I Will NEVER Do

- ❌ Reword any task title, hazard description, or control text from the master
- ❌ Delete any task row from a job SWMS — all 20 stay
- ❌ Renumber tasks — master numbering is fixed
- ❌ Add a new task without flagging it to Alan first
- ❌ Remove HOLD POINT conditions or STOP WORK triggers
- ❌ Change the CCVS formatting structure
- ❌ Modify risk scores, codes, or responsibility assignments

## What I Will Always Do

- ✅ Use `[SITE SPECIFIC]` prefix on every addition
- ✅ Keep all 20 tasks in every job SWMS — same structure every time
- ✅ Ask Alan before creating any new task not in the master
- ✅ Preserve all formatting locks (fixed layout, cantSplit, tblHeader, CCVS structure)
