"""
prompts/control_pack.py -- Project WHS benchmark / control-pack behavioural prompt layer.

Composed with system.py to form the full control-pack generation behaviour.
"""

CONTROL_PACK_BEHAVIOUR = """\
PROJECT WHS BENCHMARK RULES:
1. Build the draft from the actual project scope, source documents, and defensible likely package structure.
2. Prefer package fidelity over generic project summaries.
3. Do not invent package boundaries, authority requirements, or specialist scopes unless supported by the source or clearly marked provisional.
4. Distinguish clearly between:
   - confirmed packages
   - provisional packages
   - conditional hazards
   - open items requiring confirmation
5. Use HRCW logic in a disciplined way: YES / CONDITIONAL / NO with specific reasons for conditional calls.
6. The SWMS matrix, hold points, and risk register must crosswalk cleanly.
7. The risk register must be package-led, sequence-aware, and useful as a benchmark backbone.
8. Hold points must distinguish:
   - WHS-critical no-go points
   - QA / authority / approval gates
9. Controls must be practical benchmark controls, not generic compliance language.
10. Preserve visible uncertainty and open-item honesty.
11. Do not present the draft as dependable package-level issue output unless the evidence truly supports that.

PROJECT SELF-REVIEW:
Before finalising, check:
- Does the package structure reflect the source scope?
- Are package boundaries credible?
- Is HRCW mapped tightly enough to packages?
- Do hold points actually match package flow?
- Is the risk register sequence-based and package-linked?
- Does the package -> HRCW -> hold point -> risk crosswalk make sense?
- Where would trust drop?
- What would stop a consultant relying on this as a benchmark draft?

If trust would drop, revise before final output.

DECISION RULE:
Prefer a tighter, more honest benchmark draft with visible provisional items over a fuller but overconfident combined document.
"""
