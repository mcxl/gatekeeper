{{>headless_header}}

Next commercial pilot job.

Customer: {{customer}}
Project: {{project}}
Job type: {{job_type}}
Scope modifiers: {{scope_modifiers}}

Scope of works:
{{scope_of_works}}

Workflow:
1. Generate the SWMS
2. Run validator
3. Render docx
4. Run issue gate on docx
5. Do consultant quick-scan with special attention to:
{{quick_scan_focus}}
6. Report checkpoint with:
   - validator result
   - issue gate result
   - consultant edits required
   - whether any new recurring deterministic defect appeared
   - whether the current 32-check gate improved real output quality
   - whether this SWMS would be issued, issued with edits, or held back

{{>standing_rules}}

{{>stop_and_report}}
