# Telemetry device-binding security validation

**Execution date:** 2026-10-10 (local source-level validation)

## Scope

The simulator-compatible `POST /api/v1/ingestion` route previously accepted a
valid JWT or global Wokwi token without binding the body `deviceId` to that
credential. The current implementation adds two layers:

1. The API gateway strips caller-supplied owner, gateway-proof, and
   internal-service headers for a machine token, or replaces the owner/proof
   values with the JWT `home_energy_user_id` claim and configured internal
   proof for a JWT request.
2. The ingestion service validates the JWT-originated gateway proof, then asks
   `device-service` to confirm that the user owns the device while forwarding
   the same trusted owner/proof pair. It checks that machine telemetry has an
   explicit `deviceId:token` mapping before it sends a Kafka event.

## Commands and observed results

```powershell
Set-Location api-gateway
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=GatewaySecurityFilterTest test
```

Observed result: **8 tests passed; 0 failures; 0 errors; 0 skipped.** The tests
confirm that a machine-token request cannot forward caller-supplied owner or
proof headers, an explicitly configured `deviceId:token` mapping is accepted
at the gateway, and a JWT request forwards a trusted user ID plus the configured
gateway proof. A JWT telemetry request and another protected gateway API
request are rejected when that proof is not configured.

```powershell
Set-Location ingestion-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=IngestionAuthorizationServiceTest,IngestionServiceAuthorizationTest,IngestionControllerAuthorizationTest,ParallelDataSimulatorAuthorizationTest' test
```

Observed result: **12 tests passed; 0 failures; 0 errors; 0 skipped.**

| Verified case | Observed result |
|---|---|
| JWT owner requests telemetry for an owned device | Device-service confirmation required before acceptance |
| JWT owner requests another user's device | Rejected with HTTP 403 semantics |
| Token mapped to the requested device | Accepted |
| Valid token mapped to a different device | Rejected with HTTP 401 semantics |
| Authorization failure | Kafka template receives no publish call |
| Successful authorization | One `energy-usage` Kafka send is invoked |
| Unauthorized machine credential through the controller | HTTP 401 is preserved rather than converted to HTTP 500 |
| Cross-owner JWT telemetry through the controller | HTTP 403 is preserved rather than converted to HTTP 500 |
| Duplicate token secret assigned to two device IDs | Rejected at configuration parsing time |
| Built-in parallel simulator | Sends its configured device ID and `X-Device-Token` header |
| Caller-supplied JWT owner header without the matching internal proof | Rejected with HTTP 401 before any device-service call |
| Enabled telemetry authorization without an internal gateway proof | Rejected at service construction time |

The source Compose configuration supplies `INTERNAL_GATEWAY_TOKEN` to
`api-gateway`, `ingestion-service`, `user-service`, and
`device-service`. The development file supplies an explicitly local default;
the production file requires the variable at deployment time. User/device
services use it to authenticate gateway-originated private calls, including the
ingestion service's JWT-ownership confirmation request.

`INTERNAL_SERVICE_TOKEN` is separate: it is supplied to `usage-service` and
`alert-service` for their read-only user/device context lookups, and to
`user-service` and `device-service` for validation. The Wokwi and simulator
device-token paths are deliberately unchanged and do not send either internal
credential.

## Boundaries

These are unit/source-level tests using mocked device-service and Kafka
dependencies. The private credentials are shared secrets, not mTLS or complete
service-to-service identity; token rotation, per-service identity, replay
resistance, and a compromised peer container remain outside their scope. The
tests also do not prove a live Keycloak issuer, Docker network, Kafka broker
delivery, device-token rotation, or end-to-end service forwarding. Docker was
unavailable on 2026-10-10, so those live controls remain **NOT YET MEASURED**.
