# Home Energy Tracker ⚡

A containerized, event-driven microservices platform for household electricity monitoring. It ingests appliance readings, stores time-series usage, forecasts bills, surfaces the highest-consuming devices, and identifies persistent standby (phantom) loads. The normal dashboard mode is authenticated through the local Keycloak realm; it is not an anonymous dashboard.

> Deployment-ready means the repository contains Docker, Compose, CI, and Azure deployment guidance. A cloud deployment is not yet provisioned or verified.

## What makes the MVP different

**Standby Energy Detective** estimates low-activity baseline power, converts it into monthly wasted energy/cost, identifies likely device categories, and returns a practical saving checklist. It is paired with a deterministic **Bill Shock Forecast**, so the dashboard explains both *what is expensive* and *what can be changed*.

## Architecture

```text
Browser Dashboard (React + Nginx on HTTP) <----> Keycloak (:8180)
              |                         Authorization Code + PKCE
              | Bearer JWT
              v
       API Gateway (:8080)
       JWT, role, and ownership checks
  +----------+----------+----------+----------+----------+
  |          |          |          |          |          |
User      Device    Ingestion    Usage      Insight     Alert
(:8081)   (:8082)    (:8083)   (:8084)     (:8086)    (:8085)
                         |          |
                         v          v
                      Kafka ----> InfluxDB
                         |
                         v
                   Alert events -> Mailpit / MySQL
```

## Services

| Service | Responsibility |
| --- | --- |
| API Gateway | Public API boundary: Keycloak JWT validation, role and ownership authorization, and trusted context injection for protected downstream APIs |
| User / Device | Household profiles and registered appliances in MySQL |
| Ingestion | Accepts readings and publishes `energy-usage` events |
| Usage | Consumes usage events and writes InfluxDB time-series data |
| Insight | Bill forecast, ranking, and Standby Energy Detective |
| Alert | Threshold alert history and email delivery through Mailpit |

## Local authentication and authorization

- Authentication is enabled by default in the frontend (`VITE_AUTH_ENABLED=true`). The dashboard signs in against the local Keycloak realm using Authorization Code with PKCE and keeps its browser session refreshed while the refresh token remains valid.
- The gateway validates Bearer JWTs before forwarding protected API requests. A regular `USER` is constrained to the `home_energy_user_id` ownership claim in the token; the local `ADMIN` role is required for household-profile administration, the full alert list, and manual alert-test sending.
- User, device, usage, alert, and insight services are private Compose-network services. The gateway strips caller-supplied privileged headers and injects a gateway proof only after its public authorization checks. Background service reads use a separate internal-service token.
- The internal gateway and service tokens are development shared secrets, not mTLS, workload identity, per-service identity, token rotation, or replay protection. Replace them with an appropriate production secret-management and service-identity design before any non-local deployment.

## Run locally

Prerequisites: Docker Desktop with its engine running, Java 17+ and Maven for direct service work.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

In PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
```

Open these local tools once the stack is healthy:

| Tool | Local URL |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API Gateway | http://localhost:8080 |
| Keycloak | http://localhost:8180 |
| Kafka UI | http://localhost:8070 |
| InfluxDB | http://localhost:8072 |
| Mailpit inbox | http://localhost:8025 |

For an intentional frontend-only **offline fallback preview** while the backend is unavailable, opt out of authentication before starting Vite:

```bash
cd frontend
VITE_AUTH_ENABLED=false npm run dev
```

In PowerShell:

```powershell
cd frontend
$env:VITE_AUTH_ENABLED = 'false'
npm run dev
```

This mode is for a clearly labelled local/demo preview only: it renders fallback data and does not represent a live backend result or exercise Keycloak, gateway authorization, or protected APIs. To return to normal secure local development, start a new Vite process without `VITE_AUTH_ENABLED=false` (or run `Remove-Item Env:VITE_AUTH_ENABLED` in PowerShell before `npm run dev`).

## Current delivery status

- [x] Repository safety, environment templates, and architecture documentation
- [x] Dockerfiles for all seven Java services and frontend Nginx build
- [x] Shared MySQL schema migrations, seeded demo household, and rate-limited simulator defaults
- [x] Keycloak JWT authentication, role/ownership authorization, and protected private-service caller checks
- [x] Gateway, dashboard, deterministic energy intelligence, and explicitly opt-in local API fallback preview
- [x] CI checks and production Compose validation configuration
- [ ] Live end-to-end Compose verification in this agent environment — not run because access to Docker Desktop's named pipe was denied
- [ ] Azure VM deployment and TLS certificate provisioning
- [ ] Observability dashboard and tracing

The full project plan, AI rules, architecture, and progress log are in [`docs/`](docs/). For a professor-ready live walkthrough, use the [Professor Demo Guide](docs/09-professor-demo-guide.md). For the complete command-by-command verification checklist, use the [Complete Feature Verification Guide](docs/10-complete-feature-verification-guide.md).
