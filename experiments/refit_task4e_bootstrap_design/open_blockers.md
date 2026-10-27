# Task 4E: Open Blockers and Final Decision

## Final decision

**NO-GO — BOOTSTRAP BLOCKERS REMAIN.**

Task 4E establishes that the startup issue is a real configuration/provisioning circularity, not a Docker `depends_on` cycle. A safe staged design direction exists, but no execution prerequisite is yet approved or implemented.

## What is resolved at the planning level

| Planning question | Answer | Evidence |
|---|---|---|
| Is the full Task 4C graph a container cycle? | No. Its `depends_on` graph is acyclic. | `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml:97-216` |
| Is there an operational bootstrap cycle? | Yes. The full stack needs a real device map before the secure provisioning gateway path can be started. | `docker-compose.refit.yml:137,206`; `IngestionAuthorizationService.java:67-81`; `SecurityConfig.java:38-47` |
| Can a source-compatible design break it? | Yes, with a separately reviewed provisioning-only isolated stage followed by a full telemetry stage. | `startup_circularity_analysis.md`; `bootstrap_dependency_graph.md` |
| Can the backend issue device secrets? | No verified API/entity/lifecycle exists. | `IngestionAuthorizationService.java:149-177`; Task 4D secret review |
| Can Task 4E execute the design? | No. It is planning only. | Task 4E strict prohibitions |

## Remaining blockers

| ID | Severity | Blocker | Required safe resolution |
|---|---|---|---|
| E1 | Critical | No approved provisioning-only isolated Compose/overlay exists. | Create and statically review a new composition containing only isolated OIDC, MySQL, User Service, Device Service, and Gateway. |
| E2 | Critical | The intended experiment MySQL state handoff is unresolved. | Approve sequential reuse of the same dedicated experiment-only database/volume or another equally controlled state-continuity mechanism. Do not use a fresh separate DB or an existing DB. |
| E3 | Critical | No isolated OIDC issuer, realm, persistent identity storage, administrator bootstrap process, or issuer/JWK network route exists. | Approve and design an independent identity-provider topology; do not reuse development Keycloak. |
| E4 | Critical | Persistent-store initialization has not been authorized. | Obtain explicit approval for isolated identity/MySQL initialization first; defer Kafka/Influx initialization until full-stage approval. |
| E5 | Critical | H1/H2/H4 profile/device IDs do not exist. | Create them only through the approved isolated ADMIN gateway workflow; record returned IDs and verify one `GENERAL` device each. |
| E6 | Critical | No native device-secret issuance/rotation/revocation mechanism exists. | Approve external generation, storage, mapping injection, rotation, and redacted evidence procedure. |
| E7 | High | App and Kafka readiness are not encoded in current Compose health checks. | Define/review an internal health/readiness runbook; User/Flyway must precede Device readiness. |
| E8 | High | Kafka image/reproducibility and transport-security decisions remain open. | Pin a reviewed image digest and decide required broker hardening before runtime. |
| E9 | High | InfluxDB post-bootstrap least-privilege credential plan is unresolved. | Approve an experiment-scoped writer strategy after bootstrap; never expose values. |
| E10 | High | Runtime isolation cannot be proven until first authorized start. | Define redacted network/volume/endpoint evidence and authorize a future deployment-only start. |
| E11 | Medium | Optional dashboard callback and household user identities are unresolved. | Decide whether UI demonstration is needed; if yes, approve exact isolated origin and per-household identity mappings. |
| E12 | Critical | No approval exists for first service start or no-event smoke request. | Obtain a separate execution authorization after E1-E10 are resolved. |

## Required approval sequence

1. G0: static provisioning-only design and state-continuity review.
2. G1: isolated persistent-store initialization.
3. G2: isolated identity-provider/administrator bootstrap.
4. G3: application profile and `GENERAL` device creation.
5. G4: external device-secret issuance and mapping preparation.
6. G5: full isolated telemetry-stage start.
7. G6: no-event deployment-only smoke test.

Approval of one gate does not authorize any later gate.

## Explicitly prohibited shortcuts

- Guessing database IDs or using REFIT house numbers as IDs.
- Reusing development Keycloak realm/accounts/credentials/keys or existing device tokens.
- Disabling `SECURITY_ENABLED` or `INGESTION_AUTH_REQUIRED`.
- Using global/legacy ingestion token fallback.
- Starting the full Task 4C composition merely to obtain IDs.
- Directly calling private User/Device services as a provisioning bypass.
- Connecting any isolated service to existing MySQL, Kafka, InfluxDB, volume, network, or issuer.
- Running replay, simulator, ML, Alert, Insight, or any ingestion/Kafka event during a deployment-only smoke test.

## Re-entry criterion

The work may progress only to a separate **execution-plan review** once E1-E10 have documented, approved resolutions. It may progress to a **deployment-only smoke-test review** only when E12 has explicit authorization and the approved provisioning stage has produced verified, non-secret H1/H2/H4 mappings.
