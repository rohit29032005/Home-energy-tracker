# Task 4E: Isolation Verification Plan

## Scope

This document specifies future verification evidence. It does not inspect a live Docker environment, make requests, access credentials, or create resources. All runtime checks require separate approval after the relevant gate passes.

## 1. Static isolation already verified for Task 4C

| Isolation layer | Static evidence | Expected boundary |
|---|---|---|
| Docker network | `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml:220-223` | Only `refit-task4c-network` is declared for the full telemetry stage. |
| MySQL volume | `docker-compose.refit.yml:26-29,225-231` | Named experiment-only MySQL storage, `refit-task4c-mysql-data`. |
| Kafka volume | `docker-compose.refit.yml:54-59,225-231` | Named experiment-only Kafka storage. |
| InfluxDB volume | `docker-compose.refit.yml:78-83,225-231` | Named experiment-only InfluxDB storage. |
| Host exposure | `docker-compose.refit.yml:185-189` | Only API Gateway is loopback-bound; MySQL, Kafka, InfluxDB, User, Device, Ingestion, and Usage services are not host-published by this composition. |
| Private DNS destinations | `docker-compose.refit.yml:92,112,132,136,157-163,192-195` | Services use task-local DNS names such as `mysql`, `kafka`, `influxdb`, `user-service`, and `device-service`. |
| Existing OIDC exclusion | `docker-compose.refit.yml:202-205` | Gateway needs a future isolated issuer/JWK pair; it must not use the existing development provider. |
| Excluded downstream routes | `docker-compose.refit.yml:197-200` | Alert and Insight service routes fail closed inside the gateway container and are not part of the experiment scope. |

Static configuration is not runtime proof. It does not demonstrate which volumes/networks an actual container would attach to, nor that an isolated issuer/JWK route is reachable.

## 2. Future runtime verification matrix

| Verification area | Future approved evidence collection | Pass condition | Stop condition |
|---|---|---|---|
| Compose allow-list | Redacted resolved Compose service list and image manifest for each stage. | Provisioning stage includes only approved identity/MySQL/User/Device/Gateway components; full stage includes only Task 4C allow-list. | Any ML, Alert, Insight, replay, simulator, generator, existing-stack, or unapproved service appears. |
| Network attachment | Inspect the network attachments of each approved isolated container. | Only the named experiment network plus an explicitly approved isolated identity path is present. | Attachment to `energy-net`, a root/default development network, or any unapproved shared network. |
| Volume/mount ownership | Inspect mounts and named volume identifiers for each container. | Only approved experiment-specific volumes are mounted; no host path or existing service volume is attached. | Existing MySQL/Kafka/InfluxDB/Keycloak volume or unknown host mount appears. |
| MySQL database identity | Use a least-privilege read-only metadata check after initialization approval. | Database name, schema/Flyway history, and service endpoint match the experiment-only plan; no existing database is referenced. | Existing application database name, endpoint, user, or volume appears. |
| InfluxDB identity | Use approved read-only metadata evidence. | Experiment-only organization, bucket, retention policy, and endpoint match plan. | Existing organization/bucket/token endpoint is referenced. |
| Kafka identity | Use approved broker metadata evidence, without event production. | Fresh approved cluster identity, expected isolated broker endpoint, no pre-existing consumer group/topic reuse. | Existing broker, topic, group, or host port is contacted. |
| OIDC issuer and JWK route | Inspect configured URL identifiers and obtain a redacted future token claim summary only after identity approval. | Token `iss` equals configured isolated issuer; JWK route is isolated/reachable; expected `ADMIN` or `USER` role is present. | Existing development issuer/realm, unexpected audience/issuer, or credentials exposed in evidence. |
| Gateway/Ingress mapping parity | Compare device ID list plus opaque secret-reference labels in the approved secret store. | The same three returned device IDs are represented in Gateway and Ingestion mappings; each has one unique reference. | Missing ID, duplicate ID/reference, unknown ID, or raw secret appears. |
| Profile/device ownership | Use supported authenticated application reads after provisioning approval. | H1/H2/H4 source label maps to a returned profile ID and exactly one returned `GENERAL` device ID. | A REFIT label is treated as a backend ID, a duplicate device exists, or an existing profile/device is touched. |
| No-event smoke scope | Inspect redacted system state before and after smoke test. | No ingestion requests, Kafka records, Influx points, model calls, replay artifacts, or alert events are produced. | Any event, point, model invocation, simulator activity, or alert path is observed. |

## 3. Issuer, audience, and role verification rules

The backend source validates OIDC JWTs at API Gateway. It maps `realm_access.roles` rather than a custom role claim (`api-gateway/src/main/java/com/hometracker/api_gateway/config/SecurityConfig.java:56-69`). It also requires `home_energy_user_id` for non-admin ownership flows (`OwnershipGatewayFilter.java:75-105`).

Future redacted evidence must establish:

1. the configured isolated issuer URL equals the token `iss` value;
2. the JWK-set URL used by Gateway belongs to the same approved isolated issuer;
3. the intended audience/client relationship is accepted by the actual configured resource-server behavior; and
4. the role and, where applicable, numeric ownership claim are correct.

The repository does not contain a custom audience-validation rule in `SecurityConfig.java`; therefore any audience expectation must be verified against the approved isolated identity configuration and the framework's runtime behavior. It must not be assumed solely from client naming.

No raw JWT, bearer header, JWK, password, client secret, or signing key belongs in the evidence package.

## 4. Device authorization verification rules

Machine telemetry authorization has two distinct stages:

1. Gateway recognizes a configured device secret and removes caller-supplied privileged headers (`IotIngestionTokenFilter.java:61-128`).
2. Ingestion Service checks the exact relationship between payload device ID and configured secret (`IngestionAuthorizationService.java:84-104`).

Future verification must test mapping structure and identity without printing secret values. It must demonstrate that H1, H2, and H4 have distinct backend device IDs and distinct opaque secret references. A future security test may validate valid/cross-device/invalid mappings only after its own explicit request approval; Task 4E does not authorize any such request.

## 5. Redaction and evidence retention

Allowed evidence: service names, container IDs, image digests, network/volume names, non-secret database names, returned numeric IDs, redacted status/health results, timestamps, approval IDs, and opaque secret-reference labels.

Forbidden evidence: passwords, authorization headers, JWTs, device secrets, internal gateway proofs, internal-service credentials, client secrets, private keys, bootstrap credentials, full connection strings with credentials, or `docker compose config` output containing resolved values.

All evidence must be retained under the experiment record and not pasted into the research paper or source repository unless separately reviewed for redaction.

## 6. Known verification gaps

- There is no implemented provisioning-only composition to inspect yet.
- There is no approved isolated Keycloak/OIDC endpoint or identity storage.
- Task 4C lacks application-service and Kafka Compose health checks; a future runbook must define safe internal readiness evidence.
- Runtime isolation cannot be proven until a separately authorized start, but that start is currently blocked.
