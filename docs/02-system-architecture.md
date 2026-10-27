# System Architecture

## Architecture Style

Event-driven microservices, deployed as Docker containers. Synchronous REST is used for request/response operations; Kafka is used for energy usage events and alert events.

## Tech Stack

| Area | Selected technology |
| --- | --- |
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Identity provider | Keycloak local development realm, OpenID Connect Authorization Code + PKCE |
| Edge routing | Nginx or Caddy reverse proxy with HTTPS |
| API gateway | Spring Cloud Gateway / existing `api-gateway` module |
| Backend services | Java, Spring Boot, Spring Web, Spring Data |
| Event broker | Apache Kafka in KRaft mode |
| Relational data | MySQL 8 for users, devices, and alerts |
| Time-series data | InfluxDB 2 for timestamped energy usage |
| AI insight layer | Spring AI with a provider configured through environment variables; optional, never required for core calculations |
| Monitoring | Spring Boot Actuator, Prometheus, Grafana, and one external APM: Datadog **or** New Relic |
| Containers | Docker and Docker Compose |
| CI/CD | GitHub Actions + GitHub Container Registry + SSH deployment |
| Cloud target | Azure Linux VM, using GitHub Student Pack credits |

## Service Responsibilities

| Service | Responsibility | Data dependency |
| --- | --- | --- |
| API Gateway | Single public API entry point; validate Keycloak JWTs; enforce role and ownership rules; inject trusted downstream context after authorization | Routes to internal services |
| User Service | User profiles | MySQL |
| Device Service | Appliance registration and thresholds | MySQL |
| Ingestion Service | Validate incoming readings and publish `energy-usage` events | Kafka |
| Usage Service | Consume readings, write time-series usage, calculate aggregates, publish alerts | Kafka, InfluxDB, User/Device APIs |
| Alert Service | Consume alert events, persist history, send email | Kafka, MySQL, SMTP provider |
| Insight Service | Create deterministic forecast/standby calculations and optional AI wording | Usage Service API, optional AI provider |

## Runtime Topology

```text
Browser dashboard <--> Keycloak (OIDC login / PKCE)
        |
        | Bearer JWT
        v
HTTPS reverse proxy (public)
        |
        v
API Gateway (public through proxy only)
JWT validation + role/ownership authorization
        |
        | trusted gateway context only after authorization
        v
User   Device  Ingestion  Usage  Insight  Alert services
                    |       |
                    v       v
                  Kafka -> InfluxDB
                    |
                    v
              Alert Service -> MySQL / email

Prometheus -> service metrics -> Grafana
External APM -> traces/logs/alerts
```

## Network Rules

- The reverse proxy is the only component that accepts public HTTP/HTTPS traffic.
- Kafka, MySQL, InfluxDB, Grafana, Prometheus, and Spring services communicate on a private Docker network.
- Database, Kafka, and monitoring ports must not be exposed publicly in production.
- The gateway routes to Docker service names, never `localhost`.
- Docker Compose service DNS names are used, for example `kafka:9092`, `mysql:3306`, and `usage-service:8084`.
- The Gateway strips caller-supplied privileged identity headers and adds
  `X-Gateway-Authorization` only after public JWT, role, and ownership
  checks. Private downstream APIs reject unauthenticated direct callers.
- Background read-only service calls use `X-Internal-Service-Token`; both
  internal credentials remain private Compose-network secrets. They are shared
  development credentials and do not provide production mTLS, workload
  identity, per-service identity, rotation, or replay protection.

## Repository Structure Target

```text
Home-Energy-Tracker/
  api-gateway/
  user-service/
  device-service/
  ingestion-service/
  usage-service/
  alert-service/
  insight-service/
  frontend/
  docker/
    nginx/
    prometheus/
    grafana/
  docs/
  docker-compose.yml                 # local development
  docker-compose.prod.yml            # production topology
  .env.example                       # keys only, never secrets
  .github/workflows/deploy.yml
```

## Main App Flow

```text
Sign in through Keycloak -> Dashboard gets a Bearer JWT -> API Gateway validates
JWT/role/ownership -> Add an owned device -> Submit/simulate reading
-> Ingestion API -> Kafka energy-usage topic -> Usage Service -> InfluxDB
-> Dashboard refreshes owned usage, bill forecast, standby insight
-> threshold breach -> Kafka energy-alerts topic -> Alert Service -> email/history
```

## Key Decisions

- Keep microservices to demonstrate distributed systems and event-driven processing.
- Begin on one Azure VM with Docker Compose: this retains service separation without prematurely paying for managed infrastructure per service.
- Use MySQL for transactional records and InfluxDB only for energy time series.
- Keep Kafka single-node for the demo/portfolio deployment; describe it as a development-scale broker, not high availability.
- Make calculations deterministic first; AI may explain insights but cannot be the source of bill totals or alerts.
- Build the frontend after stable gateway APIs and use it only through the gateway.
- Keep authorization decisions at the Gateway and require downstream proof so
  a client cannot bypass the public boundary by supplying a forged owner
  header. Replace the current shared internal credentials with a production
  service-identity design before external deployment.

