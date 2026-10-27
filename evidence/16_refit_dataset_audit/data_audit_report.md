# REFIT Task 1 Dataset Audit

## Scope

This report audits only checksum-verified files locally available from the official Zenodo REFIT cleaned record 5063428. It does not claim to audit the full 20-house University of Strathclyde archive.

- Official record: https://zenodo.org/records/5063428
- DOI: https://doi.org/10.5281/zenodo.5063428
- Official University landing page: https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/
- Locally checksum-verified files: 5/5
- Official-record files unavailable locally: CLEAN_House5.csv
- Selected replay-quality households: 5

## Selection rule

A household is eligible only when at least one exact 14-day window has observed nominal-slot coverage >= 90% (capped at 100% because timestamps may jitter), estimated missing-slot fraction <= 10%, maximum observed gap <= 3600 seconds, and native-cadence share >= 90%, where native cadence means an observed interval within +/-1 second of 8 seconds. These are pre-registered data-quality gates; no model result was used.

## Interpretation constraints

- The source files are the cleaned REFIT release. Duplicate merging, short-gap forward filling, and long-gap zeroing are upstream transformations documented by the source publisher. This audit does not present their post-cleaning completeness as raw-data quality.
- The full University archive and the official REFIT anomaly CSV could not be retrieved programmatically because the official file endpoints presented Cloudflare bot verification. No unofficial mirror was substituted.
- The source CSV `Issues` field was counted for traceability, but its semantics have not been inferred and it is not treated as an anomaly label.
- Therefore raw-versus-cleaned change rates, official anomaly-label schema, label-to-aggregate alignment, and true anomaly counts are NOT VERIFIED — DO NOT CLAIM IN PAPER.
- Aggregate measurements are Watts. No energy conversion, imputation, row removal, anomaly injection, replay, model training, or alert testing was performed by this Task 1 script.

## Table 1A — Household selection

`Estimated missing-slot percentage` and major gaps describe the full cleaned-source span; they are not a claim about the selected 14-day replay window.

| Household | Duration (calendar days) | Records | Observed interval | Estimated missing slots (full span) | Duplicate % | Major gap statistics | Selected/Rejected | Reason |
|---:|---:|---:|---|---:|---:|---|---|---|
| 1 | 638.95 | 6960008 | nominal 8 s; median 7 s, p95 14 s | 23.81% | 0.000000% | >1 h: 26; max: 3594413 s | SELECTED | Checksum-valid; at least one 14-day window passed all gates. |
| 2 | 617.41 | 5733526 | nominal 8 s; median 7 s, p95 14 s | 32.04% | 0.000000% | >1 h: 81; max: 5358903 s | SELECTED | Checksum-valid; at least one 14-day window passed all gates. |
| 3 | 614.65 | 6994594 | nominal 8 s; median 7 s, p95 14 s | 21.20% | 0.000000% | >1 h: 21; max: 3594416 s | SELECTED | Checksum-valid; at least one 14-day window passed all gates. |
| 4 | 633.98 | 6760511 | nominal 8 s; median 7 s, p95 14 s | 24.10% | 0.000000% | >1 h: 221; max: 1215817 s | SELECTED | Checksum-valid; at least one 14-day window passed all gates. |
| 11 | 392.15 | 4431541 | nominal 8 s; median 7 s, p95 11 s | 13.46% | 0.000000% | >1 h: 15; max: 887146 s | SELECTED | Checksum-valid; at least one 14-day window passed all gates. |

## Next required action

Task 2 must first decide and document the energy-normalisation policy from aggregate active power in Watts using actual inter-sample intervals. It must not assume an eight-second interval across gaps. The official anomaly CSV must be obtained and schema-inspected before any genuine-label ML evaluation is claimed.
