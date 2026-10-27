# Task 4C — Static Validation Report

**Date:** 2026-10-14  
**Method:** Non-mutating source/configuration inspection only. Docker lifecycle commands (`up`, `down`, `build`, `pull`, `restart`) were not run. No HTTP request, Kafka publication, database initialization, or secret retrieval occurred.

## Validation results

| ID | Check | Result | Evidence / interpretation |
|---|---|---|---|
| SV-01 | Compose syntax with an ephemeral non-secret validation environment | Pass | `docker compose --env-file .env.example -f .\\docker-compose.refit.yml config --quiet` returned exit code 0. The process supplied only temporary `static-validation-*` values; nothing was saved and no Docker resource was created. |
| SV-02 | Service allow-list | Pass | Resolved services: `api-gateway, device-service, influxdb, ingestion-service, kafka, mysql, usage-service, user-service`. |
| SV-03 | Prohibited services absent | Pass by direct inspection | No ML, Alert, Insight, frontend, Keycloak, Mailpit, simulator/replay, monitoring, or generator service is declared. |
| SV-04 | Shared container-name avoidance | Pass by direct inspection | The file contains no `container_name`; it cannot claim the fixed names used by existing Compose files. |
| SV-05 | Network/volume namespace | Pass by direct inspection | Only `refit-task4c-network` and `refit-task4c-*` named volumes are declared. |
| SV-06 | Host-port collision against current Compose definitions | Pass by direct inspection | Existing dev/prod Compose definitions do not declare host port 18080. The Task 4C gateway is loopback-only on 18080 by default. |
| SV-07 | Read-only host port snapshot | Pass at inspection time | `Get-NetTCPConnection -State Listen -LocalPort 18080` returned no listener. This is not a runtime reservation; repeat immediately before any approved start. |
| SV-08 | Original Compose preservation | Pass | Post-write SHA-256 values exactly match the pre-write values recorded in `config_diff_report.md`. |
| SV-09 | Placeholder-only secret template | Pass | All nine secret/configuration-gate variables in `.env.example` are blank. The check reported variable names only and printed no values. |
| SV-10 | Authentication fail-closed | Pass by direct inspection | Required interpolation remains for OIDC URLs, internal proofs, and device-token mapping; `SECURITY_ENABLED=true`, `INGESTION_AUTH_REQUIRED=true`, and legacy global tokens are disabled. |

## Runtime limits of this report

Static validation cannot prove Docker image build success, container readiness, network isolation at runtime, migration behavior, Keycloak/OIDC connectivity, credential validity, health endpoint behavior, or data-path correctness. No such claim is made here.

## Required static validation command

The validation was run from this directory with short-lived, process-scoped **non-secret sentinel strings**. They are syntactically valid only; the OIDC endpoint used the reserved `.invalid` domain and no Docker resource received the values. Do not save these strings to `.env` and do not use actual credentials during Task 4C.

```powershell
$env:REFIT_MYSQL_ROOT_PASSWORD = 'static-validation-root'
$env:REFIT_MYSQL_APP_PASSWORD = 'static-validation-app'
$env:REFIT_INFLUX_ADMIN_PASSWORD = 'static-validation-influx-password'
$env:REFIT_INFLUX_ADMIN_TOKEN = 'static-validation-influx-token'
$env:REFIT_INTERNAL_GATEWAY_TOKEN = 'static-validation-gateway-proof'
$env:REFIT_INTERNAL_SERVICE_TOKEN = 'static-validation-service-proof'
$env:REFIT_IOT_INGESTION_DEVICE_TOKENS = '101:static-validation-h1,102:static-validation-h2,104:static-validation-h4'
$env:REFIT_KEYCLOAK_ISSUER_URI = 'https://refit-oidc.invalid/realms/refit-experiment'
$env:REFIT_KEYCLOAK_JWK_SET_URI = 'https://refit-oidc.invalid/realms/refit-experiment/protocol/openid-connect/certs'
docker compose --env-file .env.example -f .\docker-compose.refit.yml config --quiet
```

The resolved configuration was additionally checked without printing its environment values. Results: the eight-service allow-list passed; prohibited service absence passed; no `container_name` value was present; public port exposure was limited to `127.0.0.1:18080:8080`; expected volumes were `refit-task4c-influx-data`, `refit-task4c-kafka-data`, and `refit-task4c-mysql-data`; and the only network was `refit-task4c-network`.

A preliminary local PowerShell assertion had an ordering/null-handling mistake while examining the resolved JSON; it was corrected and rerun. The Compose syntax command itself succeeded on its first execution and no Docker state changed during either inspection.

The real runtime configuration must instead be supplied through an untracked secret source only after explicit approval. A blank `.env.example` is designed to prevent accidental runtime deployment.

## Static validation conclusion

Configuration parsing alone is insufficient for a deployment decision. The missing isolated OIDC provider and unprovisioned H1/H2/H4 device-token map remain critical blockers. The Task 4C status is therefore **NO-GO — BLOCKERS REMAIN** even if syntax checks pass.
