# ML-service local regression validation

**Execution date:** 2026-10-10  
**Execution mode:** local Python test suite; no Docker runtime

## Command executed

~~~powershell
.\.venv\Scripts\python.exe -m pytest ml-service\tests -q
~~~

## Observed result

**18 tests passed in 10.62 seconds.** Pytest emitted one dependency
deprecation warning from Starlette TestClient/httpx; no test failure occurred.

## Covered local contracts

- Existing telemetry input acceptance, negative-energy rejection, health, and
  trained-artifact prediction API behaviour.
- Explicit REFIT experimental-profile selection and score-oriented output.
- Legacy and REFIT Kafka-worker reconnection/cleanup paths.
- REFIT isolated-topic routing, invalid-event failure routing, time-bin energy
  and coverage preservation, warm-up/scoring behavior, consecutive-candidate
  alerting, and gap-driven stream reset behavior.
- REFIT input-commit ordering when result or failure-topic publication cannot
  be acknowledged.

## Boundary

This result is a local mocked/unit-level regression run. It does not measure a
running Kafka broker, the production inference endpoint, throughput, model
accuracy on an external test set, or a live Docker deployment.
