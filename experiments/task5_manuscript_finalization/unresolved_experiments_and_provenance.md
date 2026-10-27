# Unresolved experiments and data-provenance issues

## Critical before a strong journal-performance claim

| Priority | Unresolved issue | Why it matters | Minimum evidence required |
| --- | --- | --- | --- |
| 1 | Isolated device and identity provisioning | REFIT H1/H2/H4 must not be mapped to existing device IDs merely by matching numbers; each household needs one authorised device and unique non-production credential. | Approved isolated Keycloak realm, three test profiles, three aggregate-meter devices, device-token association checks, and redacted provisioning evidence. |
| 2 | Ingestion contract and unit reconciliation | The project must not send watts where `energyConsumed` expects kWh, or double-convert interval energy. | Static contract confirmation, adapter/payload validation, and a pilot reconciliation from submitted request through accepted/persisted event. |
| 3 | Safe isolated deployment | Current host memory prevents simultaneous main and isolated stacks; unplanned concurrent deployment risks instability and data contamination. | Human-approved maintenance/recovery plan, isolated volumes/networks, verified backup/rollback plan, capacity gate, and deployment-only smoke test. |
| 4 | Pilot REFIT replay | A full historical replay must not begin before authentication, schema, timestamp, and unit behavior are validated. | Dry run, bounded pilot, request/event/persistence reconciliation, rejected/ambiguous-request log, and clean stop criteria. |
| 5 | Full H1/H2/H4 replay | The primary cohort is prepared but has not passed an end-to-end path. | Pilot approval, chronological three-house execution logs, storage reconciliation, and isolation evidence. |
| 6 | Aggregate anomaly ground truth | Existing official annotation evidence is appliance-level and does not yet establish aggregate labels for the H1/H2/H4 cohort. | Retrieved official annotation schema, verified timestamp alignment, explicit aggregation policy, label counts, and provenance review. |
| 7 | ML feature compatibility | The legacy model uses weather/context fields and `Avg_Past_Consumption`, but REFIT aggregate artifacts do not provide a verified equivalent feature contract. | Approved, causal feature mapping; no silent imputation of a research evaluation feature; retraining/evaluation protocol if the model changes. |
| 8 | REFIT anomaly-accuracy evaluation | There is no valid REFIT accuracy metric until labels and feature protocol are established. | Pre-registered split, label provenance, baseline comparators, household-held-out/temporal test, and reported uncertainty. |
| 9 | Alert-deduplication under REFIT replay | Configured deduplication has historical local evidence only and no REFIT replay evidence. | Pilot/final test logs with controlled duplicate scenarios, persistence checks, delivery records, and false-suppression analysis. |
| 10 | Performance, recovery, and fault behavior | Historical local checks do not establish current isolated behavior. | Repeated throughput/latency runs, Kafka/DB failure tests, recovery/ordering checks, resource measurements, and stated hardware conditions. |

## Data-provenance limitations that remain in the manuscript

1. The legacy `smart_meter_data.csv` has no verified external source, licence, physical-unit description, household/device identity, label-generation method, or causal construction of `Avg_Past_Consumption`.
2. The legacy classifier's numerical results therefore remain a reproducible, dataset-specific artifact result rather than a real-household benchmark.
3. REFIT cleaned data are publisher-cleaned. The quality gates characterize the selected cleaned release, not raw sensor quality.
4. REFIT `Aggregate` is active power in watts. The documented energy field is a numerical sample-hold estimate; the source's point-sample versus interval-average semantics remain unresolved.
5. The source `Time` field is retained verbatim. UTC output strings were derived from `Unix` and do not resolve the human-readable timestamp's timezone convention.
6. H3/H11 have a documented solar-generation interference caveat and are not corrected to net import or pure consumption.
7. Official anomaly annotation file schema, counts, timestamps, and alignment remain unverified because the official file endpoint was unavailable during source audit.

## Experiments intentionally not claimed as completed

- REFIT ingestion through the live API
- REFIT device-token authorization
- REFIT Kafka, database, alert, or notification processing
- REFIT anomaly labels, anomaly probability distributions, or accuracy metrics
- REFIT-based deduplication, throughput, latency, recovery, or fault-test results
- Isolated Keycloak realm/device creation, database initialization, or isolated Docker deployment
- Production security, production resilience, or physical-meter accuracy

## Evidence needed before journal-submission reconsideration

An appropriately scoped journal submission would require a documented real-data experiment with source/licence traceability, a verified energy/feature contract, isolation from existing data, pilot reconciliation, end-to-end logs, a valid anomaly-label protocol, pre-registered household/temporal evaluation, comparators, and repeated systems measurements. Until then, the paper should be described as a transparent prototype and reproducibility study.
