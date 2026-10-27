# Gateway-protected downstream service boundary validation

**Execution date:** 2026-10-11  
**Validation type:** focused local unit, MockMvc, and MockRestServiceServer tests; no Docker runtime

## Purpose

Private Docker-network placement does not itself prove which workload made an
HTTP request. This record extends the earlier user/device private-caller work
to the downstream usage, alert, and insight HTTP APIs. It records tests that
reject absent, forged, mixed, and cross-owner caller context before the
business-service method is invoked.

## Credential model

| Credential | Use | Where it is accepted |
|---|---|---|
| `INTERNAL_GATEWAY_TOKEN` in `X-Gateway-Authorization` | API gateway forwards an authorized browser/API request. | Gateway-protected HTTP APIs in user, device, usage, alert, and insight services; ingestion also uses it only for JWT telemetry ownership confirmation at device service. |
| `INTERNAL_SERVICE_TOKEN` in `X-Internal-Service-Token` | Background context reads. Usage/alert call user/device; insight calls usage. | Explicit read-only background paths only. |

Both secrets must be distinct. Gateway-protected routes reject a supplied
internal-service credential. Background read calls must be header-clean: they
must not include `X-Authenticated-User-Id` or
`X-Gateway-Authorization`. The design is static shared-secret defense in
depth, not mTLS or workload identity.

## Local test commands and observed results

~~~powershell
Set-Location usage-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=UsageAccessVerifierTest,UsageControllerAuthorizationTest' test
~~~

**Observed:** 10 tests passed; 0 failures; 0 errors; 0 skipped.

The verifier/controller tests demonstrate:

- a matching gateway owner can read its own usage;
- a gateway-admin request without an owner header is allowed;
- a valid, header-clean internal-service request can perform only the intended
  read;
- missing, forged, mixed, or owner-smuggled credentials return 401 before
  usage lookup;
- a valid gateway credential with a mismatched owner returns 403 before
  usage lookup.

~~~powershell
Set-Location alert-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=AlertControllerAuthorizationTest,AlertContextClientInternalAuthenticationTest,AlertServiceDeduplicationTest' test
~~~

**Observed:** 11 tests passed; 0 failures; 0 errors; 0 skipped. The run
contains 4 alert-controller authorization tests, 2 outgoing context-client
header tests, and 5 existing alert delivery/deduplication regression tests.

The controller cases demonstrate:

- every alert HTTP route requires valid gateway proof;
- `GET /alert/user/{userId}` allows only the matching owner or a
  gateway-admin request without an owner header;
- `GET /alert` and `POST /alert/test-send` reject a user-owner header,
  retaining gateway-admin semantics;
- the internal-service credential, alone or mixed with a valid gateway proof,
  is never an accepted alert HTTP credential.

~~~powershell
Set-Location insight-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B test
~~~

**Observed:** 17 tests passed; 0 failures; 0 errors; 0 skipped. The full run
contains 4 Insight controller authorization tests and 1 Usage-client
MockRestServiceServer test alongside the existing calculation tests.

The authorization-specific tests demonstrate:

- all five Insight routes reject a missing gateway credential before the
  Insight service is called;
- cross-owner access returns 403 before the service is called;
- matching owner and gateway-admin requests are accepted;
- the Insight-to-Usage request carries only
  `X-Internal-Service-Token`, not a user-owner or gateway-proof header.

## Static Compose configuration check

~~~powershell
$env:DOCKER_CONFIG='<project-root>\.docker-config-validation'
docker compose -f docker-compose.yml config --no-interpolate --quiet
docker compose -f docker-compose.prod.yml config --no-interpolate --quiet
~~~

**Observed:** both Compose files parsed successfully on 2026-10-11 after the
token configuration was extended to usage, alert, and insight services. The
development configuration supplies both appropriate tokens to these services;
the production configuration requires the secrets at deployment time.

This validates Compose syntax and environment wiring only. It does not start
containers or demonstrate a live inter-container request.

## Residual security limitations

1. The gateway and background credentials are shared static secrets. A
   compromised workload holding one can impersonate that caller class.
2. Read endpoints accepting the internal-service credential authenticate a
   caller class rather than a unique calling workload.
3. The downstream services receive a generic gateway proof and cannot
   independently prove the original JWT role. Gateway-admin semantics still
   rely on the public gateway's role enforcement.
4. There is no current live Docker, Keycloak, token-rotation, mTLS, workload
   identity, replay-resistance, or network-segmentation validation.

The appropriate next step is per-service identity with rotation and a
transport/workload identity mechanism, followed by live container-route
integration tests.
