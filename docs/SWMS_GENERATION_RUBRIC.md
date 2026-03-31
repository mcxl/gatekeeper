# SWMS generation rubric — master spec
# Column structure: 8 columns fixed
# 1. Step 2. Task 3. Hazard 4. Risk (Pre)
# 5. Controls 6. Risk (Post) 7. Responsibility
# 8. CCVS Code (CCVS + HP + SWT in that order)
#
# Agent-specific slices derived from this document:
# agents/decomposer.py — sequencing, framework, job-type overrides
# agents/control_writer.py — dominant control family, CCVS Code rules, HP/SWT, anti-drift
# core/reviewer_agent.py — quality thresholds, issue gates, coordinator floor rule
#
# Human reference only.
# Do not parse at runtime.
#
# Note:
# Full rubric content will be added manually or in a later docs-only phase.
