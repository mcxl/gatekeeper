{{>headless_header}}

Run a batch of commercial pilot jobs in sequence.

Jobs to run:
{{batch_jobs}}

For each job:
1. Generate SWMS
2. Run validator
3. Render docx
4. Run issue gate on docx
5. Do consultant quick-scan
6. Record pilot evidence

After all jobs:
1. Update pilot tracking table
2. Run detect_patterns()
3. Report cross-job recurring defect summary
4. Commit tracking updates

{{>standing_rules}}

{{>stop_and_report}}
