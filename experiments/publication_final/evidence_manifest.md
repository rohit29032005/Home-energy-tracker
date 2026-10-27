# Evidence manifest

## Evidence classes

| Class | Meaning | Use in the manuscript |
| --- | --- | --- |
| A | Previously recorded historical evidence | Retained only with source path, run date, and historical label. |
| B | Newly reproduced result | Existing result reproduced from a copied input and current code without changing the existing application. |
| C | Newly generated isolated experiment | New offline analysis, component test, or microbenchmark created for this manuscript. |
| D | Not tested or blocked | A capability or experiment not run; it is not reported as a pass. |

## B. Newly reproduced supervised-baseline evidence

| Item | Path | Evidence and result |
| --- | --- | --- |
| Execution manifest | `evidence/ml_validation/experiment_manifest.json` | Run time, exact commands, copied-input hash, isolation boundary, and non-executed work. |
| Validation report | `evidence/ml_validation/ml_validation_report.md` | Complete narrative of data checks, baseline reproduction, and limitations. |
| Schema and split checks | `evidence/ml_validation/analysis/schema_validation.json`; `analysis/split_leakage_checks.json` | 5,000-row/7-field copied CSV; no observed cross-split timestamp, raw-record, or engineered-feature fingerprint overlap; two provenance issues unresolved. |
| Reproduced models and metrics | `evidence/ml_validation/reproduction/model/`; `reproduction/evidence/04_ml_evaluation/` | New random-forest and logistic-regression outputs; the metric comparison matches the historical record exactly. |
| Reproduction comparison | `evidence/ml_validation/analysis/reproduction_comparison.json` | Maximum absolute difference of zero across reported baseline metrics. |

## C. Newly generated isolated evidence

| Item | Path | Evidence and result |
| --- | --- | --- |
| Fixed-model bootstrap analysis | `evidence/ml_bootstrap_ci/results_300/bootstrap_summary.json`; `bootstrap_draws.csv` | 300 stratified bootstrap draws for the 750-row held-out interval; test F1 0.902439 with 95% interval 0.838300 to 0.957444. |
| Input contract and Wokwi-scale check | `evidence/ml_robustness/results/robustness_results.json`; `input_validation_results.csv`; `wokwi_controlled_predictions.csv` | Five of five in-process validation cases passed. Documented Wokwi energy boundaries expose a scale mismatch with training values; synthetic inputs have no labels. |
| Single-worker inference benchmark | `evidence/ml_inference_benchmark/results_single_worker_repeated/summary.json`; `single_record_latencies.csv` | 300 local in-process inference observations; mean 98.719 ms and p95 129.680 ms. |
| Offline component tests | `evidence/component_tests/execution_summary.json`; `test_inventory.csv`; `README.md` | 19 of 19 fresh in-process/pure-local tests passed. Two Kafka-worker suites were blocked by an unavailable dependency and are not counted as passes. |

All C-class work avoided Docker lifecycle commands, HTTP requests, live Kafka, databases, persistent volumes, credentials, REFIT replay, and model training except for the isolated baseline reproduction explicitly described in the B-class manifest.

## A. Historical evidence retained with explicit status

| Item | Path | Historical claim retained |
| --- | --- | --- |
| Controlled local integration | `evidence/13_end_to_end/review2_e2e_results_20261005-214326.json` | A pre-existing single-host synthetic case submitted three values totaling 1.5 kWh, observed analytics after 3.79 s, and observed a threshold-alert record after 13.64 s. It was not rerun in this task. |
| Local k6 load test | `evidence/09_performance/load_test_summary_20261005.md` | A pre-existing single-host k6 run reported 450/450 HTTP 201 responses and 109.77 ms p95. It is not a capacity claim and was not rerun. |
| Resilience tests | `evidence/10_resilience/usage_influx_dlt_embedded_kafka_20261010.md`; `evidence/10_resilience/ml_refit_worker_publish_commit_order_20261010.md` | Pre-existing local test records only; they are described as historical component evidence rather than new end-to-end fault validation. |
| Historical test inventory | `evidence/15_final_validation/test_summary.csv`; `evidence/component_tests/historical_surefire_summary.csv` | Existing reports were inspected read-only and are not presented as freshly executed tests. |

## D. Not tested or blocked

| Item | Status | Exact reason |
| --- | --- | --- |
| Full current Docker end-to-end experiment | Blocked | Existing stack recovery remains unauthorized after Kafka OOM evidence. |
| Live device/JWT authorization validation | Not run | Requires application endpoints and credentials, prohibited by the experiment isolation boundary. |
| Broker-backed Kafka test | Blocked | Current local Python environment lacks the Kafka client dependency; live broker use remains prohibited. |
| REFIT replay and multi-household experiment | Blocked | REFIT isolated deployment, household/device provisioning, and data-replay gates remain unresolved and undeployed. |
| New k6 performance run | Not run | Requires HTTP load against a live isolated environment, not available within the safe boundary. |
| New fault injection or alert-deduplication run | Not run | Requires disposable services and side-effect controls beyond the approved offline scope. |

## Integrity notes

- The supplied supervised CSV hash is `d48df940fd29444fb9222fc0b59cfde632e147ccd1d49dc7bed9d5f9dc88f588`.
- The model/metric results must be interpreted conditionally because the repository does not document the CSV source, licence, label-generation process, or causal construction of `Avg_Past_Consumption`.
- No secret, token, password, device credential, personal email, or database content is reproduced in this manifest.
