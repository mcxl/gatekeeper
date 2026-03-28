# What To Use When Flowchart
**Visual Guide for Safe Method Quality Work**
Version: 2026-03-28

---

## Purpose

This flowchart turns the Safe Method quality-system docs into a quick visual path.

Use it when you want to decide:
- which document to open
- which workflow to run
- whether to use benchmark mode, multi-agent mode, automation work, or the SWMS Review Engine setup

---

## Flowchart

```mermaid
flowchart TD
    A["Start Here"] --> B{"What are you trying to do?"}

    B -->|Understand the whole system| C["Open QUALITY_SYSTEM_INDEX.md"]
    B -->|Check current benchmark priority| D["Open BENCHMARK_GOVERNANCE_REGISTER.md"]
    B -->|Run one benchmark cycle| E["Open LBV_ONE_CYCLE_PLAYBOOK.md"]
    B -->|Run a multi-agent cycle| F["Open MULTI_AGENT_STARTER_PROMPT_PACK.md"]
    B -->|Build automation| G["Open LBV_FLYWHEEL_ARCHITECTURE.md<br/>Then use automation implementation prompt"]
    B -->|Start SWMS Review Engine mode| H["Open SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md"]
    B -->|Need draft vs benchmark vs issue-ready clarity| I["Open QUALITY_GOVERNANCE_NOTE.md"]
    B -->|Need to record a cycle result| J["Open REFINEMENT_DECISION_LOG_TEMPLATE.md"]
    B -->|Need to close a stream| K["Open BENCHMARK_CLOSE_OUT_TEMPLATE.md"]

    C --> L["Read IP_MAP.md<br/>Read QUALITY_GOVERNANCE_NOTE.md<br/>Read LBV_FLYWHEEL_ARCHITECTURE.md"]

    D --> M{"Is there an ACTIVE stream?"}
    M -->|Yes| N["Choose one stream only<br/>Use one main weakness only"]
    M -->|No, only HOLD/new mode| O["Check benchmark setup docs for that mode"]

    E --> P["Paste master governance prompt<br/>Then paste stream task prompt"]
    P --> Q["Run one clean cycle<br/>Record one decision"]

    F --> R["Use Writer -> Critic -> Classifier -> Fixer/Checker"]
    R --> S["Use launch checklist before starting"]
    S --> T["Use close-out checklist before finishing"]

    G --> U["Build issue-gate checks first<br/>Then benchmark regression checks"]
    U --> V["Validate on one benchmark stream before expanding"]

    H --> W["Use first benchmark asset checklist"]
    W --> X["Choose one PC risk register + one subcontractor SWMS"]
    X --> Y["Fill first benchmark expectation note"]
    Y --> Z["Move stream from HOLD to ACTIVE"]

    N --> E
    O --> H

    Q --> AA{"What is the next step?"}
    AA -->|Another internal cycle| D
    AA -->|External review| AB["Use Aussie WHS evaluation prompt"]
    AA -->|Close benchmark stream| K

    T --> AA
```

---

## Short Use Guide

### If you are unsure where to start

1. Open [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)
2. Pick one active stream
3. Open [MULTI_AGENT_STARTER_PROMPT_PACK.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_STARTER_PROMPT_PACK.md)
4. Run one clean cycle

### If there is no active stream

1. Open the relevant benchmark setup doc
2. gather the first benchmark assets
3. define the first expectation note
4. activate the stream

### If the next step is not clear

Open [WHAT_TO_USE_WHEN.md](C:\Users\AlanRichardson\gatekeeper\docs\WHAT_TO_USE_WHEN.md)

---

## Related Documents

- [WHAT_TO_USE_WHEN.md](C:\Users\AlanRichardson\gatekeeper\docs\WHAT_TO_USE_WHEN.md)
- [QUALITY_SYSTEM_INDEX.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_SYSTEM_INDEX.md)
- [MULTI_AGENT_STARTER_PROMPT_PACK.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_STARTER_PROMPT_PACK.md)
- [SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md)

