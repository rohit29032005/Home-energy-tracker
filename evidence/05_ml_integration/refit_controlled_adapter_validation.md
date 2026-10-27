# Experimental REFIT controlled-model integration validation

## Scope

This evidence records a separate **experimental controlled-perturbation**
inference path for the REFIT artifact. It does not replace the legacy
Wokwi-compatible supervised model, does not consume `energy-usage`, and does
not publish to `anomaly-results`.

The controlled-model evaluation itself is retained in
`evidence/18_refit_controlled_ml_v1_1/`. Its strict 99th-percentile,
three-consecutive-bin policy produced zero primary-cohort alert detections;
therefore this adapter is deliberately not represented as a deployed
real-world fault detector.

## Implemented contract

### Explicit REST route

`POST /experimental/refit-controlled/predict`

Required JSON fields:

```json
{
  "refitProfileId": 1,
  "streamId": "explicit-replay-stream",
  "energyConsumed": 0.0003,
  "timestamp": "2026-01-01T00:00:08Z",
  "intervalSeconds": 8
}
```

- `refitProfileId` is restricted to 1, 2, 3, 4, or 11.
- `streamId` explicitly owns causal state. No `deviceId` to household mapping
  exists in the route.
- The adapter aggregates exact interval energy into UTC-aligned 300-second
  bins, requires 285 seconds of coverage, uses a six-bin causal warm-up, and
  resets state for a material gap, non-monotonic timestamp, or overlapping
  interval.
- Results expose an uncalibrated `anomalyScore`, frozen threshold, candidate,
  and three-bin alert state only after a bin closes. They never expose a
  probability.

### Dedicated Kafka side path

The optional worker is disabled unless
`REFIT_CONTROLLED_KAFKA_ENABLED=true`.

```text
refit-controlled-replay
  -> RefitControlledKafkaWorker
  -> refit-controlled-anomaly-results

invalid/failed event
  -> refit-controlled-anomaly-failures
```

It rejects an implicit `deviceId` mapping and never writes to the legacy
`anomaly-results` topic, so the existing alert service cannot consume this
experimental score without a future explicit integration decision.

## Actual validation executed

Command executed from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest ml-service\tests -q
```

Observed result on 2026-10-10:

```text
18 passed, 1 warning in 10.62s
```

The warning is FastAPI/Starlette's dependency deprecation notice for
`TestClient`; it is not a test failure.

The tests cover:

1. legacy `/predict` model loading and existing Wokwi payload compatibility;
2. explicit profile requirement and absence of `anomalyProbability` on the
   REFIT route;
3. exact cross-bin energy allocation;
4. causal-history warm-up;
5. material-gap reset;
6. three-consecutive-candidate persistence;
7. explicit REFIT Kafka output and failure-topic contracts.
8. legacy and experimental worker reconnection after a simulated broker
   connection failure, without requiring a live broker;
9. closure of the connected producer and cleanup of a partially initialized
   consumer when producer creation fails;
10. disabled-worker state in the ML health response.
11. unacknowledged REFIT result or failure-topic publication leaves the input
    consumer offset uncommitted in the local worker double.

Both Kafka workers now retry a broker connection after the configurable
`KAFKA_CONNECTION_RETRY_SECONDS` delay (default 5 seconds). The ML health
endpoint exposes an intentionally small worker state (`disabled`, `starting`,
`reconnecting`, or `connected`) and connection-attempt count. This does not
turn a disconnected broker into a healthy pipeline: it makes the degradation
visible and prevents a transient broker outage from permanently ending the
worker thread.

## Runtime limitation

`docker compose ps` could not connect to the local Docker daemon during this
validation (`//./pipe/docker_engine` was unavailable). Consequently a live
Docker/Kafka end-to-end replay is **NOT YET MEASURED**. The REST and Kafka
contracts above have unit/TestClient coverage only; they are not evidence of a
running broker path.
