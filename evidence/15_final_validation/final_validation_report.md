# Final Runtime Validation Report

**Validation date:** 2026-10-05  
**Environment:** local Docker Compose deployment

## Outcome

On the dated **2026-10-05** local deployment, the stack was operational and had
evidence for authenticated-telemetry baseline behaviour, anomaly processing, alert delivery, dashboard APIs,
observability, performance, and controlled service recovery. This report
summarizes measured runs; it does not make a production-capacity claim.

## Runtime health

- All **17 configured Compose services** were running in the final health sweep.
- HTTP 200 was observed from the frontend, API-gateway health endpoint,
  Prometheus readiness endpoint, Grafana health endpoint, and Mailpit API.
- Prometheus recorded **8 active scrape targets**, all with health `up`.
- The deployed gateway returned non-empty authenticated JSON for all eight
  principal frontend data routes. Details:
  `evidence/12_integration_tests/runtime_dashboard_api_validation_20261005.md`.

## Security validation

The historical security suite passed **8/8** cases:

- owned-user access: 200;
- missing or malformed JWT: 401;
- cross-user user/device access: 403;
- administrator listing: 200;
- machine-token telemetry ingestion: 201; and
- an actually expired JWT: 401.

Evidence: `evidence/06_security/security_results.csv` and
`evidence/06_security/security_results.json`.

This dated deployment evidence predates the 2026-10-10 device-bound token and
gateway-proof hardening. Those newer controls are supported by focused local
source-level tests in `evidence/06_security/`; they were not re-executed
against a running Docker route because the Docker daemon was unavailable.

### Post-validation private-caller hardening (2026-10-10 to 2026-10-11)

After the dated runtime deployment, the private user/device service boundary
was strengthened with a split between `INTERNAL_GATEWAY_TOKEN` for
gateway-originated protected calls and `INTERNAL_SERVICE_TOKEN` for
background read-only context lookups. The 2026-10-11 extension also protects
the Usage, Alert, and Insight HTTP APIs themselves rather than relying only on
the gateway route. Focused local tests passed: **8** API-gateway filter
tests, **12** ingestion authorization tests, **8** device-service
verifier/controller tests, **7** user-service verifier/controller tests,
**10** Usage authorization tests, **3** Usage outgoing-token tests, **11**
Alert-service tests (including 4 controller authorization tests), and **17**
Insight-service tests (including 4 controller authorization tests and 1
Usage-client header test). The tests show that absent, forged, mixed, or
cross-owner private-caller requests are rejected at the filter/verifier
boundary and that background clients attach the separate credential; they do
not establish a live Docker request path, browser login, Keycloak signature
validation, or inter-container enforcement. See
`evidence/06_security/private_service_caller_authentication_tests.md` and
`evidence/06_security/gateway_protected_downstream_services_20261011.md`.

### Frontend authorization alignment (2026-10-11)

The authenticated frontend now hides account creation from a regular USER,
retains it for an administrator, and defensively rejects a non-administrator
create invocation. It also refreshes a stored Keycloak refresh token before
the short local access-token lifetime expires and retries a protected request
once after a successful refresh. Frontend lint and production build passed;
the Vite bundle-size advisory remained a warning only. No live browser
USER-versus-ADMIN or refresh-token interaction was rerun while Docker was
unavailable. See
`evidence/12_integration_tests/frontend_authorization_ui_validation_20261011.md`.

## Controlled end-to-end result

The successful dated record is
`evidence/13_end_to_end/review2_e2e_results_20261005-214326.json`.

- Synthetic telemetry through the simulator-compatible ingestion endpoint
  reached usage and insight services in **3.79 seconds**.
- The isolated analytics case measured **1.50 kWh**, **$0.18** current estimated
  cost, **15.00 kWh** projected monthly usage, and **$11.80** projected monthly
  cost; all seven configured analytics assertions passed.
- The alert case submitted **1.00 kWh** against a **0.10 kWh** threshold,
  observed a persisted `THRESHOLD` alert with `sent = true` in **13.64 seconds**,
  and verified a newly created matching Mailpit email.
- The controlled synthetic alert user was disabled again at the end of the run
  (HTTP 200) to prevent continuing scheduler-driven notifications.

## Alert deduplication

Two identical high-energy records for device 1 produced one stored ML anomaly
alert and one explicit suppression log entry within the 15-minute window. A
later Mailpit delivery was also observed. Evidence:
`evidence/07_alert_deduplication/live_deduplication_validation_20261005.md`.

The final Prometheus snapshot reported suppression counters of **1** for
`ML_ANOMALY` and **30** for `THRESHOLD`; these are cumulative counters from the
running local environment, not rates per test.

## Performance result

The real local k6 run submitted **450** authenticated ingestion requests over
the configured ramp to 10 requests/s. All 450 acceptance checks passed; the
measured HTTP failure rate was **0.00%**, mean duration **39.44 ms**, and p95
duration **109.77 ms**. Full raw and summary results are retained in
`evidence/09_performance/`; see
`evidence/09_performance/load_test_summary_20261005.md` for the exact scope and
limitation.

## Resilience result

- A controlled **Mailpit** outage recorded continued ingestion handling and
  automatic container recovery (`recovered=True`).
- A controlled **ML inference service** outage returned ingestion HTTP 201
  during the fault, and the script later recorded container-state recovery.
  The captured evidence does **not** establish post-restart Kafka reconnection
  or unique event processing.

Evidence: `evidence/10_resilience/fault-mailpit-20261005-215216.md` and
`evidence/10_resilience/fault-ml-inference-service-20261005-215300.md`.
These runs prove only the recorded acceptance and container-state recovery
behavior; they do not claim end-to-end message delivery, Kafka replay, or
application readiness through every possible outage.

## Implementation note

The API-gateway ownership and IoT token filters were corrected to avoid treating
the normal empty completion of a reactive proxy chain as an absent principal.
The focused regression suite passed **4/4** tests. The standard source-building
Dockerfile remains present. A `Dockerfile.local` fallback was added solely for
this session because the Docker builder had a transient Maven DNS failure; it
packages the locally tested Maven artifact rather than bypassing tests.
