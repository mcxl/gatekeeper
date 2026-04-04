# Job States Schema — Stage 2 Metadata Fields

## Extraction metadata

| Field | Type | Description |
|-------|------|-------------|
| extraction_char_count | int | Total characters extracted from PDF |
| extraction_page_count | int | Number of pages in PDF |
| chars_per_page | float | Average characters per page |
| confidence_tier | green / amber / red | Extraction quality routing decision |
| vision_audit_triggered | bool | Whether Haiku vision audit ran |
| vision_audit_result | legible / illegible / null | Vision audit outcome |
| dis_score | float / null | Document integrity score (reserved) |
| failure_reason | platform_timeout / fetch_error / vision_abort / logic_breach / null | Terminal failure category |

## Confidence routing

- **green**: all pages >= 1200 chars AND no critical page flags → direct to Sonnet
- **amber**: any page < 1200 chars OR any critical page flag → Haiku vision audit first 2 pages
- **red**: vision audit returns illegible → abort, manual review required

## Job states

| State | Meaning |
|-------|---------|
| received | Webhook accepted, queued for processing |
| processing | PDF fetch + extraction + review in progress |
| complete | Review finished, comments posted |
| failed | Terminal failure (see failure_reason) |
| failed_orphaned | Processing exceeded 150s, cleaned up by orphan monitor |
| timed_out_soft | 120s timeout reached, processing may still be alive |
