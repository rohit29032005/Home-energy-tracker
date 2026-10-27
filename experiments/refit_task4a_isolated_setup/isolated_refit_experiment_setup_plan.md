# Task 4A — Isolated REFIT Experiment Device Setup Plan

**Status:** Planning complete; execution is **not approved**.  
**Date:** 2026-10-12  
**Scope:** Design and read-only inspection only. No device, user, token, database record, Docker configuration, authentication rule, replay request, or REFIT event was created or changed.

## 1. Executive decision

### GO/NO-GO

| Decision | Result | Reason |
|---|---|---|
| Continue with the present shared Docker deployment | **NO-GO** | A replay would write to the shared Kafka topic and Influx bucket, and the baseline ML worker would consume the events. Dedicated IDs alone do not prevent shared-pipeline and shared-data effects. |
| Plan an isolated REFIT experiment deployment | **Design GO only** | The existing application supports profile and device records, and device-bound credentials can be supplied through runtime secrets without backend or model changes. Implementation still needs explicit approval. |
| Provision devices, credentials, or an experiment environment now | **NO-GO** | Task 4A permits planning only. |

The minimum **semantically and operationally safe** future topology is a separate REFIT experiment deployment containing three dedicated application household profiles, one logical aggregate-meter device per profile, and three distinct device-bound credentials. The deployment must use separate stateful infrastructure from the existing stack.

The verified data-unit decision remains unchanged:

```text
Task 2 derived_interval_energy_kwh  ->  ingestion API energyConsumed
```

`original_aggregate_power_w` remains source provenance only. It must never be submitted as `energyConsumed`.

## 2. Current device and authorization evidence

| Area | Verified finding | Consequence for the plan |
|---|---|---|
| Existing device workflow | The protected `POST /api/v1/device` workflow creates a normal device record with `name`, `type`, `location`, and `userId`; MySQL assigns its ID. The UI calls this same supported workflow. | New experiment device IDs must be captured from the creation responses, never preselected. |
| Existing profile workflow | An administrator can create an application household profile through `POST /api/v1/user`. The project documentation explicitly distinguishes this profile from a Keycloak login. | A device-token replay does not require a new Keycloak login for each experiment profile. |
| Device ownership | A regular authenticated user can act only for its own profile; an administrator can provision household/device records through the normal gateway flow. | Profile/device provisioning requires an authorized administrator, not direct database writes. |
| Credential lifecycle | No token table, token entity, credential-issuance endpoint, rotation endpoint, or automatic pairing workflow exists. Device tokens are parsed from the runtime `IOT_INGESTION_DEVICE_TOKENS` mapping when services start. | Credential generation and revocation are deployment-secret operations, not UI/API operations. |
| Token binding | The gateway recognizes configured machine tokens, while the ingestion service performs the decisive exact `deviceId -> token` match. Duplicate IDs and duplicate token values are rejected. | One unique token must be generated for each returned experiment device ID. A token must not be reused across houses. |
| Current Task 4 state | The running configuration contains a mapping for backend device `1` only, with no verified REFIT House 1/2/4 association. | Existing devices and credentials must not be reused or inferred from numeric IDs. |
| Shared pipeline | Ingestion publishes to shared `energy-usage`; Usage writes shared Influx data; the baseline ML worker consumes that topic and emits anomaly results. | A logical device-only setup in the current stack is not strict experiment isolation. |

Primary implementation references are `device-service/.../DeviceController.java`, `DeviceService.java`, `DeviceDto.java`, `ingestion-service/.../IngestionAuthorizationService.java`, `api-gateway/.../IotIngestionTokenFilter.java`, `usage-service/.../UsageService.java`, `ml-service/app/kafka_worker.py`, and `docker-compose.yml`.

## 3. Recommended isolated setup

### 3.1 Why three profiles are required

The application aggregates usage and threshold checks by `userId`, not merely by device ID. Therefore, one experiment user owning three devices would combine the independent REFIT households at the household/dashboard/alert level. Although it would create fewer database rows, it is rejected because it would collapse House 1, House 2, and House 4 into one application household.

The recommended minimum preserves household identity as follows:

| REFIT source household | Future application profile | Future logical device | Device type | Required setting |
|---:|---|---|---|---|
| House 1 | `REFIT Experiment — House 1` | `REFIT H1 Aggregate Meter` | `GENERAL` | `alerting=false` |
| House 2 | `REFIT Experiment — House 2` | `REFIT H2 Aggregate Meter` | `GENERAL` | `alerting=false` |
| House 4 | `REFIT Experiment — House 4` | `REFIT H4 Aggregate Meter` | `GENERAL` | `alerting=false` |

Each profile requires a unique, project-controlled, non-personal contact address if the current user schema requires an email. Each profile/device ID must be generated by the supported application workflow and recorded only after creation.

Each meter is intentionally a **logical whole-house aggregate meter**, not an appliance claim. Names and locations should state this clearly, for example `REFIT Experiment / House 1`, so results cannot be mistaken for appliance-level telemetry.

### 3.2 Non-secret mapping ledger

After authorized device creation, retain a local non-secret ledger with this structure:

| REFIT household | Generated application profile ID | Generated backend device ID | Device label | Credential reference name |
|---:|---:|---:|---|---|
| 1 | `[returned after creation]` | `[returned after creation]` | `REFIT H1 Aggregate Meter` | `REFIT_REPLAY_H1_TOKEN` |
| 2 | `[returned after creation]` | `[returned after creation]` | `REFIT H2 Aggregate Meter` | `REFIT_REPLAY_H2_TOKEN` |
| 4 | `[returned after creation]` | `[returned after creation]` | `REFIT H4 Aggregate Meter` | `REFIT_REPLAY_H4_TOKEN` |

The ledger stores identifiers and secret-reference names only. It must not contain token values.

## 4. Required isolated deployment boundary

### 4.1 Why the current Docker stack is unsuitable

The current Compose deployment has fixed container names, fixed host ports, and shared named volumes such as MySQL, Kafka, and InfluxDB data. `docker compose -p refit-experiment` alone would not provide a safe parallel environment because those fixed names and shared resources can collide.

Furthermore, accepted telemetry in the current stack would reach:

```text
ingestion -> shared energy-usage Kafka topic -> Usage / baseline ML -> InfluxDB / anomaly-results / alert paths
```

Disabling `alerting` on the experiment profiles prevents ordinary threshold-alert evaluation for those profiles, but it does not prevent Kafka, InfluxDB, ML-worker, metric, or topic effects.

### 4.2 Future deployment specification requiring approval

Create a **new deployment-only Compose specification** (for example, `docker-compose.refit-experiment.yml`) rather than editing the active `docker-compose.yml`. This future file is not created by Task 4A.

It must have all of the following characteristics:

1. Unique or omitted `container_name` values.
2. A unique Docker network and unique named volumes for MySQL, Kafka, and InfluxDB.
3. Non-conflicting host ports, or no externally exposed ports except those needed for the approved test.
4. A separate Keycloak and Mailpit instance if interactive administration/UI is required.
5. The same approved application images and the same immutable baseline model artifact/version; no baseline model source, artifact, or feature schema modification.
6. A separate non-versioned secret source, for example a local excluded environment file or an approved secret manager.
7. A distinct experiment Influx bucket/organization and Kafka broker/topic state created only inside the isolated deployment.

No secret value belongs in Git, source code, `replay_config.example.yaml`, `.env.example`, Dockerfiles, or reports.

## 5. Least-privilege authorization and credential design

### 5.1 Provisioning roles

| Activity | Minimum authorized actor | Notes |
|---|---|---|
| Create the three application profiles | Application administrator through the existing gateway/UI/API workflow | Direct MySQL writes are not required or recommended. |
| Create one device under each new profile | Administrator, or a JWT owner whose claim matches that profile | Use returned IDs; do not supply/assume fixed IDs. |
| Generate and store device secrets | Deployment/secret operator | Must not be the replay tool, source repository, or report. |
| Inject mapping and restart isolated services | Deployment/Docker operator | Only the isolated `api-gateway` and `ingestion-service` need the device-token mapping refresh. |
| Optional UI/JWT access for experiment profiles | Keycloak administrator | Only needed for interactive UI/JWT access. First create the application profile, then set the JWT ownership claim to its returned ID. |
| Later time-series or topic cleanup | Separately authorized Influx/Kafka operator | Required only after an actual replay and only against verified isolated resources. |

### 5.2 Device credentials

Generate three different high-entropy machine tokens, one for each returned device ID. The future isolated runtime mapping has this *structure* only:

```text
IOT_INGESTION_DEVICE_TOKENS=<H1_DEVICE_ID>:<H1_TOKEN>,<H2_DEVICE_ID>:<H2_TOKEN>,<H4_DEVICE_ID>:<H4_TOKEN>
```

The same secret mapping must be injected into **both** the isolated `api-gateway` and isolated `ingestion-service`. Keep these controls unchanged:

```text
INGESTION_AUTH_REQUIRED=true
IOT_INGESTION_LEGACY_GLOBAL_TOKEN_ENABLED=false
```

The replay process receives only its three device-bound tokens. It must not receive a Keycloak administrator credential, a user-management JWT, an internal gateway token, an internal-service token, or the existing Wokwi credential.

The present shared stack's device-`1` mapping remains untouched. If anyone later proposes using the shared stack instead, its existing mapping would have to be preserved in full; that alternative remains NO-GO unless separately approved with its contamination and cleanup risks accepted.

## 6. Impact on existing users, records, and baseline pipeline

| Area | Recommended isolated deployment impact | Rejected shared-stack impact |
|---|---|---|
| Existing application users/devices | None | New records would coexist with normal users; accidental selection and dashboard exposure are possible. |
| Existing device-1/Wokwi mapping | None | Must be preserved while adding entries; an incomplete mapping could break the existing demo. |
| MySQL/Kafka/Influx data | Separate state only | Replay data would persist in shared resources. |
| Baseline ML pipeline | Same immutable baseline runs in its own experiment environment | The existing baseline worker would consume replay events and affect shared operational metrics/topics. |
| Alerts/email | Experiment profiles set `alerting=false`; isolated Mailpit only | Data may still reach other shared pipeline components even if threshold alerts are disabled. |
| Research traceability | Independent receipts and IDs per household | Greater risk of mixed operational and experimental evidence. |

## 7. Future rollback and cleanup plan

This plan is for a later approved execution only; Task 4A performs none of these actions.

1. Stop the replay process and save its non-secret reconciliation receipts.
2. Remove the three experiment device-token entries from the isolated secret source and restart only the isolated gateway and ingestion service, preventing new ingress.
3. Verify no in-flight replay process remains and reconcile submitted, failed, and ambiguous receipts before deletion.
4. Export any evidence that has been explicitly approved for retention.
5. Delete only the three experiment device records and their three experiment profiles using the normal authorized workflow. The user-to-device MySQL foreign key can cascade device-row deletion.
6. Treat InfluxDB, Kafka, and alert records as independent cleanup targets. Application device/user deletion does not remove time-series points; no application-scoped Influx delete API was found. Delete only verified experiment resources, device IDs, time windows, and isolated topics/volumes after separate approval.
7. Remove/rotate the three experiment tokens and disable/delete optional experiment Keycloak identities.
8. For the isolated deployment, remove only explicitly verified experiment containers, network, volumes, and topics. Never run a broad reset or delete shared application volumes.

## 8. Exact approvals required before implementation

All of the following approvals are required, in order:

1. **Environment approval:** approve creation of a separate REFIT experiment Compose/deployment specification with unique containers, ports, network, volumes, broker, and Influx state. This is a deployment configuration change, not a backend-code change.
2. **Record-provisioning approval:** authorize an application administrator to create three dedicated experiment household profiles and one aggregate-meter device under each profile through the existing supported workflow.
3. **Credential approval:** authorize a deployment/secret operator to generate three distinct device-bound secrets and inject them into the isolated gateway and ingestion services. No secret is to be committed or displayed.
4. **Lifecycle approval:** authorize start/restart of the isolated services and read-only health, profile, device, and mapping-ID verification.
5. **Validation approval:** after the above evidence is recorded, separately authorize Task 4's configuration/CSV/mapping/unit checks and a dry-run only.
6. **First ingestion approval:** separately authorize the first actual ingestion request. This cannot be bundled into any earlier approval.

## 9. Stop condition

Task 4A ends here. No profile/device/token was created, no configuration was changed, and no HTTP request or REFIT replay was performed. A future implementation must not begin until the approvals in Section 8 are explicit.
