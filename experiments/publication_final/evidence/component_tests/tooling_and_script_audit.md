# Tooling, Script, and Performance-Harness Audit

## k6 load harness

`tools/performance/k6-ingestion.js` is an end-to-end load scenario. Its source creates randomized ingestion payloads and performs HTTP POST requests to the configured gateway URL. The companion `tools/performance/run-load-test.ps1` can run native k6 or start a disposable k6 Docker container, writes raw and summary evidence, and requires an ingestion token supplied through the environment or parameter.

**Decision:** not run. It would send telemetry, invoke an endpoint, and may start a Docker container. Consequently, this evidence set contains no throughput, latency, error-rate, or scalability result.

## Data and experiment scripts

| Source | Static behavior relevant to this audit | Decision |
|---|---|---|
| `scripts/refit_task1_audit.py` | Dataset audit path | Not run; dataset activity belongs to a separately controlled experiment task. |
| `scripts/refit_task2_preprocess.py` | Reads selected REFIT inputs and writes cleaned/replay-ready outputs | Not run; writes experiment artifacts. |
| `scripts/refit_task2_verify.py` | Read-only verification of Task 2 outputs | Not run; it is dataset evidence rather than component-test evidence. |
| `scripts/refit_task4_generate_anomalies.py` and similarly named helper | Generates controlled synthetic perturbation artifacts | Not run; would create labels and evidence. |
| `scripts/refit_task4_verify_anomalies.py` | Verifies anomaly-generation outputs | Not run; separate data/experiment scope. |
| `scripts/refit_task5_verify_training.py` | Verifies training outputs | Not run; model/data artifact scope. |
| `ml-service/training/train.py` and controlled training code | Reads datasets and writes model/evidence outputs | Not run; no training authorized by this component audit. |
| `real_data_replay/replay_stream.py` | Can make ingestion requests during replay | Not run. One no-I/O timestamp helper test was selected instead. |

## What the fresh execution does and does not establish

The fresh test output supports narrow claims about local component behavior: header/token handling in gateway filter code, deterministic state/feature logic in the REFIT controlled implementation, causal-feature and allocation logic in the trainer helpers, and per-device timestamp monotonicity. It does not establish performance, deployment behavior, real telemetry delivery, database writes, alerts, emails, or detection accuracy on a household dataset.

