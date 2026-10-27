# Component-Test Blockers and Exclusions

## Blocking issue: local Kafka client dependency

**VERIFIED:** Importing `ml-service/tests/test_refit_kafka_worker.py` and `ml-service/tests/test_kafka_reconnect.py` fails before test execution because the active local Python interpreter cannot import `kafka`.

**Impact:** The two mock-based Kafka worker suites (9 source tests in total) have no fresh result in this evidence set. This does not establish a code defect or a broker failure.

**Safe next step, requiring separate authorization:** run the tests inside an approved, isolated environment where the declared development dependency is already installed or may be installed under a reproducible dependency-management procedure. The test code itself uses doubles; no live broker is required once imports succeed.

## Output-containment issue for Maven

**VERIFIED:** The selected offline Maven gateway command passed 8 tests, but Maven wrote its Surefire report to the pre-existing `api-gateway/target/surefire-reports` directory rather than the requested evidence path. It did not alter source, configuration, or model files.

**Action taken:** no further Maven command was run. This prevents further test-report writes outside the delegated evidence directory.

**Safe next step, requiring separate authorization:** establish a disposable Maven workspace or an approved build-output redirection that is empirically verified before running the remaining Java component suites.

## Deliberately excluded runtime paths

| Item | Reason it was not executed in this audit |
|---|---|
| Spring application-context suites | Context startup can consume test data/Kafka/mail-related configuration and may initialize integrations. |
| `UsageKafkaFailureRecoveryTest` | Starts embedded Kafka; resource-sensitive while the Docker Kafka OOM cause is unresolved. |
| `ml-service/tests/test_api.py` route tests | Uses FastAPI `TestClient`; the task prohibited endpoint invocation. |
| `real_data_replay/test_replay_stream.py::test_retries_confirmed_503_then_accepts_201` | Starts a loopback HTTP server and invokes an endpoint; prohibited. |
| `tools/performance/k6-ingestion.js` and `run-load-test.ps1` | Sends authenticated HTTP telemetry and may invoke Docker; prohibited. |
| REFIT preprocess/anomaly/replay/training scripts | Normal use writes output artifacts, labels data, trains models, or can replay data; out of scope. |

No Docker, service, HTTP, Kafka, database, credential, event, alert, replay, or model-training action was performed.
