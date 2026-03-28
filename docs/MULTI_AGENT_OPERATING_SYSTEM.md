# Safe Method Multi-Agent Operating System
**Clean Role Design for Benchmark-Led Improvement**
Version: 2026-03-28

---

## Purpose

This document defines the simplest multi-agent pattern that can improve Safe Method outputs without creating chaos.

The goal is:
- cleaner role separation
- faster benchmark cycles
- less prompt drift
- less role confusion
- clearer stop/go decisions

This pattern is designed to sit inside the LBV quality system, not replace it.

---

## Core Principle

Use separate agents for separate kinds of thinking.

Do not ask one agent to:
- write
- critique
- classify
- implement
- and decide stop rules

That is where role blur and low-quality iteration begin.

---

## Recommended Structure

### Minimum Working Team

Use 4 agents:
1. Writer
2. Critic
3. Classifier
4. Fixer / Checker

### Optional Fifth Role

Add a Coordinator only when the system becomes busy enough that:
- multiple benchmark streams are active
- stop rules are getting missed
- stream priority is changing often

If there is only one active stream being worked cleanly, the coordinator role can stay with the main operator.

---

## Role Card

## 1. Writer

### Job

Write the strongest draft the source material can honestly support.

### Focus

- source fidelity
- real work sequence
- actual hazards
- usable controls
- visible uncertainty where needed

### Must Do

- stay close to source material
- reflect the actual likely method
- distinguish:
  - confirmed scope
  - likely assumptions
  - latent conditions
  - open items
- prefer a narrower, truer draft over a broader speculative draft

### Must Not Do

- invent unsupported scope
- invent permits, approvals, plant, or access methods
- invent HRCW triggers
- fill gaps with generic boilerplate

### Success Test

The draft is believable, source-led, and useful without pretending more certainty than exists.

---

## 2. Critic

### Job

Review the draft like a tough consultant and identify where trust drops.

### Focus

- unsupported content
- missing source translation
- wrong sequence
- generic boilerplate
- weak controls
- weak hold points
- issue blockers

### Must Do

- compare the draft to the source
- identify what is missing, collapsed, invented, or overcalled
- identify issue stoppers first
- say where a consultant would stop trusting the draft

### Must Not Do

- rewrite the whole draft
- jump into implementation
- focus on cosmetic issues before structural ones

### Success Test

The real trust failures are obvious and prioritised.

---

## 3. Classifier

### Job

Decide what kind of problem each finding is and what layer should fix it.

### Focus

- reusable rule vs case-specific fix
- issue-gate candidate vs benchmark gap
- prompt behaviour vs deterministic logic vs governance

### Must Do

- classify each finding as:
  - reusable rule
  - case-specific fix
  - issue-gate candidate
  - benchmark-quality gap
  - issue-ready blocker
- decide the likely fix layer:
  - prompt / agent behaviour
  - deterministic code / rule
  - source-input requirement
  - benchmark / governance process

### Must Not Do

- treat every finding as reusable
- blur benchmark-quality and issue-ready
- jump straight into code changes

### Success Test

The team knows what kind of fix is needed before anyone starts building.

---

## 4. Fixer / Checker

### Job

Apply the smallest safe fix for the main weakness, then verify whether it worked.

### Focus

- one main weakness
- narrowest effective fix
- regression safety
- end-of-cycle decision

### Must Do

- choose one main weakness only
- prefer deterministic fixes where prompt-only behaviour is fragile
- rerun generation/tests/checks after the fix
- ask whether any previously closed or stable stream might regress
- end the cycle with one decision:
  - continue and refine
  - narrow scope
  - pause/defer
  - close benchmark stream

### Must Not Do

- change everything at once
- keep iterating without a decision
- overfit one benchmark case
- ignore regression risk

### Success Test

One weakness improves, regressions are controlled, and the cycle ends clearly.

---

## 5. Optional Coordinator

### Job

Own stream selection, priority, and stop-rule discipline.

### Focus

- which stream is active
- what the current weakest point is
- whether the cycle should continue, hold, or close

### Use This Role When

- multiple streams compete for attention
- the team starts looping too long
- priority drift is happening

### Success Test

Only one real benchmark cycle is active at a time and stop rules are respected.

---

## Workflow

One clean cycle should run like this:

1. Coordinator/main operator selects one benchmark stream
2. Writer produces or regenerates the draft
3. Critic identifies trust failures
4. Classifier sorts findings and identifies the right fix layer
5. Fixer / Checker applies one narrow fix and verifies it
6. Main operator or coordinator makes the end-of-cycle decision
7. Decision log is updated

---

## Handoff Rules

Each role should hand off a short structured result.

### Writer Handoff

- source used
- output produced
- main assumptions
- open items / uncertainties

### Critic Handoff

- top trust failures
- top issue blockers
- what remains strong

### Classifier Handoff

- reusable rules
- case-specific fixes
- issue-gate candidates
- likely fix layer

### Fixer / Checker Handoff

- exact fix applied
- tests / checks run
- whether output improved
- regressions found or not
- end-of-cycle recommendation

---

## Stop Rules

Stop the cycle when:
- the benchmark is materially satisfied
- the next gap is architectural, not incremental
- the next change would create product-boundary confusion
- the loop is becoming low-value churn
- the next right step is external review, not more internal guessing

Do not let multi-agent work turn into endless self-conversation.

---

## Product-Boundary Rules

### SWMS

Focus on:
- task sequence
- method fidelity
- controls
- hold points
- stop-work triggers
- issue-ready blockers

### RA

Focus on:
- classification
- hazard-family relevance
- HRCW tri-state logic
- grouped risk logic
- benchmark usefulness

### Project WHS Benchmark / Control Pack

Focus on:
- package extraction
- HRCW/package mapping
- crosswalk between sections
- hold point quality
- benchmark risk register usefulness

Do not let one product mode drag another mode into the wrong standard.

---

## When to Use Multi-Agent Mode

Use it when:
- a benchmark stream is active
- the output exists and needs structured refinement
- one person/agent is starting to blur too many roles
- the current problem needs separation between critique and implementation

Do not use it for:
- trivial one-off edits
- casual brainstorming
- tasks with no benchmark or no review loop

---

## Prompt Templates

## Writer Template

```text
Act as the Writer.

Your job is to produce the strongest draft the source material can honestly support.

Focus on:
- source fidelity
- real work sequence
- actual hazards and controls
- visible uncertainty where facts are not confirmed

Do not invent unsupported scope, permits, plant, access methods, or HRCW triggers.
Prefer a narrower truthful draft over a broader speculative one.

At the end, report:
1. output produced
2. main assumptions
3. open items / uncertainties
```

## Critic Template

```text
Act as the Critic.

Review the draft like a blunt Australian WHS consultant.
Compare it directly against the source materials.

Focus on:
- unsupported content
- missing source translation
- wrong sequence
- generic boilerplate
- weak controls
- issue blockers
- where trust drops

Do not rewrite the draft.
Do not focus on cosmetic issues before structural ones.

At the end, report:
1. top trust failures
2. top issue blockers
3. what remains strong
```

## Classifier Template

```text
Act as the Classifier.

Your job is to classify the Critic's findings and decide what layer should fix them.

Classify each finding as:
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

## Fixer / Checker Template

```text
Act as the Fixer / Checker.

Your job is to apply the smallest safe fix for the single highest-priority weakness, then verify the result.

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

## Minimal Starting Pattern

If keeping it very simple, use:

1. Writer
2. Critic
3. Fixer / Checker

Add the Classifier when findings are becoming mixed or harder to sort.
Add the Coordinator when multiple streams are active.

---

## Plain-English Summary

This system works cleanly when:
- one role writes
- one role criticises
- one role decides what kind of problem it is
- one role fixes and checks

That separation is what keeps the quality loop efficient instead of messy.

---

## Related Documents

- [LBV_FLYWHEEL_ARCHITECTURE.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md)
- [LBV_ONE_CYCLE_PLAYBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)
- [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)

