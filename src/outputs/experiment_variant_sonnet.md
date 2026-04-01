# Batch Comparison Report -- 2026-04-01T22:00:29Z

**Jobs:** 5/5 completed | **Zero-FAIL:** 2 | **Avg gate FAIL:** 0.8 | **Avg gate REVIEW:** 4.0 | **Concurrency:** 2

| # | Brief | Customer | Type | Tasks | Validator | Gate F | Gate R | CW Cost | Time | Notable |
|---|-------|----------|------|-------|-----------|--------|--------|---------|------|---------|
| 1 | c06_rope_access_painti | mcxi.co | maintenance | 10 | ESCALATE_EXTERNAL | 0 | 4 | $0.049 | 291.7s | clean |
| 2 | c08_podium_slab | Apex Commerc | new_build | 11 | RETRY_INTERNAL | 1 | 6 | $0.049 | 259.0s | ccvs_completeness: Tasks with hazards... |
| 3 | urban_flow_plumbing | Urban Flow P | new_build | 12 | RETRY_INTERNAL | 2 | 4 | $0.053 | 363.9s | ccvs_coverage: Tasks without monitori... |
| 4 | c10_stack_replacement | Harbourline  | remedial | 12 | RETRY_INTERNAL | 1 | 3 | $0.053 | 334.1s | unsupported_controls: 1.3:membrane; 1... |
| 5 | c11_directional_drilli | Precision Ut | civil | 12 | ESCALATE_EXTERNAL | 0 | 3 | $0.026 | 183.3s | clean |

## Summary

- Validator PASS_INTERNAL: 0
- Validator RETRY_INTERNAL: 3
- Validator ESCALATE_EXTERNAL: 2
- Total gate FAILs across all jobs: 4
- Total gate REVIEWs across all jobs: 20
- Most FAILs: urban_flow_plumbing
- Average time per job: 286.4s

## Control Writer Cost

- Jobs with cost data: 5
- Total input tokens: 55,118
- Total output tokens: 46,697
- Total estimated cost: $0.2309
- Avg cost per job: $0.0462
