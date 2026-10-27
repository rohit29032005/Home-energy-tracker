# AI Context Memory

Append to this file after a completed phase or a material architecture decision. Do not replace older entries; keep a concise, chronological record.

## 2026-09-08 — Project baseline documented

- Project direction: retain the advanced event-driven microservices architecture rather than merge into a monolith.
- Current modules: API Gateway, User, Device, Ingestion, Usage, Alert, and Insight services.
- Current infrastructure: Docker Compose provides MySQL, Kafka, InfluxDB, Mailpit, and monitoring configuration; application services still need production containers and Compose entries.
- Target deployment: Azure Linux VM using Docker Compose, GitHub Actions, GitHub Container Registry, HTTPS reverse proxy, and one external APM provider.
- MVP novelty: Standby Energy Detective plus month-end Bill Shock Forecast.
- Important security work remains: remove and rotate hard-coded secrets; use environment variables; replace inter-service `localhost` URLs with Docker service names.

## 2026-09-08 — Phase 0: Repository Safety and Baseline Completed

- Created `.gitignore`, `.env.example`, and root `README.md`.
- Sanitized hard-coded development passwords (`Sahil_201_`) across all `application.properties` files and parameterized credentials using environment variable placeholders.
- Parameterized `docker-compose.yml` passwords and secret tokens.
- Standardized microservice port assignments (Gateway: 8080, User: 8081, Device: 8082, Ingestion: 8083, Usage: 8084, Alert: 8085, Insight: 8086). Fixed invalid `service.port` in `user-service`.
- Initialized `api-gateway` module with Maven `pom.xml`, `application.properties`, and `ApiGatewayApplication.java`.
- Verified clean Maven compilation (`mvn clean compile`) for all 7 microservices.

## 2026-09-08 — Phase 1: Containerize the Existing Backend Completed

- Created Dockerfiles for all 7 Spring Boot microservices (`api-gateway`, `user-service`, `device-service`, `ingestion-service`, `usage-service`, `alert-service`, `insight-service`).
- Added missing `spring-boot-starter-test` dependency in `insight-service` pom.xml.
- Added `spring.flyway.baseline-on-migrate=true` to `user-service`, `device-service`, and `alert-service` properties to baseline existing schemas.
- Extended `docker-compose.yml` with healthchecks for MySQL, Kafka, and InfluxDB, and container definitions for all 7 application microservices.
- Launched complete 12-container stack locally (`docker compose up -d`).
- Verified end-to-end event flow: Ingestion Service ➔ Kafka (`energy-usage`) ➔ Usage Service.

## 2026-09-09 — Phase 2: Complete Backend API Foundation Completed

- Fixed `api-gateway` WebFlux filter (`CorrelationIdFilter`) by implementing Spring Cloud Gateway `GlobalFilter` and `Ordered`.
- Fixed `api-gateway` exception handling (`GlobalExceptionHandler`) to handle WebFlux `ServerHttpRequest` and `WebExchangeBindException`.
- Verified consistent `ErrorResponse` DTO structure and `GlobalExceptionHandler` across all 7 microservices.
- Verified correlation ID (`X-Correlation-ID`) propagation and MDC log pattern formatting across all microservices.
- Verified Actuator (`/actuator/health`) and Prometheus metric endpoints across all services.
- Verified 100% clean Maven compilation for all 7 microservices (`api-gateway`, `user-service`, `device-service`, `ingestion-service`, `usage-service`, `alert-service`, `insight-service`).

## 2026-09-09 — Phase 3: Energy Intelligence Completed

- Created `TariffConfig` component with configurable tiered tariff slabs and fixed monthly supply charges.
- Created `BillCalculationService` with deterministic algorithms for bill estimation, 30-day month-end forecasting, and continuous baseline power (Watts) calculations.
- Added `BillForecastDto`, `ApplianceRankingDto`, `ApplianceRankingResultDto`, and `StandbyDetectiveDto` transferred models.
- Implemented **Standby Energy Detective** feature in `InsightService` to detect phantom idle loads, calculate monthly wasted kWh and cost, and assess risk levels (`LOW`, `MEDIUM`, `HIGH`).
- Implemented safe AI fallback in `InsightService` (`getSavingsTips` and `getOverview`) so deterministic analytics and template recommendations are returned seamlessly if the Ollama AI model is unavailable.
- Exposed REST endpoints in `InsightController`: `/bill-forecast/{userId}`, `/appliance-ranking/{userId}`, and `/standby-detective/{userId}`.
- Added JUnit 5 & Mockito unit tests (`BillCalculationServiceTest`, `InsightServiceTest`) with 100% pass rate (12 tests passed).

## 2026-09-09 — Phase 4: Dashboard Completed

- Created React 18 + TypeScript web dashboard initialized with Vite, Tailwind CSS, Lucide Icons, and Recharts in [`frontend/`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/frontend).
- Configured Vite development server proxy to target API Gateway (`http://localhost:8080`).
- Implemented household user switcher (`Header.tsx`) for switching active user profiles.
- Implemented executive metric cards (`SummaryCards.tsx`): total kWh, current cost ($), month-end bill shock forecast ($), and top appliance.
- Implemented dedicated **Standby Energy Detective** card (`StandbyDetectiveCard.tsx`) displaying baseline Watts, monthly phantom wastage, risk level badges (`LOW`, `MEDIUM`, `HIGH`), and an interactive recommendation checklist.
- Implemented Recharts visualization (`UsageCharts.tsx`): 7-day consumption area chart and appliance ranking bar chart.
- Implemented device management (`DeviceManagement.tsx`): appliance cards, add appliance modal form, and deletion handler.
- Implemented reading simulator controls (`SimulatorControls.tsx`): inject simulated smart meter readings into `ingestion-service` / Kafka topic.
- Implemented alert history view (`AlertHistory.tsx`) and AI / deterministic savings tips panel (`SavingsTips.tsx`).
- Verified 100% clean frontend compilation (`npm run build`) without errors.

## 2026-09-12 — Phase 5: Deployment and CI/CD Completed

- Created [`docker/nginx/nginx.conf`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/docker/nginx/nginx.conf) for production reverse proxying and static React SPA bundle hosting.
- Created [`frontend/Dockerfile`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/frontend/Dockerfile) multi-stage build (Node 20 -> Nginx alpine).
- Created [`docker-compose.prod.yml`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/docker-compose.prod.yml) container orchestration file with internal networking (`energy-net`), production volume mounts, restart policies, and hidden internal service ports.
- Created [`.env.production.example`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/.env.production.example) production environment variable template.
- Created [`.github/workflows/ci-cd.yml`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/.github/workflows/ci-cd.yml) GitHub Actions workflow running automated Java 17 Maven compilation/tests for all 7 microservices, Node 20 React build verification, and production Docker Compose configuration validation.
- Authored step-by-step Azure VM deployment & Let's Encrypt SSL guide in [`docs/08-azure-vm-deployment-guide.md`](file:///c:/Users/anju2/Desktop/Home-Energy-Tracker/docs/08-azure-vm-deployment-guide.md).

## Current Task

Phase 6 — Observability and Portfolio Readiness (Prometheus/Grafana dashboard setup, APM tracing, project demo recording).

## Known Issues / Blockers

- None currently. Phase 5 CI/CD pipeline and cloud deployment assets are fully established.

## 2026-09-23 — Local Stack Hardening and Verification

- Corrected the API Gateway compatibility baseline to Spring Boot 3.4.5 with Spring Cloud 2024.0.0, and verified that its Maven build succeeds.
- Reworked all seven Java Dockerfiles into source-build, multi-stage images; added a root `.dockerignore`; corrected the frontend build context; and aligned the Nginx `/api/` proxy with the gateway route prefix.
- Made Flyway in `user-service` the single owner of the shared MySQL schema. Added migrations for missing alert fields and a seeded demo household with five appliances.
- Made simulator traffic opt-in and conservatively rate-limited by default instead of generating a large continuous load.
- Added the user-listing API endpoint, aligned frontend device categories with the backend enum, and corrected ingestion timestamps to ISO-8601 strings.
- Added isolated test configuration for database, Kafka, and Influx-dependent application-context tests.
- Verified: frontend production build; deployable JAR packaging for all seven Java services; Compose syntax for local and production files; gateway test task (no tests); user service 2 skipped tests; device service 2 tests with 1 skipped; alert, ingestion, and usage services 1 passing test each; insight service 12 passing tests.
- Live end-to-end Compose verification remains blocked on this machine because Docker Desktop's engine cannot start due to a stale local `sailor-ingest.sock` endpoint. The Compose configuration and application artifacts are ready; do not describe the local 12-container flow or Azure deployment as verified until Docker is healthy and the flow has been rerun.

## Current Task

Phase 5.5 — restore Docker Desktop engine, run the 12-container stack, inject demo readings, and capture the live dashboard/API proof. Phase 6 observability begins after that verification.

## Known Issues / Blockers

- Docker Desktop's local engine is unavailable on this workstation. Frontend-only preview is live with safe fallback data at `http://localhost:3000`; it is not a live microservices result until Docker starts.

## 2026-09-25 — Live Local Demo Path Verified

- Corrected Docker Compose MySQL credential defaults: service containers now use the application account consistently, and the local MySQL healthcheck uses the same default root password as the database container.
- Corrected production Compose application services to use `MYSQL_PASSWORD` rather than the root password when connecting as the application account.
- Restored the local backend stack while preserving the Vite development frontend on port 3000. The Docker `frontend` service remains intentionally excluded in this mode because it would conflict with Vite on the same port.
- Verified live Gateway health (`200`), direct User/Device APIs, the exact Vite proxy route (`http://localhost:3000/api/v1/user`), ingestion (`201 Created`), Usage API, and Bill Forecast API.
- Added `docs/09-professor-demo-guide.md` with the current command sequence, expected outcomes, professor-facing explanation, honest feature boundaries, and troubleshooting.

## Current Task

Professor-ready live demo and documentation are available. Future work: production-image rebuild from the latest source, Azure VM provisioning/TLS, observability, and a live time-series chart endpoint.

## Known Issues / Blockers

- The local development frontend is live through Vite. For a container-only demo, stop Vite first, then start Docker Compose `frontend`; both bind port 3000 and cannot run simultaneously.
- The dashboard's seven-day line chart is currently illustrative client-side data. Usage, forecast, ranking, standby, device, and alert API endpoints are the live-backed demo proof points.

## 2026-10-11 — Private API Boundary and Authenticated Demo Hardening

- Extended the existing gateway-proof boundary to the Usage, Alert, and Insight
  HTTP APIs. Each now validates the trusted gateway credential before a
  gateway-injected owner header is trusted.
- Added matching owner checks for user-scoped Usage, Alert, and Insight paths.
  Gateway-admin routes remain owner-header-free only after public gateway role
  enforcement; background service tokens are rejected at Alert and Insight
  HTTP boundaries.
- Added a separate read-only Insight-to-Usage internal-service credential path.
  Usage and Alert continue to use the same background credential only for
  selected user/device context reads.
- Updated development and production Compose token wiring. Both Compose files
  parse successfully with Docker Compose static validation.
- Added focused local evidence: Gateway 8 tests, Usage 10 tests, Alert 11
  tests, and Insight 17 tests passed with zero failures/errors. The tested
  security scope and limitations are recorded in evidence/06_security/.
- Updated the React UI so normal users do not see the administrator-only
  account-create action. Added Keycloak refresh-token handling with
  pre-expiry refresh and one safe retry after HTTP 401. Frontend lint and
  production build pass; the Vite bundle-size advisory remains non-blocking.
- Corrected the professor and complete-verification guides to use the
  Keycloak user/admin roles, short-lived CLI tokens, gateway-only host access,
  and an ownership-valid automatic-alert scenario.

## Current Task (2026-10-11)

Run a live Docker/browser verification after the local Docker named-pipe
permission is available. The required follow-up evidence is a real Keycloak
login, a USER-versus-ADMIN browser check, a refresh-token exchange, and a
gateway-to-private-service route test.

## Known Issues / Blockers (2026-10-11)

- This validation session receives permission denied when accessing
  //./pipe/docker_engine. Static Compose validation and local source-level
  tests pass, but the current changes have not been verified by a running
  Docker network.
- The gateway and internal-service proofs remain shared static secrets. They
  are defense in depth, not per-service identity, mTLS, workload identity,
  rotation, or replay protection.

## 2026-10-11 — Live Docker Runtime Verification Completed

- Rebuilt and started the corrected `alert-service`. The root cause was
  Spring's ambiguous constructor selection in `AlertContextClient`; annotating
  the production constructor fixed startup. Targeted tests remain green.
- Restructured Alert Service test-only Maven dependencies into a normal-test
  profile that is disabled for the Docker image build. This avoids resolving
  the large Kafka/RocksDB test graph while building a runtime image, without
  changing normal local test execution.
- Verified live Keycloak OIDC discovery (`200`), API Gateway health (`200`),
  protected frontend proxy behavior (`401` without a bearer token), and the
  frontend static response (`200`).
- Verified live USER versus ADMIN and owner versus cross-household gateway
  authorization, controlled IoT device-token binding, and JWT-bound ingestion.
- Sent two controlled device-1 readings (`0.37 kWh` and `0.19 kWh`) and
  observed device usage move from `0.00 kWh` to `0.56 kWh` after asynchronous
  Kafka-to-Influx processing.
- Verified all five protected insight endpoints, deterministic AI fallback,
  admin-only alert dispatch, persisted alert status, and Mailpit SMTP
  acceptance. Verified a create/read/create-device/delete-device/delete-user
  CRUD sequence with cleanup.
- Recreated Prometheus and Grafana. Both readiness/login endpoints returned
  `200`; Prometheus reported the gateway plus all six Java services `up`.
  The optional ML target remains `down` because its container was not started.
- Full commands, exact statuses, and limitations are recorded in
  `evidence/15_final_validation/docker_live_runtime_validation_20261011.md`.

## Current Task (2026-10-11)

Prepare the professor-facing demonstration from the verified core local
stack, then separately repair optional ML model file access before claiming
live ML inference. Prometheus and Grafana were recreated and their public
endpoints were verified; do not overstate optional Grafana provisioning
warnings as a completed dashboard demonstration.

## Known Issues / Blockers (2026-10-11)

- The optional `ml-inference-service` remains excluded from the verified run
  because two Windows refit-model directories cannot be read by Docker. The
  core deterministic insight fallback is verified; live ML inference is not.
- Prometheus and Grafana were recreated successfully, but Grafana logged
  optional plugin-provisioning warnings. The service availability endpoints
  are evidence; a fully curated Grafana-dashboard result is not.

## 2026-10-11 — Baseline ML Docker Recovery Prepared

- Isolated the optional controlled-REFIT model directories as the remaining
  source-build context blocker for `ml-inference-service`.
- Updated the root `.dockerignore` to exclude only the two inaccessible
  optional REFIT directories; the persisted baseline Random Forest artefact
  remains included in the Docker build context.
- Set the Compose default `REFIT_CONTROLLED_EXPERIMENTAL_ENABLED=false` so a
  baseline-only local deployment is explicit and truthful until the separate
  experimental artifacts are restored.
- Static Compose configuration validation passed. The baseline artifact was
  locally deserialized and its application-level prediction helper scored one
  8-feature input; exact evidence and reproducible post-Docker commands are in
  `evidence/15_final_validation/ml_baseline_recovery_preparation_20261011.md`.
- A later endpoint recheck was unreachable from the validation shell, so this
  update makes no new live Docker, Kafka, alert, or REFIT runtime claim.

## 2026-10-11 — Live ML Container Verification Completed

- Docker Desktop recovered and the complete Compose stack was brought up.
  Gateway, frontend, Keycloak OIDC discovery, Prometheus readiness, and
  Grafana login each returned HTTP `200` from the host.
- `ml-inference-service` reported `UP` with baseline model
  `random_forest-csv-20261003T205417Z`; its legacy Kafka worker reported
  `connected` with no last connection error.
- A Wokwi-compatible three-field payload returned a successful baseline
  prediction (`anomaly: false`, probability `0.0`) and correctly listed the
  four missing contextual inputs as imputed. The controlled-REFIT route remains
  deliberately `DISABLED` pending separate experimental-artifact recovery.
- Exact request/response evidence is recorded in
  `evidence/15_final_validation/ml_baseline_recovery_preparation_20261011.md`.
- Keycloak is currently a local development-mode service. Static internal
  shared tokens remain defence in depth only, not per-service identity, mTLS,
  rotation, or replay protection.
