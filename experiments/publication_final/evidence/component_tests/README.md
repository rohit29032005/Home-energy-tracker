# Offline Component-Test Evidence

## Scope and safety boundary

This evidence set records a source-level audit and the limited set of component tests executed on 15 October 2026. The execution boundary was deliberately narrow: no Docker lifecycle command, application HTTP endpoint, Kafka broker, data volume, credential, event replay, model training, or load test was invoked. The executed tests used in-memory objects, test doubles, or pure local calculations only.

## Fresh execution result

Four commands were selected after static inspection. Three completed successfully and one intentionally isolated safe test completed successfully. Together, the successful commands executed **19 tests: 19 passed, 0 failed, 0 errored, 0 skipped**.

| Evidence group | Test count | Result | What it validates | Execution class |
|---|---:|---|---|---|
| API-gateway security filters | 8 | PASS | Device-token/JWT handling, ownership forwarding, and spoofed-header stripping | In-process reactive unit/component test |
| REFIT controlled runtime | 5 | PASS | Explicit profile selection, interval splitting, warm-up, persistence, and gap reset logic | Pure in-memory unit test |
| REFIT controlled trainer | 5 | PASS | Leakage safeguards, causal features, label separation, persistence, and interval allocation | Pure in-memory unit test |
| Replay timestamp helper | 1 | PASS | Monotonic current-timestamp adjustment per device | Pure standard-library unit test |

The exact commands and unmodified console output are stored in `raw_outputs/`. `execution_summary.json` is the machine-readable summary.

## Important negative finding

An initial combined Python command could not import the two Kafka-worker test modules because the local interpreter lacks the `kafka` Python package. This is an environment/dependency blocker, not a failed assertion in the workers. No package was installed, because this audit was offline and change-free. The two affected modules were not represented as passing tests.

## Existing report inventory

The repository already contained 28 Java Surefire XML suite reports covering 87 reported tests (0 failures, 0 errors, 3 skipped). They are inventoried in `historical_surefire_summary.csv`. They are **historical report artifacts observed read-only during this audit**, not fresh re-execution evidence. Their provenance and recency cannot be established from the audit alone, so they must not be presented as newly run results.

## Tests deliberately not run

The audit excluded all tests or tools whose runtime path could exceed the safe boundary:

- Spring application-context tests, because test resource files configure data/Kafka/mail-related properties and a full context can initialize side-effecting integrations.
- `UsageKafkaFailureRecoveryTest`, because it starts an embedded broker and is resource-sensitive while the Docker Kafka service has an unresolved OOM history.
- FastAPI `TestClient` routes, the replay retry test using an in-process loopback HTTP server, and the k6 scenario, because the task prohibited endpoint invocation. The standalone timestamp test was safe and run separately.
- Data preprocessing, synthetic-anomaly generation, trainer execution, and replay scripts, because their normal path writes data artifacts, produces labels, trains models, or can send telemetry.
- Additional Maven executions after the gateway run. Maven ignored the attempted relocated build-directory property and wrote reports to the pre-existing `api-gateway/target` tree. No source/configuration/model was modified, but further Maven runs were stopped so no additional files would be written outside this evidence directory.

## Interpretation limits

These results demonstrate component behavior under mocks and local fixtures only. They do not demonstrate end-to-end API availability, container health, live authorization, Kafka delivery, database persistence, alert delivery, model generalization, REFIT replay correctness, or system throughput.

