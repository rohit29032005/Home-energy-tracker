# Task 0 — Experiment Baseline Audit

**Audit date:** 12 October 2026 (IST)  
**Repository:** `Home-Energy-Tracker`  
**Task status:** **COMPLETE — audit only**

## Scope and non-negotiable boundary

This record establishes the baseline before a household-data experiment. No
dataset was downloaded, no historical reading was replayed, no model was
trained or refitted, no alert was deliberately generated, and no paper or
application architecture was changed during Task 0. The only new artifact
created by this task is this audit file.

The working tree already contained substantial user work and untracked
artifacts when the audit began. Those pre-existing changes were preserved.

---

## 1. Executive baseline result

The repository contains a working microservice implementation and a separate,
safety-oriented real-data replay tool. The intended evidence wording, after
the required data and runtime checks have been completed, is:

> "real-world recorded household electricity data replayed as a continuous live-like stream."

It must **not** be described as real-time household metering, a live utility
feed, or a genuine fault-labelled anomaly experiment.

The system is **conditionally ready** for the next feasibility stage, but it
is **not ready for a five-house execution** without resolving the credential
and device-mapping issue in Section 8.1. Existing REFIT-related evidence is
available as prior evidence; the data/artifact directories themselves could
not be freshly enumerated by this audit process, so their availability is not
re-claimed here.

---

## 2. Verified application baseline

### 2.1 Docker Compose topology

`docker compose config --quiet` completed successfully. `docker compose
config --services` reported the following 17 configured services:

| Layer | Service(s) | Relevant host port(s) / state |
|---|---|---|
| Data | `mysql`, `influxdb` | `3306`, `8072 -> 8086` |
| Streaming | `kafka`, `kafka-ui` | `9092`, `9094`, `8070` |
| Identity and gateway | `keycloak`, `api-gateway` | `8180`, `8080` |
| Core microservices | `user-service`, `device-service`, `ingestion-service`, `usage-service`, `alert-service`, `insight-service` | Internal Docker ports `8081`–`8086` |
| ML | `ml-inference-service` | Internal Docker port `8090` only |
| User interface | `frontend` | `3000 -> 80` |
| Observability | `prometheus`, `grafana` | `9090`, `3001 -> 3000` |
| Local notification capture | `mailpit` | SMTP `1025`, UI/API `8025` |

A read-only `docker compose ps --format json` inspection listed all 17
services with `State: running` at audit time. This establishes container state,
not an end-to-end experiment result.

**Current-runtime caution.** Direct host HTTP probes from the audit execution
environment were first blocked by sandbox socket policy; an approved retry
then timed out while checking the gateway and frontend. Consequently, this
Task 0 audit does **not** make a new 12 October public-endpoint health claim.
The older live validation remains historical evidence only:
`evidence/15_final_validation/docker_live_runtime_validation_20261011.md`.

### 2.2 Public ingestion contract

The public telemetry boundary is implemented by:

* Gateway route: `api-gateway/src/main/resources/application.properties`
* Controller: `ingestion-service/src/main/java/com/hometracker/ingestion_service/controller/IngestionController.java`
* Request DTO: `ingestion-service/src/main/java/com/hometracker/ingestion_service/dto/EnergyUsageDto.java`
* Publisher: `ingestion-service/src/main/java/com/hometracker/ingestion_service/service/IngestionService.java`

| Contract item | Verified implementation |
|---|---|
| Method and path | `POST /api/v1/ingestion`, normally through `http://localhost:8080` API Gateway |
| Success response | `201 Created` from `IngestionController` after the service has accepted the request |
| JSON fields | `deviceId` (required), `energyConsumed` (numeric, `>= 0`), `timestamp` (required `Instant`) |
| Correct experiment unit | An **interval-energy value in kWh**. It must not be raw REFIT aggregate power in Watts and must not be a cumulative meter value. The server validates non-negativity but does not enforce a physical unit. |
| Timestamp behavior | The DTO parses an `Instant`; ingestion forwards it unchanged to Kafka. No source-time ordering, future-time, or historical-time rejection rule was found in the controller/service source. |
| Event identity | No client event ID or idempotency key exists at the ingestion boundary. |
| Primary machine header | `X-Device-Token` |
| Device-token rule | The ingestion service checks that the submitted token matches the exact `deviceId:token` mapping. Reuse of one token across multiple configured device IDs is rejected by the parser. |
| JWT route | The gateway may forward a JWT-derived `X-Authenticated-User-Id` together with a private gateway proof; ingestion verifies ownership against `device-service`. |

An HTTP `201` means that the public ingestion boundary accepted the request. It
does **not** independently prove Kafka publication, InfluxDB persistence, ML
processing, alert delivery, or dashboard visibility.

### 2.3 Verified processing flow

~~~text
Meter / replay sender
  -> API Gateway :8080
  -> Ingestion Service
  -> Kafka topic: energy-usage
       -> Usage Service -> InfluxDB
       -> ML Inference Service -> Kafka topic: anomaly-results -> Alert Service
       -> Usage Service rolling one-hour threshold calculation (scheduled every 10 seconds)
          -> Kafka topic: energy-alerts -> Alert Service
~~~

#### Ingestion and persistent usage data

`IngestionService` publishes `EnergyUsageEvent(deviceId, energyConsumed,
timestamp)` to `energy-usage`. `UsageService` consumes the same topic as group
`usage-service` and writes the following exact InfluxDB schema:

| InfluxDB element | Verified value |
|---|---|
| Bucket / organization defaults | `usage-bucket` / `hometracker` |
| Measurement | `energy_usage` |
| Tag | `deviceId` |
| Field | `energyConsumed` |
| Write time | Event timestamp, with millisecond precision |

The usage service queries the most recent one-hour or requested-day range,
joins each device to `Device.userId`, and obtains the user alerting preference
and threshold before producing a threshold event. If InfluxDB persistence
fails, the listener throws `InfluxWriteException`; the configured policy is
bounded retry followed by `energy-usage.DLT`.

#### Alert and deduplication path

`AlertService` consumes both:

* `energy-alerts` for user/household threshold events, and
* `anomaly-results` for positive baseline-ML anomaly events.

For an ML anomaly it resolves `deviceId -> userId`, checks whether the user has
alerting enabled, and creates a `ML_ANOMALY` alert. The persisted deduplication
key is:

~~~text
userId : deviceId-or-HOUSEHOLD : alertType
~~~

The configured default deduplication window is **15 minutes**. Delivery is to
local Mailpit in the development Compose stack; it is a local email-capture
service, not proof of production email delivery.

Historical live evidence from 11 October 2026 showed two accepted readings
(`0.37 kWh` and `0.19 kWh`) reflected as `0.56 kWh` in the Usage API, proving
the ingestion -> Kafka -> Usage -> InfluxDB path for that dated run. See
`evidence/15_final_validation/docker_live_runtime_validation_20261011.md`.

---

## 3. Authentication, ownership, and experiment safety

The Compose development stack enables gateway security by default. The public
gateway uses Keycloak JWT validation for user requests and an explicit
machine-token path for telemetry. The ingestion service performs a second
authorization check:

* a machine token must match the submitted device ID; or
* a gateway-authenticated user must own the submitted device.

The gateway removes caller-supplied trust headers before forwarding trusted
headers. User/device/usage/alert services also check gateway or internal
service proof headers for their protected APIs.

This is useful defence in depth for the local project, but it is **not** a
claim of production-grade mTLS, workload identity, credential rotation, replay
protection, or managed secret storage. The Keycloak configuration is explicitly
development-oriented.

---

## 4. Baseline ML audit

### 4.1 Legacy deployed baseline

The accessible baseline artifact is:

* Model version: `random_forest-csv-20261003T205417Z`
* Model family: Random Forest
* Decision threshold: `0.31`
* Inference endpoint: `POST /predict` inside `ml-inference-service`
* Kafka input/output: `energy-usage` -> `anomaly-results`
* Failure topic: `anomaly-processing-failures` after bounded retries

The model metadata declares these eight features:

~~~text
Electricity_Consumed, Temperature, Humidity, Wind_Speed,
Avg_Past_Consumption, Hour, DayOfWeek, ConsumptionDeviation
~~~

The existing Wokwi/ingestion payload contains only `deviceId`,
`energyConsumed`, and `timestamp`. At baseline inference time,
`Temperature`, `Humidity`, `Wind_Speed`, and `Avg_Past_Consumption` are
imputed from persisted feature defaults, and `Hour`, `DayOfWeek`, and
`ConsumptionDeviation` are derived by the service. The response explicitly
lists the imputed fields.

The 11 October live-container evidence recorded a successful direct baseline
prediction for `deviceId=1`, `energyConsumed=0.55`, and a UTC timestamp. It
returned `anomaly=false`, probability `0.0`, baseline version
`random_forest-csv-20261003T205417Z`, threshold `0.31`, and four imputed
context features. This proves the dated direct `/predict` check only; it does
not prove a new replay experiment or a fresh ML-to-alert execution.

### 4.2 Baseline-model limitation relevant to household data

The legacy model was trained from `smart_meter_data.csv`. Its accessible
dataset audit records 5,000 rows, values numerically bounded at approximately
0–1 for `Electricity_Consumed`, and no source/license or label-generation
provenance. Therefore:

> **NOT VERIFIED — DO NOT CLAIM IN THE PAPER:** that the legacy Random Forest
> is trained on REFIT, trained on real household records, or valid for
> unnormalised REFIT/replay interval-energy values.

The baseline model may remain active as an application component, but it must
not be used as evidence of real-household anomaly performance without a
separate, documented compatibility and evaluation protocol.

### 4.3 Separate REFIT controlled experiment path

The codebase also contains a deliberately isolated REFIT
controlled-perturbation path:

* Training: `ml-service/training/train_refit_controlled.py`
* Runtime engine: `ml-service/app/refit_controlled.py`
* Optional endpoint: `POST /experimental/refit-controlled/predict`
* Optional Kafka topics: `refit-controlled-replay`,
  `refit-controlled-anomaly-results`, and
  `refit-controlled-anomaly-failures`

This path is disabled by default in `docker-compose.yml` through
`REFIT_CONTROLLED_EXPERIMENTAL_ENABLED=false` and
`REFIT_CONTROLLED_KAFKA_ENABLED=false`. It never consumes the Wokwi
`energy-usage` topic and never publishes into the legacy `anomaly-results`
topic. Its endpoint returns experiment-scoped scores and does not create an
alert automatically.

The optional model/evidence directories could not be read by this audit
process (`ml-service/models/refit-controlled-v1/`,
`ml-service/models/refit-controlled-v1.1/`,
`evidence/18_refit_controlled_ml/`, and
`evidence/18_refit_controlled_ml_v1_1/`). The root `.dockerignore` also
excludes the optional model directories from the Docker build context.

> **NOT VERIFIED — DO NOT CLAIM IN THE PAPER:** that an optional REFIT model
> artifact is currently deployable in the running container, enabled, or
> producing live alerts.

---

## 5. Existing real-data and replay materials

### 5.1 Prior REFIT source evidence

Existing prior evidence under `evidence/16_refit_dataset_audit/` documents a
checksum-verified cleaned REFIT subset for Houses 1, 2, 3, 4, and 11. It
records House 5 as unavailable during that earlier acquisition. It also
documents independently selected 14-day windows and keeps Houses 3 and 11 as
solar-interference sensitivity cases.

This is **prior recorded evidence**, not a fresh Task 0 download or fresh
source verification. In the current audit environment, `data/refit/` was
visible as a directory but could not be enumerated with the expected source or
processed contents. This prevents a current re-run of the data audit.

The associated controlled-perturbation documentation explicitly says that
positive labels are synthetic perturbations placed on a recorded baseline, not
verified appliance failures, meter faults, or genuine REFIT anomaly labels.

> **NOT VERIFIED — DO NOT CLAIM IN THE PAPER:** real REFIT anomaly accuracy,
> genuine-fault precision/recall/F1, official anomaly-label alignment, or
> full-archive coverage.

### 5.2 Replay tool capability and protections

`real_data_replay/replay_stream.py` is the proposed sender for a later
controlled run. Its intended input is the Task-2 processed file
`data/refit/processed/cleaned_dataset.csv`. It constructs the existing
ingestion payload using estimated **interval kWh**, preserves source timestamps
in receipts, and is dry-run by default. HTTP traffic occurs only when the
operator supplies `--execute`.

Verified protections in the source:

* a household-to-existing-device map is mandatory;
* raw REFIT Aggregate-W values are never sent directly as `energyConsumed`;
* a 2xx result is recorded only as ingress acceptance;
* source/current/rebased timestamp modes are explicit;
* retry of an uncertain transport failure is opt-in because it may duplicate
  ingestion; and
* receipts preserve source time, replay time, HTTP result, and source caveats.

The replay sender has no backend idempotency key to use. Accordingly, a later
execution is at-least-once at best and must not claim exactly-once delivery.

### 5.3 Existing Wokwi simulator

The separate §iot-simulator/§ PlatformIO/Wokwi project is also available. Its
ESP32 code sends the same JSON contract and §X-Device-Token§ header every
eight seconds. Its Eco, Heavy, and Alert Test modes generate **synthetic**
readings of 1–6 kWh, 8–20 kWh, and 26–40 kWh respectively. It is useful for a
local functional demonstration of the secured ingestion pipeline, but it is
not household data and must not be mixed with, or reported as, the recorded
household-data experiment.

---

## 6. Historical timestamp and data-timeline readiness

Source inspection shows that a valid `Instant` is forwarded through ingestion
and written by Usage Service using the event timestamp. The replay tool can
produce `current`, `rebased`, or original `source` timestamps.

However, no historical bulk POST/replay was performed in Task 0. The following
is therefore the correct current statement:

> **NOT VERIFIED — DO NOT CLAIM IN THE PAPER:** historical source timestamps
> have been accepted and persisted correctly at the intended five-house replay
> scale, or historical events will appear in a current-time dashboard window.

For a later dashboard/pipeline demonstration, `--timestamp-mode current` is
the appropriate live-like mode; original source time remains in the replay
receipt. `--timestamp-mode source` is suitable only for a clearly labelled
historical/forensic check because the dashboard's current window will normally
exclude 2014/2015 events.

---

## 7. Existing evidence, tests, and their limits

The repository records useful historical checks, including:

| Evidence area | Existing evidence | Correct interpretation |
|---|---|---|
| Baseline ML | `evidence/15_final_validation/ml_baseline_recovery_preparation_20261011.md` | Direct baseline artifact and container checks; not real-data evaluation. |
| Core live pipeline | `evidence/15_final_validation/docker_live_runtime_validation_20261011.md` | Dated ingestion-to-Influx and access-control validation. |
| Security/frontend regression | `evidence/15_final_validation/security_and_frontend_regression_20261011.md` | Local regression evidence; not a fresh runtime proof in this task. |
| Legacy ML tests | `evidence/05_ml_integration/ml_service_pytest_20261010.md` | Local/mocked test evidence, not end-to-end household replay. |
| Controlled-label verifier | `evidence/17_refit_anomaly_labelling/anomaly_dataset_verification.json` | Structural verification of a controlled-synthetic benchmark only. |

No historical score, metric, graph, paper claim, or headline number from these
files should be re-used as a result of the new household-data experiment until
the exact later stage that reproduces and verifies it.

---

## 8. Issues found before any experiment

### 8.1 Blocking issue — five-house credential/device-map mismatch

**What the audit found:**

* The current Compose default config maps only device `1` to a device token.
* `real_data_replay/replay_stream.py` accepts one `REPLAY_DEVICE_TOKEN` for a
  run, while its seed example maps five REFIT households to device IDs 1–5.
* The ingestion service deliberately rejects reuse of one configured token for
  multiple device IDs and requires the submitted token to match the payload
  device ID.

**Why this matters:** a five-house replay using the current seed map and one
token would not be authorized for devices 2–5. It must not be run as-is.

**What is needed before a five-house execution:** five verified local aggregate
meter devices, a documented household-to-device map, and a credential approach
that respects the exact device-bound token rule. The experiment must also use
accounts with alerts disabled or explicitly record intentional alert effects.

No workaround was implemented in Task 0.

### 8.2 Blocking issue — REFIT files/artifacts are not accessible to this audit runner

**What the audit found:** previous source/evaluation evidence is readable, but
the current process could not enumerate `data/refit/` contents or access the
optional REFIT model/evidence directories.

**What is needed:** restore/read-grant the intended source, processed, and
optional artifact directories to the actual execution identity, or provide a
fresh documented data location. Until then, only a dry-run plan can be audited;
the data pipeline must not be presented as freshly executed.

### 8.3 Scientific limitation — legacy model/data compatibility

**What the audit found:** the deployed legacy Random Forest uses a separate,
unprovenance-labelled 0–1-scale CSV and imputes four missing context fields.

**What is needed:** keep the legacy model's result separate from any REFIT
experiment. If the research goal is household-data anomaly evaluation, use the
explicit controlled REFIT protocol only after its artifact/data access and
evaluation boundary have been verified.

### 8.4 Reliability limitation — no ingress idempotency

**What the audit found:** ingress has no event identifier/idempotency key. A
network timeout can occur after acceptance.

**What is needed:** do not retry ambiguous transport failures by default;
record them as `TRANSPORT_UNCERTAIN`. Any later retry policy must be stated as
at-least-once delivery, never exactly-once processing.

---

## 9. Commands executed in this Task 0 audit

All commands below were read-only inspections; none sent telemetry, trained a
model, changed Compose state, or edited application code.

~~~powershell
rg --files -g "docker-compose*.yml" -g "*.java" -g "*.py" -g "*.json" -g "*.md" -g "*.csv"
docker compose config --services
docker compose config --quiet
docker compose ps --format json
rg -n ... docker-compose.yml
Get-Content ingestion-service/.../EnergyUsageDto.java
Get-Content ingestion-service/.../IngestionAuthorizationService.java
Get-Content usage-service/.../UsageService.java
Get-Content alert-service/.../AlertService.java
Get-Content ml-service/models/model_metadata.json
Get-Content ml-service/app/main.py
Get-Content ml-service/app/kafka_worker.py
Get-Content real_data_replay/README.md
Get-Content evidence/16_refit_dataset_audit/*.md
Get-Content evidence/17_refit_anomaly_labelling/*
Get-ChildItem data/refit, ml-service/models, evidence/*refit*
icacls data/refit; icacls ml-service/models/refit-controlled-v1
git status --short
~~~

The direct HTTP probe attempt was also read-only. It was blocked/timed out in
this agent execution environment and was not treated as an application failure
without an interactive user-side check.

---

## 10. Task 0 conclusion and controlled next step

Task 0 is complete. The project has a documented telemetry boundary, stream
topics, InfluxDB schema, user/device association, baseline ML route, isolated
experimental REFIT path, alert deduplication policy, and a dry-run-first replay
tool. The unresolved items are specific and actionable: multi-device
credentials/mapping, data/artifact access, and preservation of the scientific
boundary between the legacy model and controlled real-recorded-data experiment.

**Stop point required by the master plan:** Do not download, preprocess,
replay, train, enable REFIT, or edit the paper until Task 1 is explicitly
authorised.

### Exact paper-safe statement at this point

> The system baseline was audited before the proposed recorded-household-data
> experiment. The implementation supports controlled replay through the
> existing secured ingestion boundary, while data provenance, credential
> mapping, timestamp behavior, and downstream outcomes must be verified in
> subsequent experiment stages. No new household-data experiment result is
> reported by this audit.

