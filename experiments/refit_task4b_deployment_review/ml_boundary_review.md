# Task 4B — ML Boundary Review

**Scope:** Static source review only. No model was loaded, trained, replaced, invoked, or modified.

## Verified baseline ML boundary

The legacy ML worker is not device-filtered. When the ML service starts with `KAFKA_ENABLED=true`, `ml-service/app/main.py:260-270` starts `KafkaInferenceWorker`. That worker subscribes to Kafka topic `energy-usage` using consumer group `ml-inference-service` (`ml-service/app/kafka_worker.py:102-109`) and publishes every successfully processed result to `anomaly-results` (`.../kafka_worker.py:161-170`). Alert Service consumes `anomaly-results` in group `alert-service-anomaly` (`alert-service/.../AlertService.java:59-72`).

The current Compose configuration enables the legacy worker (`docker-compose.yml:183`; production `docker-compose.prod.yml:167`). Therefore, a REFIT event sent to the current shared broker's `energy-usage` topic can reach the existing baseline ML/alert path. This source-code evidence is why the shared deployment remains NO-GO.

## Options compared

| Option | Source-code evidence | Benefits | Limitation / decision |
|---|---|---|---|
| 1. Exclude the baseline ML service from the REFIT deployment | API Gateway does not depend on ML service in `docker-compose.yml:271-307`; legacy worker starts only when its container/service is included and `KAFKA_ENABLED=true`. | No baseline worker consumes experiment broker events; no model loading or predictions during environment validation. | **Recommended for initial deployment validation.** No events are sent at this stage. |
| 2. Include a separate ML service for experiment-only processing | The repository contains `RefitControlledKafkaWorker`, disabled by current Compose defaults, with separate input/output/failure topics. Evidence: `ml-service/app/refit_kafka_worker.py:1-231`, `ml-service/app/main.py:34-41, 274-283`, `docker-compose.yml:194-198`. | Its dedicated topic names prevent direct use of legacy `anomaly-results` when correctly configured on an isolated broker. | It expects a different controlled-REFIT schema (`refitProfileId`, `streamId`, `intervalSeconds`) and a separate controlled artifact. It is outside initial deployment validation and needs an explicit later protocol/model approval. |
| 3. Later event-path test without any ML consumer | Ingestion and Usage are independently connected through `energy-usage`; Usage consumes in group `usage-service` and writes Influx. Evidence: `IngestionService.java:24-35`; `UsageService.java:61-76`. | Tests the application event path without triggering ML or ML alerts. | This is not part of Task 4B because Task 4B sends no events. A later test still changes isolated Kafka/Influx state and needs separate approval. |

## Recommendation for initial deployment validation

1. Do not include `ml-inference-service` in the initial isolated Compose specification.
2. Do not include `alert-service` in that minimum validation set, because it consumes `anomaly-results` and `energy-alerts` and writes alert records.
3. Send no telemetry, REFIT data, synthetic data, or Kafka messages.
4. Validate only static configuration, network isolation, service readiness, secret references, and the absence of a legacy ML consumer on the isolated broker.

This ensures that deployment validation does not alter any model artifact or create predictions. It also avoids claiming that a model has been empirically evaluated.

## Controlled-REFIT worker status

### Verified facts

- `RefitControlledKafkaWorker` uses default topics `refit-controlled-replay`, `refit-controlled-anomaly-results`, and `refit-controlled-anomaly-failures` (`ml-service/app/refit_kafka_worker.py:46-52`).
- It uses consumer group `refit-controlled-inference-service` (`.../refit_kafka_worker.py:130-137`).
- It explicitly rejects the legacy device-based payload contract; its required fields are `refitProfileId`, `streamId`, `energyConsumed`, `timestamp`, and `intervalSeconds` (`.../refit_kafka_worker.py:224-257`).
- The controlled worker is gated by `REFIT_CONTROLLED_KAFKA_ENABLED` and artifact availability (`ml-service/app/main.py:274-283`).

### Consequence

It is technically distinct from the legacy worker, but it is **not** a drop-in target for the planned ingestion API replay. Integrating it would require a separately approved adapter/protocol path. Task 4B does not change its configuration, artifact, model, or behavior.

## Baseline model handling

The legacy service loads `anomaly_model.joblib` plus `model_metadata.json` in `ModelStore.load()` (`ml-service/app/main.py:158-175`) and uses optional context fields to build a feature frame (`.../main.py:210-260`). No REFIT deployment validation should attempt to feed raw Task 2 rows into this path merely because `energyConsumed` exists; the data contracts are not shown to be equivalent beyond the three shared ingestion fields.

## ML-related validation gate

Before a future isolated deployment is created, the deployment specification must show one of these two static states:

| Gate | Required evidence | Pass condition |
|---|---|---|
| Initial validation | `ml-inference-service` absent from the isolated specification, or conclusively disabled and unconnected to experiment Kafka | No consumer group `ml-inference-service` can attach to the experiment broker. |
| Later experiment ML path | A separately approved ML plan, explicit topic names, artifact provenance, payload schema, consumer group, and alert isolation | No legacy topic or alert topic is reused; model work has explicit authorization. |

## Decision

**GO FOR DEPLOYMENT PLANNING ONLY:** exclude ML and alert services from the initial validation deployment.  
**NO-GO for ML execution:** no legacy or controlled ML worker may be started for REFIT data without a later explicit approval.
