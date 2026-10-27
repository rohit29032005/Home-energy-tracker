# Task 3 — Frozen Experimental Protocol

## Status and scope

**Status:** protocol only; no replay, model training, anomaly generation, backend/Docker modification, device-token modification, or paper update was performed in Task 3.

This protocol governs a future experiment using the checksum-verified Task 2 REFIT artifacts. It is deliberately written before an execution stage so that data handling, cohort boundaries, measurement meaning, and acceptance conditions are defined independently of later outcomes.

The future study must be described as **historical household data replayed as a continuous live-like stream**. It must not be described as newly acquired real-time household data.

## 1. Verified Task 2 foundation

The authoritative Task 2 output is `experiments/refit_task2_energy_normalization/artifacts/`. Its manifest records checksum-verified input files, a deterministic configuration, and hashes of the generated outputs. The Task 2 verifier reports `verification: passed`. At this freeze point, the manifest records configuration SHA-256 `1cc71af477e9be668182fa1ed08a257c22d3060f93c13339081e18e3ec70e772` and preprocessor SHA-256 `f92fdcac5e00aa8e1a8f6f92417785053eb77159449f34699a7339b8bad1d4a5`.

| Cohort | Houses | Retained interval records | Role in this protocol |
|---|---:|---:|---|
| Primary | H1, H2, H4 | 468,847 | Main system-integration and any later primary analysis cohort |
| Solar sensitivity | H3, H11 | 326,340 | Separate sensitivity analysis only; never pooled into primary household-consumption claims |
| Excluded source observations | all selected houses | 536 | 531 cross-gap records and 5 end-of-window records; they are not replay candidates |

The selected source windows, recorded in `evidence/16_refit_dataset_audit/household_selection.csv`, are H1/H2/H3 from 2014-10-01 to 2014-10-15, H4 from 2015-04-22 to 2015-05-06, and H11 from 2015-04-17 to 2015-05-01. The difference in calendar periods is a reason to avoid describing relative multi-house replay as contemporaneous real-world observation.

### 1.1 Exact cleaned-data schema and semantics

Each Task 2 cleaned cohort CSV has these exact 21 columns:

```text
household_id, cohort, source_filename, source_row_number, original_time_text,
original_unix, timestamp_utc_from_unix, original_aggregate_power_w,
interval_end_source_row_number, interval_end_unix,
interval_end_timestamp_utc_from_unix, interval_end_aggregate_power_w,
interval_seconds, derived_interval_energy_kwh, energy_integration_method,
interval_classification, data_quality_flags, source_issues_raw,
source_issue_marked, solar_interference_documented, known_source_caveat
```

| Fields | Confirmed meaning | Protocol use |
|---|---|---|
| `household_id`, `cohort`, `source_filename`, `source_row_number` | Source identity and cohort assignment | Define the source-event identity and enforce cohort separation |
| `original_time_text`, `original_unix`, `timestamp_utc_from_unix` | Original textual time is retained verbatim. `Unix` is the canonical chronology, and UTC text is derived from `Unix`. | Sort source events by `original_unix`, then `source_row_number`; do not assert a timezone for `original_time_text` itself. |
| `original_aggregate_power_w` | Whole-house active power in W at the interval start. | Provenance only; never send raw W into the ingestion field called `energyConsumed`. |
| `interval_end_*`, `interval_seconds` | The following retained source observation and elapsed interval. | Reconstruct interval boundaries and validate chronological continuity. |
| `derived_interval_energy_kwh`, `energy_integration_method` | Estimated interval energy, computed as `interval-start aggregate W × interval seconds / 3,600,000` by the left-rectangle/sample-hold method. | Candidate value for a later replay adapter. It is an estimate, not a direct meter reading or cumulative meter value. |
| `interval_classification`, `data_quality_flags`, `source_issues_raw`, `source_issue_marked` | Cadence/source-quality context. `Issues` and IQR-related flags are not anomaly labels. | Preserve in the evidence ledger; do not convert them into truth labels or automatic anomalies. |
| `solar_interference_documented`, `known_source_caveat` | REFIT descriptor caveat attached to H3/H11. | Force H3/H11 into sensitivity-only reporting. |

The data retains enough information to reconstruct an ordered stream **within each household** from `(household_id, original_unix, source_row_number)` and to reconstruct the derived interval boundary. The cohort files are grouped by household rather than guaranteed globally ordered across households, so a future replay preparation step must sort explicitly. The files contain no backend `deviceId`, event ID, idempotency key, replay-wall-clock timestamp, ingestion timestamp, Kafka offset, Influx record ID, or persistence result.

Selected-window validation found zero invalid, missing, non-finite, or negative aggregate values; zero-W aggregate readings occur only once in H2 and four times in H11. All selected `Time`/`Unix` UTC cross-checks matched, and no selected-window duplicate or out-of-order Unix timestamps were found. These facts establish input quality; they do not establish anomaly labels.

### 1.2 Important exclusion-log caveat

`excluded_records_log.csv` contains 531 `GAP_OVER_16_SECONDS` and 5 `NO_SUCCESSOR_AT_WINDOW_END` exclusions. Its fields named `related_predecessor_row_number` and `related_predecessor_unix` are not directionally reliable for every observed gap row: for a `GAP_OVER_16_SECONDS` row they can refer to the later successor observation. Future chronology checks must therefore use the canonical `original_unix` and source-row fields in the cleaned records, rather than treating the `related_predecessor_*` names as a universal relationship.

## 2. Research questions

The questions are separated so that system-integration evidence is never misrepresented as ML accuracy evidence.

| ID | Testable question | Evidence required | Claim boundary |
|---|---|---|---|
| RQ-INT-1 | Can a selected, ordered Task 2 household interval stream be represented losslessly in the existing ingestion contract after an explicitly audited compatibility adapter is available? | Source-to-payload mapping ledger; client receipts; HTTP status accounting | Addresses input-contract integration, not downstream persistence. |
| RQ-INT-2 | For a controlled replay, can planned events be reconciled with observable ingress, broker, consumer, persistence, and alert evidence? | Run ledger plus pre/post offset, database, and metric snapshots | A HTTP `201` alone is insufficient proof of end-to-end processing. |
| RQ-ML-1 | Does the available data support a scientifically defensible anomaly-detection accuracy evaluation? | Provenance-aligned labels or a separately declared controlled-perturbation benchmark | No precision, recall, F1, or accuracy claim is permitted until the label basis is approved. |
| RQ-REP-1 | Can the preprocessing and later run-accounting outputs be reproduced from frozen inputs and configuration? | Manifest hashes, deterministic preprocessing verification, and future run manifests | Reproducibility is assessed separately from functional success. |

## 3. Frozen cohort design

### 3.1 Primary cohort: H1, H2, H4

H1, H2, and H4 are the primary cohort because each has a checksum-verified source file, a Task 1 pre-registered eligible 14-day window, valid Task 2 reconciliation, and no retained REFIT solar-interference caveat. H1's source caveat states that rewiring eliminated solar contribution; H2 and H4 have no documented solar-interference caveat in the Task 2 quality report.

The primary cohort is used for the main historical replay/system-integration evaluation. It is not proof that the three homes are a representative population sample.

### 3.2 Solar sensitivity cohort: H3, H11

H3 and H11 are processed with the same checksum, chronology, and interval-energy procedure but remain a separate sensitivity cohort because the REFIT descriptor documents solar-generation interference. Their energy is not corrected net-import energy and must not be pooled with the primary cohort in household-consumption or ML-generalisation summaries.

### 3.3 Household inclusion/exclusion rule

A household is eligible for a named cohort only when all of the following hold: (i) expected source checksum matches, (ii) required source columns are present, (iii) a Task 1 eligible window exists, (iv) Task 2 source-to-output reconciliation passes, and (v) its documented caveat is compatible with the intended cohort. No household may be added for convenience. House 5 is not part of this protocol.

## 4. Frozen replay intent

The detailed semantics and retry policy are in `replay_semantics_and_retry_policy.md`. The principal choices are frozen as follows:

1. **Main live-like mode:** preserve the REFIT source time in an external run ledger, but send a current UTC payload timestamp to the existing ingestion contract. This is necessary because the contract carries only one timestamp and current dashboard/aggregation code queries wall-clock windows.
2. **Ordering:** process each household in ascending `(original_unix, source_row_number)` order. For a concurrent primary-cohort run, use relative alignment at `t=0`; ties are deterministically ordered by relative offset, source Unix time, household ID, and source row number. Relative alignment is an artificial replay schedule and will be logged as such.
3. **Source-timestamp mode:** reserve original 2014/2015 timestamps for a historical-persistence check only. It cannot support current-window dashboard/alert claims because current services query wall-clock ranges.
4. **Run sequence:** first a single-household H1 smoke test; then a dry-run for all three primary homes; then a short concurrent primary run. H3/H11 require a separately reported sensitivity run after the primary workflow is proven.
5. **Compatibility gate:** Task 2's fields do not directly satisfy the existing replay helper's required old schema (`source_unix`, `timestamp_utc`, `estimated_interval_energy_kwh`, and `is_replayable`). A future compatibility adapter must be reviewed and hash-logged before any replay. Task 3 does not create that adapter.

## 5. Event accounting and reconciliation

`event_accounting_plan.csv` is the binding list of fields, evidence sources, and limitations. The source-event identity for reconciliation will be:

```text
run_id + household_id + source_filename + source_row_number + original_unix
```

This identity is available in the replay ledger, but it is not currently carried by the ingestion DTO, Kafka event, or Influx point. Consequently, exact downstream per-run reconciliation is not currently guaranteed. Any metric that cannot be observed must be reported as **not measured**, not as zero.

The required reconciliation hierarchy is:

```text
selected source records
  = planned replay events + intentionally excluded records
planned replay events
  = final client receipts (HTTP accepted + HTTP failed + transport uncertain)
```

Kafka, InfluxDB, ML, and alert counts must be reported as separate measured layers. A discrepancy must be investigated from client receipt, to ingress logs, Kafka topic/consumer offsets, `energy-usage.DLT`, Influx query results, ML metrics, and alert metrics; it must never be silently allocated to a downstream category.

## 6. Label and ML-evaluation position

The official REFIT anomaly dataset exists, but it is appliance-level and covers H1, H10, H16, H18, and H20. Only H1 overlaps the current five-house Task 2 selection. The official CSV/README are not present locally and could not be retrieved programmatically in this environment, so their schema, time alignment, and H1-window overlap have not been audited.

The recommended immediate study is therefore a **system-integration experiment without an ML accuracy claim**. A future controlled-perturbation evaluation may be scientifically valid only when declared before generation, created after chronological partitioning, and labelled solely as controlled-perturbation detection. A future genuine-label study is limited to an appliance-level/H1-only analysis unless a separately justified aggregate mapping is verified. Details are frozen in `labeling_strategy.md` and `cohort_and_split_plan.md`.

## 7. Stage gates and acceptance criteria

| Gate | Stage | Entry condition | Advance condition | Failure / hold condition |
|---|---|---|---|---|
| G1 | Protocol approval | All six Task 3 deliverables exist and Task 2 artifacts verify. | Reviewer accepts cohort boundaries, compatibility limitation, accounting plan, and label boundary. | Any unresolved issue is treated as accepted/declined explicitly; no execution begins silently. |
| G2 | Small replay smoke test | A reviewed compatibility adapter and verified H1-to-existing-device mapping exist; services are healthy. | Five planned H1 events have one final client receipt each; all are HTTP-accepted; no transport-uncertain outcome exists. | Any non-accepted, ambiguous, unlogged, unauthorized, or schema-invalid event stops progression. |
| G3 | Multi-household replay readiness | G2 passed; separate verified device mappings exist for H1/H2/H4. | A no-network dry-run produces exactly 25 planned records per primary house, preserves per-house order, and records a one-to-one mapping/receipt plan. | Missing mapping, cross-cohort selection, non-monotonic source order, or schema mismatch blocks execution. |
| G4 | Short end-to-end validation | G3 passed; clean, isolated observation window and pre-run counters/offsets are recorded. | 25 events per primary house (75 total) are HTTP-accepted and all observable downstream evidence is reconciled or explicitly classified as unavailable. | Any unexplained client discrepancy, duplicate indication, missing scoped persistence evidence, or ambiguous outcome holds the extended run. |
| G5 | Extended replay | G4 passed and the rate/collision preflight is documented. | A pre-registered continuous segment reconciles at every measurable layer; results preserve the primary/sensitivity separation. | Capacity failure, timestamp collision, unexplained count difference, or unbounded retry stops the stage. |
| G6 | Offline ML evaluation | A label basis and split plan have been approved before fitting. | Evaluation follows the frozen chronological split, feature-fit boundary, and label terminology. | Missing/unaligned ground truth, test leakage, or synthetic labels described as real anomalies invalidates the ML result. |
| G7 | Optional experimental-model integration | G6 has a reproducible offline result and an isolated experimental model artifact. | Model version, feature contract, input/output topics, event accounting, and alert behavior are verified without replacing the baseline model. | Any baseline-model replacement, undocumented topic path, or unaccounted alert behavior holds integration. |

The numerical event counts in G2–G4 are deliberately small operational samples, not performance thresholds. Exact ledger reconciliation is required because it is an integrity property, not an arbitrary success rate. G5 has no pre-claimed throughput target; a future rate must be justified by G4 evidence rather than selected to guarantee success.

## 8. Reproducible read-only checks

The following checks are permitted before later approval and do not replay telemetry:

```powershell
python experiments\refit_task2_energy_normalization\verify_artifacts.py
Get-Content experiments\refit_task2_energy_normalization\artifacts\data_manifest.json
Get-Content experiments\refit_task2_energy_normalization\artifacts\per_household_quality_report.csv
Get-Content experiments\refit_task2_energy_normalization\artifacts\timestamp_interval_report.csv
```

No POST request is a health check. A later execution stage must record the exact command, configuration hash, input hash, household-device mapping hash, service versions, and pre/post observability snapshots in a run manifest.

## 9. Evidence references

- `experiments/refit_task2_energy_normalization/preprocessing_config.yaml`
- `experiments/refit_task2_energy_normalization/artifacts/data_manifest.json`
- `experiments/refit_task2_energy_normalization/artifacts/per_household_quality_report.csv`
- `experiments/refit_task2_energy_normalization/artifacts/timestamp_interval_report.csv`
- `experiments/refit_task2_energy_normalization/artifacts/excluded_records_log.csv`
- `experiments/refit_task2_energy_normalization/reproducibility_validation.md`
- `evidence/16_refit_dataset_audit/household_selection.csv`
- `ingestion-service/src/main/java/com/hometracker/ingestion_service/dto/EnergyUsageDto.java`
- `ingestion-service/src/main/java/com/hometracker/ingestion_service/service/IngestionService.java`
- `usage-service/src/main/java/com/hometracker/usage_service/service/UsageService.java`
- `real_data_replay/replay_stream.py`
- [Official REFIT cleaned dataset record](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/)
- [Official annotated REFIT anomaly dataset, DOI 10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33](https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/)
