# Development Phases

## Working Principle

Complete, test, and document one phase before beginning the next. A phase is done only when its checkbox items, local verification, and memory log entry are complete.

## Phase 0: Repository Safety and Baseline

- [x] Add `.gitignore`, `.env.example`, and a root `README.md`.
- [x] Remove hard-coded secrets from every tracked configuration file.
- [x] Rotate exposed development credentials before the repository becomes public.
- [x] Standardize all service ports and replace invalid `service.port` configuration with `server.port`.
- [x] Add local and production Spring profiles/environment-variable configuration.
- [x] Confirm every Maven module builds independently.

## Phase 1: Containerize the Existing Backend

- [x] Add a production Dockerfile to each Spring Boot service.
- [x] Extend Docker Compose to include all application services.
- [x] Configure private Docker networking and service-name URLs.
- [x] Add health checks and startup dependencies.
- [x] Run the complete Kafka, MySQL, InfluxDB, and service stack locally.
- [x] Verify the ingestion -> Kafka -> usage persistence path.

## Phase 2: Complete Backend API Foundation

- [x] Implement and test API Gateway routes.
- [x] Add consistent request validation and error response handling.
- [x] Confirm User, Device, Usage, Ingestion, Alert, and Insight APIs through Swagger/Postman.
- [x] Add Spring Boot Actuator health and Prometheus metric endpoints.
- [x] Add correlation IDs to request/event logs where practical.

## Phase 3: Energy Intelligence

- [x] Define tariff configuration and deterministic monthly bill estimate.
- [x] Implement month-end bill forecast from the current consumption rate.
- [x] Implement appliance ranking by usage.
- [x] Implement Standby Energy Detective with documented baseline assumptions.
- [x] Add unit tests for all calculations and edge cases.
- [x] Keep optional AI-generated explanations behind a safe fallback.

## Phase 4: Dashboard

- [x] Create the React + TypeScript frontend.
- [x] Integrate Keycloak Authorization Code + PKCE login and secure-by-default
  frontend token refresh.
- [x] Gate account creation in the frontend and Gateway so a regular USER
  cannot perform administrator-only profile actions.
- [x] Build dashboard summary cards: total kWh, estimated bill, forecast, and top device.
- [x] Build device management and energy-reading/simulator controls.
- [x] Build usage chart, alert history, and standby insight UI.
- [x] Add responsive, loading, empty, and error states.

## Phase 5: Deployment and CI/CD Preparation

- [ ] Provision an Azure Linux VM and secure SSH access.
- [x] Prepare Docker, Docker Compose, production environment templates, and
  Nginx reverse-proxy configuration (`docker/nginx/nginx.conf`).
- [ ] Configure the deployed VM firewall, DNS, HTTPS certificate, and
  deployment-time secret store.
- [ ] Deploy with `docker-compose.prod.yml` using provisioned production
  environment values.
- [x] Add GitHub Actions build/test/image-publish/deploy workflow (`.github/workflows/ci-cd.yml`).
- [x] Create step-by-step Azure VM deployment guide (`docs/08-azure-vm-deployment-guide.md`).
- [ ] Verify HTTPS and confirm private ports are not accessible from the
  internet after a real deployment.

## Phase 6: Observability and Portfolio Readiness

- [ ] Add Prometheus/Grafana dashboards for services and energy events.
- [ ] Configure Datadog **or** New Relic for one end-to-end trace path.
- [ ] Configure uptime/health alerting.
- [ ] Add architecture diagram, screenshots, API documentation, and deployment instructions to README.
- [ ] Record a short project demo covering the Kafka event flow and Standby Energy Detective.

## Phase 7: Authentication and Private-Boundary Hardening

- [x] Define the local Keycloak identity-provider, USER/ADMIN role, and
  `home_energy_user_id` ownership-claim strategy.
- [x] Add browser login, Gateway JWT validation, role checks, and
  user/device/usage/alert/insight ownership enforcement.
- [x] Strip caller-supplied privileged headers at the Gateway and require
  internal gateway/service credentials at protected private HTTP boundaries.
- [ ] Replace shared internal tokens with rotating per-service identities,
  workload identity, or mTLS for a non-local deployment.
- [ ] Rerun browser, Keycloak, and inter-container authorization tests against
  a live Docker deployment before making an end-to-end security claim.

