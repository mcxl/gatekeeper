# Multi-Agent Claude Code Runbook
**How to Use the Multi-Agent Pattern in Practice**
Version: 2026-03-28

---

## Purpose

This note explains how to use the Safe Method multi-agent pattern inside Claude Code without overcomplicating the workflow.

It connects:
- the operating system
- the workflow diagram
- the launch/close-out checklists
- the actual prompts used in a live session

---

## Core Principle

Do not start with a swarm.

Start with:
- one active benchmark stream
- one clear weakest point
- one clean cycle
- one role at a time

Claude Code can simulate the multi-agent pattern either by:
- role-based sequential prompting in one thread
- or separate agents/subtasks where helpful

For most Safe Method work, start with role-based sequential prompting first.

---

## Recommended Session Pattern

### Step 1. Load Governance

Start the session by loading the quality-system context.

Use:
- the master governance prompt

This ensures Claude Code:
- uses the benchmark register
- respects product boundaries
- reports in governance format

### Step 2. Launch One Stream

Use the launch checklist before starting.

Confirm:
- one benchmark stream
- one weakest point
- source files
- stop rule

### Step 3. Run the Roles in Order

For most cycles, the cleanest order is:

1. Writer
2. Critic
3. Classifier
4. Fixer / Checker

Only use the optional coordinator role when priorities or stop rules are becoming messy.

### Step 4. Close the Cycle Properly

Use the close-out checklist.

Confirm:
- one clear decision
- decision log updated if needed
- governance register updated if needed
- next step is explicit

---

## Two Practical Ways To Run It

## Option A — Single-Thread Role Prompting

Best for:
- most benchmark cycles
- lower complexity
- clean operator control

Pattern:
1. paste the master governance prompt
2. give Claude the stream/task prompt
3. explicitly tell Claude which role to perform next
4. move through the roles in one thread

Example:
- "Act as the Critic for the 18 Danks Street SWMS output..."
- "Now act as the Classifier for those findings..."
- "Now act as the Fixer / Checker and apply the narrowest safe fix..."

## Option B — Separate Agents / Subtasks

Best for:
- parallel non-overlapping work
- when role separation is already stable
- when analysis and implementation can safely split

Use separate agents only when:
- they are not fighting over the same files
- the ownership boundary is clear
- the main thread remains the coordinator

Do not start here unless the cycle is already well understood.

---

## Suggested Role Prompts

## Writer Prompt

```text
Act as the Writer for this benchmark stream.

Your job is to produce or regenerate the strongest draft the source material can honestly support.

Stay tight to source material.
Do not invent unsupported scope, permits, plant, access methods, or HRCW triggers.
Prefer a narrower truthful draft over a broader speculative one.

At the end, report:
1. output produced
2. main assumptions
3. open items / uncertainties
```

## Critic Prompt

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

## Classifier Prompt

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

## Fixer / Checker Prompt

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

## Best-Practice Rules

### 1. One Stream At a Time

Do not mix benchmark streams in one live cycle.

### 2. One Main Weakness At a Time

Do not ask the Fixer / Checker to solve multiple unrelated problems at once.

### 3. Stop At the Right Point

If the next step is:
- external review
- product decision
- architecture change

stop the cycle and record that clearly.

### 4. Use External Review Deliberately

Do not invoke expert review for defects that should have been caught by:
- issue gates
- benchmark regression
- deterministic checks

### 5. Preserve Product Boundaries

Do not let:
- SWMS expectations
- RA expectations
- Project/control-pack expectations

bleed into each other.

---

## Minimal Real-World Flow

For most Safe Method work, this is enough:

1. paste the master governance prompt
2. run one benchmark stream
3. use the writer role
4. use the critic role
5. use the classifier role if needed
6. use the fixer/checker role
7. update the decision log
8. update the governance register if needed

That is usually enough.

---

## Related Documents

- [MULTI_AGENT_OPERATING_SYSTEM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_OPERATING_SYSTEM.md)
- [MULTI_AGENT_WORKFLOW_DIAGRAM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_WORKFLOW_DIAGRAM.md)
- [MULTI_AGENT_LAUNCH_CHECKLIST.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_LAUNCH_CHECKLIST.md)
- [MULTI_AGENT_CLOSEOUT_CHECKLIST.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_CLOSEOUT_CHECKLIST.md)
- [LBV_ONE_CYCLE_PLAYBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md)

