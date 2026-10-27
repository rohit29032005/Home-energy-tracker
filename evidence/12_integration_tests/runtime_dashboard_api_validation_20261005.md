# Runtime Dashboard and Gateway Validation

**Validation time:** 2026-10-05, local Docker Compose environment  
**Scope:** authenticated dashboard APIs after the gateway response-body regression fix

## Defect corrected

`OwnershipGatewayFilter` and `IotIngestionTokenFilter` previously applied a
`switchIfEmpty(...)` fallback after `GatewayFilterChain.filter(...)`. A normal
gateway chain completes as `Mono<Void>`, so a successful proxied response was
mistaken for an absent principal and the gateway returned an empty response.

The fallback is now evaluated while the stream still represents the principal.
The regression tests in `GatewaySecurityFilterTest` passed **4/4** after the
change, including authenticated telemetry forwarding and preservation of a
successful owned-resource response.

## Live API results

A fresh `demo-user` Keycloak token was used for each request. The table records
the HTTP status and non-empty response size observed through
`http://localhost:8080`.

| Gateway route | Status | Response bytes | Non-empty JSON |
|---|---:|---:|---|
| `/api/v1/user/1` | 200 | 147 | Yes |
| `/api/v1/device/user/1` | 200 | 878 | Yes |
| `/api/v1/usage/1?days=1` | 200 | 1,112 | Yes |
| `/api/v1/alert/user/1` | 200 | 106,739 | Yes |
| `/api/v1/insight/bill-forecast/1?days=3` | 200 | 277 | Yes |
| `/api/v1/insight/appliance-ranking/1?days=3` | 200 | 1,596 | Yes |
| `/api/v1/insight/standby-detective/1?days=3` | 200 | 706 | Yes |
| `/api/v1/insight/saving-tips/1?days=3` | 200 | 649 | Yes |

The same runtime also returned `401` for a missing JWT and `403` for a
cross-user request; the full eight-case security record is stored in
`evidence/06_security/security_results.csv`.

## UI and platform health

The final sweep returned HTTP 200 from the frontend (`:3000`), gateway health
endpoint (`:8080/actuator/health`), Prometheus readiness endpoint (`:9090/-/ready`),
Grafana health endpoint (`:3001/api/health`), and Mailpit API (`:8025/api/v1/messages`).
All 17 configured Compose services were running at the time of this sweep.
