# Multi-Agent Starter Prompt Pack
**Ready-to-Use Prompt Sequence for Claude Code**
Version: 2026-03-28

---

## Purpose

This document gives the minimum prompt set needed to run the Safe Method multi-agent pattern in Claude Code without assembling prompts manually each time.

Use this when:
- one benchmark stream is active
- you want a clean cycle
- you want role separation without overcomplicating the session

---

## 1. Master Governance Prompt

Paste this first at the start of a serious Claude Code session:

```text
Use the Safe Method quality-system docs as the operating method for this work.

Before doing anything substantial, read and follow these documents:
- C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_SYSTEM_INDEX.md
- C:\Users\AlanRichardson\gatekeeper\docs\IP_MAP.md
- C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md
- C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md
- C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md
- C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md
- C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_OPERATING_SYSTEM.md
- C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_CLAUDE_CODE_RUNBOOK.md
- C:\Users\AlanRichardson\gatekeeper\docs\REFINEMENT_DECISION_LOG_TEMPLATE.md
- C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_CLOSE_OUT_TEMPLATE.md

Operating rules:
1. Respect product boundaries between SWMS, RA, and Project WHS benchmark/control pack.
2. Do not assume benchmark-quality means issue-ready.
3. Use one benchmark stream and one main weakness per cycle.
4. Prefer narrow, benchmark-led, regression-safe improvements.
5. Update the decision log if a full cycle is completed.
6. Update the governance register if stream status or weakest point changes.

At the end of the task, report:
1. product mode
2. benchmark stream
3. weakest point addressed
4. work completed
5. end-of-cycle decision
6. whether the decision log or close-out template should now be updated
```

---

## 2. Stream Launch Prompt

Paste this second, filling in the placeholders:

```text
Run one clean multi-agent benchmark cycle for this stream.

Product mode:
[PASTE MODE]

Benchmark stream:
[PASTE STREAM]

Current weakest point:
[PASTE CURRENT WEAKEST POINT]

Source files / benchmark materials:
[PASTE FILE PATHS]

Cycle goal:
[PASTE GOAL]

Use the multi-agent pattern in this order:
1. Writer
2. Critic
3. Classifier
4. Fixer / Checker

Rules:
- keep the cycle narrow
- address one main weakness only
- do not broaden into unrelated streams
- stop if the next correct step is external review or architecture change
- update the decision log if a full cycle is completed

At the end, report:
1. writer result
2. critic result
3. classifier result
4. fixer/checker result
5. end-of-cycle decision
6. whether the governance register should be updated
```

---

## 3. Role Prompts

Use these if you want to force role separation explicitly.

### Writer

```text
Act as the Writer for this benchmark stream.

Produce or regenerate the strongest draft the source material can honestly support.

Stay tight to source material.
Do not invent unsupported scope, permits, plant, access methods, or HRCW triggers.
Prefer a narrower truthful draft over a broader speculative one.

At the end, report:
1. output produced
2. main assumptions
3. open items / uncertainties
```

### Critic

```text
Act as the Critic for this benchmark stream.

Review the current draft like a blunt Australian WHS consultant.
Compare it directly against the source materials.

Focus on:
- unsupported content
- missing source translation
- wrong sequence
- generic boilerplate
- weak controls
- issue blockers
- where trust drops

At the end, report:
1. top trust failures
2. top issue blockers
3. what remains strong
```

### Classifier

```text
Act as the Classifier for this benchmark stream.

Classify the Critic's findings into:
- reusable rule
- case-specific fix
- issue-gate candidate
- benchmark-quality gap
- issue-ready blocker

Also identify the likely fix layer:
- prompt / agent behaviour
- deterministic code / rule
- source-input requirement
- benchmark / governance process

At the end, report:
1. findings by category
2. likely fix layer for each major finding
3. the one highest-priority weakness for this cycle
```

### Fixer / Checker

```text
Act as the Fixer / Checker for this benchmark stream.

Apply the smallest safe fix for the single highest-priority weakness, then verify the result.

Focus on:
- one weakness only
- narrowest effective fix
- regression safety
- clear end-of-cycle decision

After the fix, rerun the necessary generation/tests/checks and report:
1. exact fix applied
2. whether output improved
3. whether any regression was found
4. end-of-cycle recommendation:
   - continue and refine
   - narrow scope
   - pause/defer
   - close benchmark stream
```

---

## 4. Simple Default Sequence

For most sessions:

1. paste the master governance prompt
2. paste the stream launch prompt
3. if Claude needs more role clarity, paste the role prompts one by one

That is usually enough.

---

## 5. When Not To Use This Pack

Do not use the full pack for:
- trivial one-off edits
- casual brainstorming
- tasks with no benchmark stream
- unrelated architectural work

---

## Related Documents

- [QUALITY_SYSTEM_INDEX.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_SYSTEM_INDEX.md)
- [MULTI_AGENT_OPERATING_SYSTEM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_OPERATING_SYSTEM.md)
- [MULTI_AGENT_CLAUDE_CODE_RUNBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_CLAUDE_CODE_RUNBOOK.md)
- [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)

