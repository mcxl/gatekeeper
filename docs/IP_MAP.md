# Safe Method IP Map
**One-Page Intellectual Property View**
Version: 2026-03-28

---

## Purpose

This document gives a one-page view of the main IP layers inside Safe Method.

It is designed to clarify:
- what the methodology IP is
- what the product/process IP is
- what the benchmark asset IP is
- what the implementation/product IP is

It should be used as a simple reference for product planning, collaboration, and commercial explanation.

---

## 1. Methodology IP

This is the core reasoning method behind quality improvement.

### Includes
- Layered Benchmark Validation (LBV)
- benchmark-first improvement logic
- layered diagnosis of failure:
  - classification
  - context
  - hazard family selection
  - confidence
  - grouping
  - control language
  - structure
  - renderer polish
- stop rules:
  - stop when benchmark is materially satisfied
  - stop when the next gap is architectural rather than incremental
- draft vs issue-ready distinction

### Value
- defines how output quality is improved systematically
- reduces blind prompt tweaking
- creates a repeatable method for turning weak output into stronger output

### Type of IP
- process IP
- methodology IP

---

## 2. Product / Process IP

This is the operating logic that turns the methodology into a repeatable system.

### Includes
- LBV flywheel architecture
- issue-gating model:
  - `FAIL_INTERNAL`
  - `REVIEW_INTERNAL`
  - `ESCALATE_TO_EXPERT_REVIEW`
- finding taxonomy:
  - reusable rule
  - case-specific fix
  - product decision
  - defer
- three separate flywheels:
  - SWMS
  - RA
  - Project WHS benchmark / control pack
- product-boundary rules:
  - standalone SWMS
  - standalone RA
  - combined WHS control pack
- stop/go/narrow/defer decision logic

### Value
- prevents chaotic refinement
- preserves product boundaries
- reduces wasted expert-review time
- makes quality improvement operational rather than ad hoc

### Type of IP
- process IP
- product-operating IP

---

## 3. Benchmark Asset IP

This is the benchmark library and proof base that makes the methodology useful and defensible.

### Includes
- benchmark cases
- benchmark close-outs
- reference job library
- benchmark prompts and benchmark comparison notes
- case studies and proof notes
- benchmark-specific evaluation criteria

### Current examples
- RA benchmark: data centre retrofit
- SWMS benchmark: facade remedial works
- SWMS benchmark: EWP roof transfer
- RA benchmark: Withers Road civil infrastructure
- project/control-pack benchmark: Withers Road combined WHS control document

### Value
- defines what “good” looks like
- provides proof that the method works
- creates reusable quality references
- supports regression protection and future product decisions

### Type of IP
- benchmark asset IP
- knowledge asset IP
- evaluation asset IP

---

## 4. Implementation / Product IP

This is the actual implemented system that turns the methodology and benchmark rules into working product behavior.

### Includes
- SWMS generation pipeline
- RA generation pipeline
- control-pack prototype pipeline
- inference matrix and classification logic
- post-processing injection rules
- review workflows
- renderers and document contracts
- templates and render contracts
- test suites and regression harnesses
- frontend flows and download/review behavior

### Examples
- SWMS orchestrator and renderer logic
- RA renderer and HRCW tri-state handling
- control-pack data layer, renderer, backend route, and prototype frontend
- evaluation harnesses and benchmark tests

### Value
- creates actual working output
- turns the method into a usable product
- supports deployment, user testing, and product iteration

### Type of IP
- software IP
- implementation IP
- product IP

---

## 5. How The Layers Fit Together

The layers build on each other:

1. **Methodology IP**
The core improvement method

2. **Product / Process IP**
The operating model for running the method repeatedly

3. **Benchmark Asset IP**
The reference set that tells the system what quality looks like

4. **Implementation / Product IP**
The code, flows, renderers, and test harnesses that produce real outputs

In short:

- methodology tells us **how to improve**
- process tells us **how to run that repeatedly**
- benchmarks tell us **what good looks like**
- implementation turns it into **working product behavior**

---

## 6. Why This Matters

Safe Method is not just code.
Its value comes from the interaction of:
- a defined improvement methodology
- a repeatable operating system
- a benchmark/proof library
- implemented product behavior

That combination is more defensible than any one part on its own.

---

## 7. Practical Use

Use this IP map when explaining Safe Method to:
- internal team members
- Claude Code / implementation agents
- collaborators
- evaluators and reviewers
- investors
- commercial partners

It is especially useful when explaining that:
- the IP is not just prompts
- the value is not just software
- the benchmark library and operating model matter as much as the code

---

## 8. Plain-English Summary

Safe Method IP has four layers:

1. **Methodology IP**
How quality is improved

2. **Product / Process IP**
How that method is run repeatedly

3. **Benchmark Asset IP**
What “good” looks like

4. **Implementation / Product IP**
The working system that produces outputs

All four together are the real asset.
