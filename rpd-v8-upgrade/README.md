# RPD WHSMS V8 Upgrade & Breadcrumb Migration

## Project Structure

```
rpd-v8-upgrade/
├── phase-1-gap-analysis/
│   ├── RPD_WHSMS_V7_Bare_Minimum_Ed6_Review.docx    ← PRIMARY: Ed.6-only gap analysis
│   ├── RPD_WHSMS_V7_Gap_Analysis_Report.docx         ← SECONDARY: with ISO 45001 option
│   └── RPD_Phase1_Document_Register_and_Verification.xlsx
│       ├── Sheet 1: Document Register (40 items, status-coded)
│       └── Sheet 2: Breadcrumb Verification Checklist (15 modules)
│
├── phase-2-whsmp-update/
│   └── procedures/
│       ├── RPD_Procedure_Demolition_Work.docx
│       ├── RPD_Procedure_Asbestos_Management.docx
│       ├── RPD_Procedure_Ground_Works.docx
│       ├── RPD_Procedure_Mobile_Plant.docx
│       ├── RPD_Procedure_Temporary_Works.docx
│       ├── RPD_Procedure_Work_at_Height.docx
│       ├── RPD_Procedure_Underground_Overhead_Services.docx
│       └── RPD_Procedures_Combined_6pack.docx
│
├── phase-3-form-migration/       ← Breadcrumb config + archived .docx forms
├── phase-4-training/             ← Re-induction materials
├── phase-5-verification/         ← Audit checklists + sign-off
│
├── project-management/
│   └── RPD_Project_Tracker_and_Weekly_Report.xlsx
│       ├── Sheet 1: Project Tracker (24 tasks, 5 phases)
│       ├── Sheet 2: Weekly Status Report (print to PDF each Friday)
│       └── Sheet 3: Progress Log (append one row per week)
│
└── .gitattributes                ← Protects xlsx/docx binary formatting
```

## IMPORTANT: Preserving Excel Formatting

The `.gitattributes` file marks all `.xlsx` and `.docx` files as binary.
This prevents Git from attempting text-based merges which corrupt Office file formatting.

**Workflow for formatted Excel files:**
1. If you've reformatted an `.xlsx` locally, your version is the master
2. Push it to Git — Git stores the exact binary, formatting intact
3. If Claude Code needs to update data (not formatting), it should:
   - Read the existing file with openpyxl (preserving styles)
   - Modify only data cells
   - Save — formatting is retained
4. Never regenerate a formatted file from scratch — always edit in place

## Current Status
- **Phase 1**: COMPLETE — Gap analysis, document register, verification checklist
- **Phase 2**: IN PROGRESS — 7 demo procedures generated, V8 drafting pending
- **Phases 3–5**: NOT STARTED
