# AI Boundaries and Coding Rules

## Goal of These Rules

Any AI-assisted change must preserve the documented microservices architecture, avoid secret leaks, and be small enough to test independently.

## Allowed Technologies

- Java 21 (or the version already pinned by the Maven modules), Spring Boot, Spring Cloud Gateway, Spring Data, Spring Kafka, Spring AI, Maven, Lombok.
- React, Vite, TypeScript, Tailwind CSS, React Router, and a lightweight chart library such as Recharts for the dashboard.
- MySQL, InfluxDB, Apache Kafka, Docker, Docker Compose, Nginx/Caddy.
- JUnit 5, Mockito, Testcontainers where a service integration test needs infrastructure.
- GitHub Actions, GitHub Container Registry, Azure VM, Prometheus/Grafana, and one APM provider.

## Do Not Introduce Without Approval

- A second backend framework or language.
- A replacement database such as MongoDB, Supabase, Firebase, Appwrite, or Clerk.
- Kubernetes, Terraform, Helm, service mesh, or a managed Kafka cluster.
- Paid third-party APIs or SaaS services beyond the agreed Azure/Student Pack resources.
- A replacement authentication provider or unaudited authentication flow. The
  project uses its configured Keycloak realm, Gateway JWT validation, role and
  ownership checks; changes to that boundary require explicit review.

## Security Rules

- Never commit passwords, tokens, SMTP credentials, database URLs containing passwords, cloud keys, or private keys.
- Use environment variables and `.env.example`; `.env` must be in `.gitignore`.
- Rotate any credential that was previously committed or pasted in a tracked file before public deployment.
- Production services must not use `localhost` to communicate with another container.
- Do not expose MySQL, Kafka, InfluxDB, Prometheus, Grafana, or service ports publicly.
- Validate all request bodies and return safe error messages; never return stack traces or secrets.
- Configure CORS only for the deployed frontend origin and localhost development origin.
- Keep the API Gateway as the public HTTP boundary. Do not add host-published
  ports for private services merely to make local testing easier.
- Treat `X-Gateway-Authorization` and `X-Internal-Service-Token` as
  trusted internal credentials: callers must not be allowed to supply them,
  and the Gateway must strip privileged identity headers before forwarding.
- Keep `INTERNAL_GATEWAY_TOKEN` and `INTERNAL_SERVICE_TOKEN` in local or
  deployment secret configuration, never in tracked source. The present
  shared-token design is a local/private-boundary control, not a replacement
  for production mTLS, workload identity, per-service credentials, rotation,
  or replay protection.

## Coding Standards

- One responsibility per service; do not copy domain logic between services.
- Use constructor injection; do not use field injection.
- Use records for simple immutable DTOs where the existing module style permits it.
- Keep controllers thin, place business logic in services, and persistence in repositories.
- Use endpoint versioning: `/api/v1/...`.
- Use clear names: `EnergyUsageEvent`, `MonthlyBillForecast`, `StandbyLoadInsight`; avoid generic names such as `Data` or `Helper`.
- Document non-obvious public APIs with OpenAPI annotations.
- Keep commits small and scoped to a phase.

## Error Handling

- Validate invalid IDs, missing devices, malformed readings, negative energy values, and invalid date ranges before processing.
- Return a consistent API error object: timestamp, status, error code, message, request path, and correlation ID when present.
- Use global exception handlers in every HTTP service.
- Kafka consumers should log failed messages safely and use retry/dead-letter handling before silently losing data.
- The dashboard must show a useful empty/error state and retry action.

## AI-Specific Boundaries

- AI may draft code, tests, documentation, and optional insight wording.
- AI must not invent energy readings, billing rates, savings, customer data, API responses, or test results.
- Bill calculations, alerts, and standby detection must be deterministic Java logic with test coverage.
- If an AI insight provider is unavailable, return the calculated values and a non-AI fallback explanation.
- AI must inspect existing files before altering architecture or dependencies.
- AI must update `docs/06-ai-context-memory.md` after completing a meaningful phase.

