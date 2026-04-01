# Batch Comparison Report -- 2026-04-01T21:33:23Z

**Jobs:** 5/5 completed | **Zero-FAIL:** 1 | **Avg gate FAIL:** 1.2 | **Avg gate REVIEW:** 4.4 | **Concurrency:** 2

| # | Brief | Customer | Type | Tasks | Validator | Gate F | Gate R | CW Cost | Time | Notable |
|---|-------|----------|------|-------|-----------|--------|--------|---------|------|---------|
| 1 | c06_rope_access_painti | mcxi.co | maintenance | 11 | RETRY_INTERNAL | 1 | 4 | $0.168 | 499.4s | ccvs_alignment: 1.7[WAH-H6]: task sug... |
| 2 | c08_podium_slab | Apex Commerc | new_build | 12 | RETRY_INTERNAL | 1 | 6 | $0.168 | 466.7s | ccvs_completeness: Tasks with hazards... |
| 3 | urban_flow_plumbing | Urban Flow P | new_build | 11 | RETRY_INTERNAL | 2 | 4 | $0.184 | 588.4s | ccvs_completeness: Tasks with hazards... |
| 4 | c10_stack_replacement | Harbourline  | remedial | 12 | RETRY_INTERNAL | 2 | 3 | $0.184 | 556.4s | no_coat_reinstate_merge: Merged: Rein... |
| 5 | c11_directional_drilli | Precision Ut | civil | 12 | ESCALATE_EXTERNAL | 0 | 5 | $0.083 | 250.3s | clean |

## Summary

- Validator PASS_INTERNAL: 0
- Validator RETRY_INTERNAL: 4
- Validator ESCALATE_EXTERNAL: 1
- Total gate FAILs across all jobs: 6
- Total gate REVIEWs across all jobs: 22
- Most FAILs: urban_flow_plumbing
- Average time per job: 472.2s

## Control Writer Cost

- Jobs with cost data: 5
- Total input tokens: 56,211
- Total output tokens: 185,514
- Total estimated cost: $0.7869
- Avg cost per job: $0.1574
