# Task 4D: Open Blockers and GO/NO-GO Decision

## Final decision

**NO-GO — the isolated identity and household-provisioning design is not ready for a future deployment-only smoke-test review.**

The source supports the intended security boundaries, but the required isolated identity service, application profile/device records, credentials, initialization approvals, and runtime test authorization do not yet exist. No Task 4D action attempted to bypass these conditions.

## Verified design strengths

1. API Gateway can validate a separate issuer/JWK-set pair through environment configuration (`api-gateway/src/main/resources/application.properties:7-11`).
2. Administrative profile creation is protected by `ADMIN` authorization (`api-gateway/.../SecurityConfig.java:38-47`).
3. Non-admin user ownership relies on a numeric `home_energy_user_id` token claim (`OwnershipGatewayFilter.java:75-105`).
4. Device machine telemetry is separately bound to exact device ID and device secret at Ingestion Service (`IngestionAuthorizationService.java:84-104`).
5. Duplicate device IDs and reused device secrets are rejected while configuration is parsed (`IngestionAuthorizationService.java:149-177`).
6. Task 4C has separate network/volume naming and passed static Compose validation without starting containers.

These strengths make an isolated future deployment feasible, but they are not evidence that it is currently configured or authorized.

## Blockers

| ID | Blocker | Evidence / reason | Required resolution before it can be closed | Owner/approval needed |
|---|---|---|---|---|
| B-01 | No isolated OIDC issuer exists. | Task 4C has no Keycloak service and only accepts externally supplied issuer/JWK URLs (`experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml:202-205`). | Approve either a separately operated isolated issuer or a new reviewed OIDC deployment overlay with separate persistent storage and network. | User/project owner plus deployment/security review. |
| B-02 | Existing development realm cannot be reused. | The checked-in `home-energy` realm/import contains development identities/credentials and dev-mode deployment configuration. | Create a new isolated realm design with independent roles, claim mapper, administrator, clients, signing material, and persistence; do not copy development accounts/secrets. | User/project owner plus identity administrator. |
| B-03 | Isolated issuer hostname and JWK route are unresolved. | Gateway must validate exact issuer/JWK pair; current static design has placeholders only. | Specify approved issuer URL, JWK-set route, network reachability, TLS/hostname posture, and configuration injection method. | Deployment/security review. |
| B-04 | Isolated dashboard callback origin is unresolved. | Task 4C has no frontend service; current browser callback behavior is tied to current origin (`frontend/src/services/auth.ts:160-205`). | Decide whether UI login is in scope. If yes, choose exact isolated UI origin and restrict redirect URI/web origins. If no, exclude optional household browser identities. | Project owner. |
| B-05 | No isolated administrator identity/bootstrap procedure exists. | Profile creation needs `ADMIN`; current development client/account must not be reused. | Approve a least-privilege manual admin or confidential provisioning-client workflow and new secrets. | Identity administrator/security review. |
| B-06 | H1/H2/H4 application profile and device IDs do not exist. | IDs are auto-generated; fresh Flyway migrations add seed records (`V1`, `V2`, `V5`, `V7`). | After approved isolated provisioning start, create records and capture returned IDs. Never infer from source household labels. | User approval for state creation. |
| B-07 | Full Task 4C startup has a device-mapping circularity. | Full config requires device token map before startup, but map needs device IDs created by provisioning. | Approve a separate provisioning-only isolated topology before full Task 4C telemetry deployment. Do not weaken security or use guessed IDs. | Project owner/deployment review. |
| B-08 | Exactly-one-device-per-household is not enforced in source. | `GENERAL` is supported, but inspected service/schema has no automatic cardinality rule. | Include manual pre/post creation cardinality and ownership checks in the approved provisioning runbook. | Provisioning operator/reviewer. |
| B-09 | Device secret issuance/rotation mechanism is not implemented. | Device mappings are configuration-only; no device-token API or secret manager is present. | Approve external generation, secure storage, injection, rotation, and redacted evidence workflow. | Security/project owner. |
| B-10 | Fresh persistent storage initialization is not authorized. | Isolated MySQL/InfluxDB/Keycloak/Kafka startup creates persistent state. | Approve named volumes, migration/seed behavior, identity persistence, retention, rollback, and cleanup ownership. | User/project owner. |
| B-11 | InfluxDB least-privilege post-bootstrap plan is unresolved. | Task 4C configuration has bootstrap/admin token configuration; a restricted runtime writer is preferable. | Approve/implement a scoped experiment writer credential after initialization, without disclosing it. | Deployment/security review. |
| B-12 | Kafka runtime hardening/reproducibility remains open. | Current static design has no verified SASL/TLS and uses an unpinned `latest` image reference. | Pin a reviewed image digest and decide whether transport authentication/encryption is required for the isolated scope. | Deployment/security review. |
| B-13 | No runtime smoke-test authorization exists. | Task 4D scope forbids containers, initialization, HTTP, and ingestion. | Obtain separate explicit approval for first start, then a separate approval for each state-changing/request test category. | User/project owner. |

## Required sequence after approvals

The order below is a design dependency order only. It is not authorization to execute.

1. Approve B-01 through B-05 and B-10 through B-12.
2. Design/review the provisioning-only isolated composition and its rollback boundary.
3. Start only that approved provisioning environment and initialize only its approved persistent stores.
4. Create three application profiles and exactly one `GENERAL` device per profile; record returned IDs and verify ownership/cardinality.
5. Generate three new device secrets outside source control, record references only, and prepare parity-checked Gateway/Ingestion configuration.
6. Review/update full Task 4C deployment configuration only under a separately approved change request.
7. Request explicit approval for the first deployment-only smoke test; do not send ingestion/replay data until a later explicit approval.

## What Task 4D did not do

- did not start Docker or any container;
- did not initialize MySQL, InfluxDB, Kafka, Keycloak, volumes, migrations, realm, or database;
- did not create profiles, users, devices, device IDs, Keycloak identities, roles, tokens, secrets, or mappings;
- did not query an API or send an ingestion event;
- did not modify Compose, application, model, authentication, or database source; and
- did not expose any secret value.

## Re-entry criterion

Task 4D may be revisited for a **deployment-design review** after B-01 through B-12 have approved, documented resolutions. It may advance to a **deployment-only smoke-test review** only when B-13 also has explicit authorization and the approved isolated provisioning design has produced verified, non-secret profile/device mapping evidence.
