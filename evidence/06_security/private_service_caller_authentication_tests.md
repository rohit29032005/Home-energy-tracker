# Private service caller-authentication validation

**Execution date:** 2026-10-10 (focused local tests; no Docker runtime)

## Purpose

User service and device service are private downstream services, but a private
network alone is not proof of the caller identity. This validation records the
current two-credential control that prevents a request with an absent, forged,
or caller-supplied owner header from being treated as an internal request.

## Credential roles

| Credential | Trusted caller and use | Accepted downstream scope |
|---|---|---|
| `INTERNAL_GATEWAY_TOKEN` carried in `X-Gateway-Authorization` | API gateway forwards an authenticated public API request; ingestion service uses the same proof while asking device service to confirm a JWT telemetry owner | Gateway-originated protected user/device requests and the JWT telemetry ownership confirmation |
| `INTERNAL_SERVICE_TOKEN` carried in `X-Internal-Service-Token` | Usage service and alert service retrieve context needed for background processing | Selected read-only user/device lookup paths only |

The two credentials must be configured as distinct secrets. A request that
carries both credentials is rejected. A background-service request must not carry
`X-Authenticated-User-Id` or a gateway proof. Device and user write paths
require a valid gateway proof; the internal service credential is not accepted
there.

The currently selected background read paths are device lookup by ID, device
list by user ID, and user lookup by ID. The user-list and write paths are not
background-service paths.

## Commands and observed results

```powershell
Set-Location api-gateway
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=GatewaySecurityFilterTest test
```

Observed result: **8 tests passed; 0 failures; 0 errors; 0 skipped.** These
mocked WebFlux tests confirm trusted-header replacement/stripping and fail
closed when the gateway proof is missing.

```powershell
Set-Location ingestion-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=IngestionAuthorizationServiceTest,IngestionServiceAuthorizationTest,IngestionControllerAuthorizationTest,ParallelDataSimulatorAuthorizationTest' test
```

Observed result: **12 tests passed; 0 failures; 0 errors; 0 skipped.** This
focused suite confirms the telemetry authorization and owner-confirmation
boundary described in
`telemetry_device_binding_tests.md`.

```powershell
Set-Location device-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=OwnershipVerifierTest,DeviceControllerPrivateCallerTest' test
```

Observed result: **8 tests passed; 0 failures; 0 errors; 0 skipped.** The
five controller tests confirm HTTP 401 before any device lookup for absent or
owner-header-only callers, HTTP 403 for a gateway owner mismatch, acceptance
of a correctly credentialed background read, and rejection of a
background-service create request.

```powershell
Set-Location user-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=OwnershipVerifierTest,UserControllerPrivateCallerTest' test
```

Observed result: **7 tests passed; 0 failures; 0 errors; 0 skipped.** The
four controller tests confirm rejection of a direct user-list call, background
read acceptance, background profile-create rejection, and gateway owner
mismatch rejection before a profile lookup.

~~~powershell
Set-Location usage-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B '-Dtest=DeviceClientInternalAuthenticationTest,UserClientInternalAuthenticationTest' test
~~~

Observed result: **3 tests passed; 0 failures; 0 errors; 0 skipped.** Mock HTTP
servers observed X-Internal-Service-Token on usage-service device-by-ID,
device-list-by-user, and user-by-ID context requests.

~~~powershell
Set-Location alert-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=AlertContextClientInternalAuthenticationTest test
~~~

Observed result: **2 tests passed; 0 failures; 0 errors; 0 skipped.** Mock HTTP
servers observed X-Internal-Service-Token on alert-service device and user
context requests.

## Verifier test coverage and source-enforced scope

| Control | Device service | User service |
|---|---|---|
| Valid gateway proof and matching owner | Observed accepted; cross-owner access rejected | Observed accepted; cross-profile access rejected |
| No credential or owner-header-only request | Observed rejected before ownership lookup | Observed rejected before ownership lookup |
| Forged gateway proof | Observed rejected | Implemented by the same verifier comparison; no separate forged-proof assertion in the focused verifier/controller run |
| Valid separate internal-service credential on a read caller | Observed accepted without an owner header | Observed accepted without an owner header |
| Internal-service credential on a write/create caller | Observed rejected by controller test | Observed rejected by controller test |
| Internal-service credential combined with an owner header | Observed rejected | Observed rejected |

The tests are focused verifier, controller, and mock-HTTP-client tests. They do
not constitute a service-network or Compose runtime test. In particular, this
record does not measure a live usage/alert client call, an end-to-end Kafka
flow, token rotation, or a request from a separate container.

## Limitations

The credential split reduces the former missing-header bypass and keeps
background lookup credentials distinct from gateway proof. It is not mTLS,
workload identity, per-service credentials, or network segmentation. The
single `INTERNAL_SERVICE_TOKEN` is shared by usage service and alert service,
so a compromise of either allowed caller can still impersonate the other at
the selected read endpoints until the token is rotated. Docker was unavailable
on 2026-10-10; no live Docker end-to-end assertion is made here.

## 2026-10-11 downstream API extension

The same private-caller model was extended to the usage, alert, and insight
HTTP APIs after this initial user/device record. Focused local validation
observed 10 usage authorization tests, 11 alert-service tests (including 4
controller authorization cases), and 17 insight-service tests (including 4
controller authorization cases and 1 outgoing Usage-client header case), all
with zero failures or errors. The full command evidence, exact scope, static
Compose parse, and the continuing shared-secret limitations are recorded in
[gateway_protected_downstream_services_20261011.md](gateway_protected_downstream_services_20261011.md).
