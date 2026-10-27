# Task 4E: Staged Bootstrap Plan

## Scope, status, and safety boundary

This is a future execution design only. It does not authorize or perform any deployment, initialization, credential issuance, profile/device creation, secret generation, HTTP request, ingestion, replay, ML inference, alerting, or database action.

**Current status: NO-GO — BOOTSTRAP BLOCKERS REMAIN.** The stages below become executable only through the explicit approval gates in `approval_gates.csv`.

## Principle: two sequential isolated stages

The full Task 4C composition cannot safely provision itself because it requires the device-ID mapping first. The minimum source-compatible approach is two sequential stages:

1. **Provisioning-only stage:** isolated OIDC provider, the intended experiment-only MySQL state, User Service, Device Service, and API Gateway. It excludes Ingestion, Usage, Kafka, InfluxDB, Alert, Insight, ML, simulator, replay, and event generators.
2. **Full telemetry stage:** the approved Task 4C services, after returned IDs and independently generated device-secret bindings have been approved and prepared.

The same dedicated experiment-only MySQL database/volume must deliberately continue from stage 1 into stage 2. A second fresh database would not contain the generated profile/device IDs. This continuity is a future design decision and must not create a connection to the existing application database.

## Stage 0 — static configuration review (no runtime state)

**Purpose:** confirm that future deployment artifacts are structurally safe before any container is created.

**Required future checks:**

1. Review a new provisioning-only Compose/overlay artifact; Task 4E does not create it.
2. Verify its service allow-list contains only isolated OIDC, MySQL, User Service, Device Service, and Gateway.
3. Confirm no `INGESTION_AUTH_REQUIRED` service, Kafka, InfluxDB, Usage Service, ML, Alert, replay, simulator, or event generator is present in the provisioning stage.
4. Verify that all database, network, volume, issuer, and secret identifiers are experiment-specific and do not reference existing development resources.
5. Verify Gateway uses `SECURITY_ENABLED=true`, isolated issuer/JWK configuration, and a new gateway internal proof; it must not weaken route authorization.
6. Verify the provisioning-only Gateway does not inherit the Task 4C mandatory device-token interpolation. This is safe only because no Ingestion Service is included and API Gateway's `IotIngestionTokenFilter` can construct with an empty configured mapping while rejecting machine telemetry (`api-gateway/.../IotIngestionTokenFilter.java:54-128`).
7. Pin a reviewed Kafka image digest for the later full stage and define a Kafka readiness mechanism before any runtime approval.

**Gate:** G0.

## Stage 1 — approve and initialize only required persistent state

**Purpose:** initialize the minimum state required to create profiles/devices, while deferring unnecessary telemetry stores.

**Future order after explicit approval:**

1. Initialize durable isolated identity-provider storage and an experiment-only MySQL volume/database.
2. Do **not** initialize Kafka or InfluxDB in this stage. They are unnecessary for profile/device provisioning and would create extra persistent state before mappings exist.
3. Confirm MySQL health using the future approved evidence method. Task 4C has a MySQL health check at `docker-compose.refit.yml:18-22`; this proves infrastructure readiness, not schema migration completion.
4. Preserve a non-secret record of the exact isolated names/labels, approval ID, and retention owner.

**Gate:** G1.

## Stage 2 — isolated identity-provider bootstrap

**Purpose:** establish an independent issuer capable of supplying an administrator token for the secured application workflow.

**Required future sequence:**

1. Start/configure a new isolated OIDC provider, distinct from the existing development `home-energy` realm and its import data.
2. Establish the approved issuer URL and JWK-set route. Gateway expects configurable issuer/JWK values (`api-gateway/src/main/resources/application.properties:7-11`).
3. Create only the approved least-privilege bootstrap administrator identity with `ADMIN` role.
4. Verify, using redacted evidence, that the issuer in a future token equals the configured isolated issuer and that the role is represented in `realm_access.roles`, which Gateway maps to `ROLE_*` (`SecurityConfig.java:56-69`).
5. Do not create optional H1/H2/H4 browser identities unless the project later approves a UI demonstration. Machine telemetry does not require them.

**Gate:** G2.

## Stage 3 — start and validate the provisioning-only application path

**Purpose:** make the secure profile/device provisioning workflow ready without activating telemetry services.

**Required future order:**

```text
isolated MySQL healthy
    -> User Service application healthy and Flyway migration complete
    -> Device Service application healthy
    -> provisioning-only API Gateway application healthy and isolated OIDC-ready
```

This intentionally deviates from the current Task 4C parallel `depends_on` arrangement. User Service owns Flyway migrations (`user-service/src/main/resources/application.properties:9-12`), while Device Service has Flyway disabled (`device-service/src/main/resources/application.properties:9-11`). Merely observing MySQL health or container start is insufficient to prove the device table is ready.

All services in this stage must be private except the approved loopback gateway entry point. Future readiness evidence must be collected through approved internal/isolated methods; no health request is authorized by Task 4E.

**Gate:** G3 prerequisites, but this stage itself requires G1/G2 completion.

## Stage 4 — provision three profiles and aggregate devices

**Purpose:** obtain the real identifiers required for device-token bindings without making telemetry calls.

**Future approved workflow:**

1. Use only the isolated `ADMIN` gateway workflow to create one application profile each for REFIT H1, H2, and H4.
2. Record each returned database-generated profile ID in a non-secret experiment ledger.
3. For every returned profile ID, verify that no experiment aggregate device is already attached.
4. Create exactly one `GENERAL` aggregate-meter device through the supported gateway workflow.
5. Record each returned device ID and verify source-label-to-profile-to-device ownership/cardinality.
6. Ensure the planned experiment profiles have `alerting=false`, then verify it before the full stage. This is required because Usage Service contains a scheduled threshold path, even though Alert Service is excluded from Task 4C.

Source labels H1, H2, and H4 must never be treated as backend user/device IDs. Fresh migrations seed demo rows, so only returned IDs are valid evidence.

**Gate:** G3.

## Stage 5 — external device-secret generation and mapping preparation

**Purpose:** produce the exact three-entry mapping that the full Task 4C configuration requires.

There is **no existing backend endpoint or authorization mechanism that issues device secrets**. The inspected implementation accepts configuration-only mappings and validates them at startup (`IngestionAuthorizationService.java:67-81,149-177`). Therefore this stage requires a separately approved external secret-management process.

**Future approved sequence:**

1. Generate one independent high-entropy secret for each returned H1/H2/H4 device ID outside source control.
2. Put secret references, never values, in the experiment ledger.
3. Build a three-entry `deviceId:secret` mapping in the approved runtime secret channel.
4. Make the exact same mapping available to API Gateway and Ingestion Service; map identifiers and secret references must be parity checked without printing values.
5. Keep legacy global-token fallback disabled and grant any future replay process only the secret for its active household.

**Gate:** G4.

## Stage 6 — initialize remaining telemetry infrastructure and start full Task 4C

**Purpose:** start the approved isolated telemetry stack only after the secure mapping exists.

**Future order after explicit approval:**

1. Confirm the full Task 4C stage is configured to use the same approved experiment-only MySQL state from provisioning, not a fresh or shared database.
2. Initialize approved isolated Kafka and InfluxDB persistent state. InfluxDB has a Compose health check (`docker-compose.refit.yml:72-76`); Kafka has no health check and requires a separately reviewed readiness criterion.
3. Bring MySQL, then User Service/Flyway, then Device Service to confirmed application readiness.
4. Start Ingestion Service only after Kafka is ready, Device Service is application-ready, the device mapping is present, and the gateway-to-ingestion proof is present. It must fail closed if either mapping/proof is absent.
5. Start Usage Service only after Kafka, InfluxDB, User Service, and Device Service are ready. Its Compose `service_started` dependencies are not sufficient proof by themselves.
6. Start API Gateway only after downstream service application readiness and isolated issuer/JWK configuration are confirmed.
7. Verify no ML, Alert, Insight, simulator, replay, or generator container is present. Task 4C sets `SIMULATION_ENABLED=false` (`docker-compose.refit.yml:132-138`).

**Gate:** G5.

## Stage 7 — deployment-only smoke test (no data)

**Purpose:** confirm deployment, identity boundary, and isolation only.

The separately approved smoke test may verify redacted health/readiness, issuer/JWK reachability, role/ownership boundaries, volume/network isolation, and device-map recognition. It must not:

- post an ingestion payload;
- publish a Kafka event;
- run replay, Wokwi, simulator, or event generator;
- train or invoke ML;
- call Alert/Insight routes; or
- intentionally trigger a threshold condition.

The test must also prove no usage points, model calls, replay records, or alerts were created. Starting containers alone is not proof of this condition because Usage Service has scheduled code; all evidence must be captured through an approved, redacted runbook.

**Gate:** G6.

## Stop conditions

Stop and return to design review if any of these is observed in a future approved run:

- a reference to existing MySQL, Kafka, InfluxDB, Docker network/volume, development Keycloak issuer, realm, or credential;
- missing/invalid isolated issuer, JWK route, `ADMIN` role, gateway proof, or device-map parity;
- User Service migration incomplete when Device Service is used;
- mismatch between ledger IDs and configuration identifiers;
- an unexpected event, usage point, alert, model call, replay process, or simulator; or
- any raw secret in an artifact, command output, or log.
