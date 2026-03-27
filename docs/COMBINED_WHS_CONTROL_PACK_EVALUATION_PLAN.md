# Combined WHS Control Pack — Internal Evaluation Plan

## Status: Ready for evaluation

---

## 1. Purpose

### What we are trying to learn

Whether the Combined WHS Control Pack prototype produces output that a WHS consultant would recognise as a useful first draft — structured enough to review and refine, not just a data dump.

Specifically:
- Does the output save meaningful time compared to assembling the same document manually?
- Are trade packages extracted accurately enough that confirmation is faster than starting from scratch?
- Is the HRCW register, SWMS matrix, hold point schedule, and risk register useful as a combined document?
- Where does the consultant stop trusting the output?

### What decision this evaluation supports

Whether to:
- **Continue and refine** — invest in polishing the renderer, extraction, and review flow
- **Narrow scope** — keep only the highest-value sections, cut the rest
- **Pause/defer** — the product mode is not yet worth the investment

---

## 2. Who Should Evaluate

### Intended evaluator profile

- WHS consultant or safety manager who has manually prepared project-level WHS documentation
- Familiar with HRCW registers, SWMS requirements, and hold point schedules
- Has reviewed or authored real project risk assessments for multi-trade construction
- Can judge whether output is credible, not just whether it looks professional

### Who should NOT be the main evaluator

- Developers (too close to the build to judge usefulness)
- Non-construction reviewers (can judge format but not content)
- Junior staff without experience preparing project-level WHS documents (cannot assess whether content is correct)

---

## 3. Suggested Test Cases

### Case 1: Withers Road (civil infrastructure benchmark)

**Input:**
"Partial upgrade of Withers Road, North Kellyville NSW — approximately 400 metres of live lane road works, Sydney Water asset relocation, conversion from chip seal to 4 lanes, T-intersection with traffic lights, pedestrian walkways, and stormwater works"

**Expected strengths:** Multiple trade packages, HRCW register should be strong, civil hold points should be present.

**Compare against:** SD Group Withers Road WHS Control Document Rev01.

---

### Case 2: Facade remedial (building/remedial multi-trade)

**Input:**
"External facade remedial works to a 12-storey occupied residential strata building in Sydney — scaffold access, concrete spalling repair, protective coating application, balcony waterproofing. Principal contractor: ABC Constructions. Client: Strata Plan 12345."

**Expected strengths:** WAH HRCW, scaffold trade package, occupied building context, silica controls.

**Compare against:** What a consultant would prepare for an occupied strata remedial job.

---

### Case 3: Data centre fit-out (services-heavy)

**Input:**
"Installing a data centre into an existing industrial warehouse (concrete tilt-up construction) in NSW — electrical distribution, UPS and battery systems, HVAC and precision cooling, fire suppression, raised floor, cable management"

**Expected strengths:** Electrical HRCW, multiple services trade packages, existing building context, fit-out classification.

**Compare against:** What a consultant would prepare for a data centre fit-out.

---

### Case 4: Ambiguous scope (trade package extraction challenge)

**Input:**
"Road and drainage upgrade works including associated services adjustments"

**Expected result:** Fewer trade packages confidently identified. More open items. System should be honest about limited information rather than over-generating.

**What to assess:** Does the system produce a useful document even with sparse input? Does it flag what's missing?

---

## 4. Evaluation Scorecard

For each test case, score the following on a 1-5 scale:

| # | Criterion | 1 (Poor) | 3 (Acceptable) | 5 (Strong) | Score | Comments |
|---|-----------|----------|-----------------|------------|-------|----------|
| 1 | **Output usefulness** — would I use this as a starting point? | Would start from scratch | Would use with major edits | Would use with minor edits | | |
| 2 | **Time saved** — how much faster than manual? | No time saved | Saves 1-2 hours | Saves half a day or more | | |
| 3 | **Trade package extraction** — were the right packages identified? | Mostly wrong | About half right | Almost all correct | | |
| 4 | **HRCW register quality** — YES/CONDITIONAL/NO accurate? | Many wrong calls | Mostly correct, some gaps | Accurate and honest | | |
| 5 | **Hold point usefulness** — conditions and authorisation sensible? | Generic or irrelevant | Reasonable but need editing | Project-specific and usable | | |
| 6 | **Risk register relevance** — hazards match the scope? | Mostly irrelevant | Relevant but generic | Specific to the project | | |
| 7 | **Risk register depth** — one-line controls appropriate? | Too shallow to be useful | About right for project-level | Good balance of detail | | |
| 8 | **Document structure** — does the combined shape work? | Confusing or redundant | Logical but could improve | Clear and professional | | |
| 9 | **Reviewability** — could I review and issue with amendments? | Would need complete rewrite | Needs significant amendment | Minor amendments only | | |
| 10 | **Open items honesty** — does it flag what's missing? | Overstates certainty | Flags some gaps | Clearly shows what needs confirmation | | |
| 11 | **Trust** — do I trust the content enough to put my name on it? | No — too many errors | Conditionally — after checking | Yes — with normal review | | |
| 12 | **Continue as product?** — should this mode be developed further? | No — not useful enough | Maybe — needs specific fixes | Yes — clear value | | |

### Overall assessment (free text):

**What was most useful?**

**What was least useful or actively misleading?**

**What would make you use this regularly?**

**What would make you stop using it?**

---

## 5. Key Questions to Answer

After completing all test cases, the evaluator should answer:

1. **Does this save enough time to matter?** If the answer is "I could do this myself in 30 minutes", the value proposition is weak. If the answer is "this would take me half a day", the value is strong.

2. **Are consultants comfortable confirming extracted trade packages?** Or do they feel the extraction step is more work than just typing them?

3. **Is the grouped risk register too shallow, too deep, or about right?** The benchmark uses one-line summary controls — is that sufficient for project-level use?

4. **Does the combined document shape feel more useful than separate RA + SWMS outputs?** Or would the consultant prefer to generate them independently?

5. **Where does trust drop?** Which section causes the most concern? Which section is the most reliable?

6. **Would you send this to a principal contractor as a draft for review?** This is the real product test — not "is it correct" but "would you put it in front of a client?"

---

## 6. Decision Outcomes

### Continue and refine (score average >= 3.5)
- Most criteria score 3 or above
- Time saved is material (2+ hours)
- Evaluator says "yes, continue" or "yes, with specific fixes"
- Proceed to: renderer polish, extraction improvement, review workflow

### Narrow scope (score average 2.5–3.5)
- Some sections are useful, others are not
- Trade package extraction needs significant improvement
- Risk register depth needs adjustment
- Proceed to: identify which sections to keep, cut or rework the rest

### Pause/defer (score average < 2.5)
- Output is not useful enough to justify further investment
- Consultants would not use it as a starting point
- The combined shape does not add value over separate documents
- Proceed to: park the product mode, focus on standalone SWMS and RA improvements

---

## 7. Recommended Evaluation Process

### Setup
1. Deploy the prototype to the live Railway environment (already deployed)
2. Prepare the 4 test case descriptions for copy-paste
3. Have the Withers Road benchmark document available for side-by-side comparison

### Evaluators
- Minimum: 1 experienced WHS consultant
- Ideal: 2-3 consultants with different project-type experience (civil, building, services)

### Per evaluator
1. Run all 4 test cases through the prototype
2. Download each .docx and review in Word
3. Complete the scorecard for each case
4. Answer the 6 key questions
5. Write free-text comments on each case

### Comparison
- Case 1 (Withers Road): compare directly to the benchmark document
- Cases 2-4: compare to what the consultant would produce manually

### Time estimate
- 30 minutes per case (including generation + review)
- 30 minutes for overall assessment
- Total: approximately 2.5 hours per evaluator

### Feedback capture
- Scorecard completed in writing (paper or digital)
- Free-text comments captured
- If possible, screen-record the evaluation session for later review

---

## 8. After Evaluation

Compile results and answer:

1. Is the product mode worth continuing? (Continue / Narrow / Pause)
2. If continuing: what are the top 3 fixes before the next evaluation?
3. If narrowing: which sections should be kept vs cut?
4. If pausing: what would need to change before revisiting?

Document the decision in `docs/COMBINED_WHS_CONTROL_PACK_DECISION.md` after evaluation is complete.
