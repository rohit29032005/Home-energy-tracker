# Gateway security unit validation

**Execution date:** 2026-10-11 (local environment)

Command executed from `api-gateway` with Java 17:

```powershell
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=GatewaySecurityFilterTest test
```

Result: **8 tests passed; 0 failures; 0 errors; 0 skipped.**

| Verified control | Observed result |
|---|---|
| POST `/api/v1/ingestion` without a JWT or valid `X-Device-Token` | Rejected with HTTP 401 by `IotIngestionTokenFilter` |
| POST `/api/v1/ingestion` with the configured machine token | Forwarded after caller-supplied owner, gateway-proof, and internal-service headers are stripped |
| POST `/api/v1/ingestion` with a token from an explicit `deviceId:token` mapping | Forwarded after caller-supplied owner, gateway-proof, and internal-service headers are stripped |
| Authenticated JWT on POST `/api/v1/ingestion` | Forwarded with the JWT user ID and configured gateway-to-ingestion proof after caller-supplied privileged headers are stripped |
| Authenticated JWT on POST `/api/v1/ingestion` when no internal proof is configured | Rejected with HTTP 401 before the proxy chain |
| Authenticated user 1 requests `/api/v1/device/user/2`, then `/api/v1/device/user/1` | Cross-user request is rejected with HTTP 403; matching request is forwarded with trusted owner and gateway-proof headers |
| Authenticated non-admin and administrator request an administrative collection/action path | Non-admin requests to `/api/v1/user`, `/api/v1/alert`, and `/api/v1/alert/test-send` are rejected with HTTP 403; an administrator request is forwarded without an owner header and with the trusted gateway proof |
| Authenticated request to a protected non-ingestion API path when no gateway proof is configured | Rejected with HTTP 403 before forwarding |

## Credential scope after the private-caller split

`INTERNAL_GATEWAY_TOKEN` is supplied to the API gateway, ingestion service,
and every gateway-protected downstream service (user, device, usage, alert,
and insight). For protected non-ingestion API paths, the
gateway removes caller-supplied `X-Authenticated-User-Id`,
`X-Gateway-Authorization`, and `X-Internal-Service-Token` headers before
attaching the configured `X-Gateway-Authorization` proof. The telemetry
filter uses the same proof only for JWT-originated telemetry; machine-token
telemetry has its caller-supplied owner/proof headers removed.
The user, device, usage, alert, and insight services validate that proof
before accepting a gateway-originated private request. The ingestion service
also presents it when it asks device service to confirm JWT telemetry
ownership.

`INTERNAL_SERVICE_TOKEN` is a distinct credential. Usage service and alert
service use it for read-only user/device context lookups, and insight service
uses it for a read-only usage lookup. It is not sent through the public gateway
and is not a substitute for the gateway proof, a browser JWT, or a Wokwi
device token.

This remains a static shared-secret defence-in-depth measure, not mutual TLS
or a complete workload-identity system. Token rotation, per-service identity,
replay resistance, and compromise of an allowed container on the same network
remain outside this test.

The focused gateway test was executed against local mocked WebFlux exchanges;
it does not start Keycloak or a browser. On 2026-10-10, `docker compose ps
--all` could not connect to `//./pipe/docker_engine`, so live Keycloak
login, JWT signature validation against a running issuer, expired-token
handling, browser authentication, and Docker end-to-end forwarding remain
**NOT YET MEASURED**.
