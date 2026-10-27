# Live Docker Runtime Validation

**Execution date:** 2026-10-11  
**Environment:** local Docker Compose stack on Windows  
**Scope:** API Gateway, Keycloak, frontend proxy, user/device authorization,
ingestion, Kafka-to-Influx propagation, insights, alerting, Mailpit, and
temporary CRUD cleanup.

## Result summary

The corrected core stack was started and exercised through the public host
boundaries. API Gateway health and Keycloak OpenID Connect discovery both
returned HTTP `200`. The React/Nginx frontend returned HTTP `200` on port
`3000`; an unauthenticated frontend proxy request to a protected route
returned HTTP `401`, confirming that the proxy reaches the secured gateway
rather than bypassing it.

`alert-service` was rebuilt after correcting the Spring constructor selection
for `AlertContextClient`. Its runtime logs show successful application startup
and Kafka subscriptions to both `energy-alerts` and `anomaly-results`.

## Live authorization matrix

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| Unauthenticated `GET /api/v1/user/1` | 401 | 401 | Pass |
| USER reads assigned profile `1` | 200 | 200 | Pass |
| USER reads profile `2` | 403 | 403 | Pass |
| USER lists all profiles | 403 | 403 | Pass |
| ADMIN lists all profiles | 200 | 200 | Pass |

The JWTs and local demo passwords were held only in process memory; no token
or credential value is recorded in this evidence.

## Controlled ingestion and event-pipeline validation

Two controlled readings for the pre-provisioned demo device (`0.37 kWh` and
`0.19 kWh`) were sent through the public gateway. The device credential and
user JWT were not printed.

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| Telemetry without credentials | 401 | 401 | Pass |
| Device-1 credential used with device 2 | 401 | 401 | Pass |
| Bound device-1 telemetry | 201 | 201 | Pass |
| Owner JWT telemetry for device 1 | 201 | 201 | Pass |
| Second user JWT telemetry for device 1 | 403 | 403 | Pass |

The Usage API was polled after accepted writes to allow asynchronous Kafka
consumption and InfluxDB persistence. Device `1` usage changed from `0.00 kWh`
to `0.56 kWh`, meeting the controlled lower bound of `0.559 kWh` (the small
tolerance accounts for floating-point representation). This is live evidence
of the ingestion → Kafka → Usage Service → InfluxDB → Usage API path.

## Insight and alert validation

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| USER reads household-2 overview | 403 | 403 | Pass |
| Bill Forecast, Appliance Ranking, Standby Detective, Overview, Saving Tips for household 1 | 200 each | 200 each | Pass |
| USER sends administrator-only test alert | 403 | 403 | Pass |
| ADMIN sends a uniquely marked test alert | 200 | 200 | Pass |
| Mailpit REST API | 200 | 200 | Pass |

The live ranking response contained 10 entries and the standby response
reported `LOW` risk. Overview and saving-tips responses reported
`isAiGenerated: false`, which is valid deterministic fallback behavior when
the optional Ollama service is unavailable. No claim of live ML inference is
made by this record.

The uniquely marked manual alert was persisted as alert ID `492` and reported
`sent: true`; Mailpit accepted the SMTP message. The alert remains in the
local demonstration database because the public API intentionally has no
delete-alert endpoint.

## Temporary CRUD cleanup validation

An ADMIN token created a unique temporary application-profile row (ID `17`),
read it, created a temporary device (ID `316`), and deleted both through the
gateway:

| Operation | Expected | Actual | Result |
|---|---:|---:|---|
| Create profile | 201 | 201 | Pass |
| Read profile | 200 | 200 | Pass |
| Create device | 200 | 200 | Pass |
| Delete device | 204 | 204 | Pass |
| Delete profile | 204 | 204 | Pass |

The temporary profile and device were removed before this validation finished.
Creating an application profile does **not** create a new Keycloak login or
automatically pair a Wokwi meter; identity provisioning and device-credential
provisioning are distinct operational steps.

## Observability runtime status

Prometheus and Grafana were then recreated from the current Compose
configuration. Prometheus readiness (`/-/ready`) and Grafana's login route
both returned HTTP `200`.

Prometheus reported the API Gateway and all six Java application-service
targets as `up`. Its only `down` target was the optional
`ml-inference-service`, which was intentionally not started because its model
directory remains inaccessible to Docker on this workstation.

Grafana logs contained optional plugin-provisioning warnings during startup,
but the Grafana HTTP server bound successfully and the login page returned
`200`. The HTTP availability result is evidence that the service is up; it is
not a claim that every optional Grafana plugin is configured.

## Constraints observed during the run

- The optional `ml-inference-service` was not included in this live validation.
  Its Windows model directory contains inaccessible refit artifacts, so a
  source-build of that optional container remains blocked until file ownership
  or model artifact packaging is corrected.
- Keycloak is running in local development mode. The stack uses JWT role and
  ownership checks plus static internal credentials as defence in depth; it is
  not a production mTLS, workload-identity, credential-rotation, or replay
  protection deployment.
