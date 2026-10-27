# Task 4D: Household and Device Provisioning Plan

## Scope and status

This document describes a future, separately approved procedure. It does **not** create a Keycloak identity, application profile, device, secret, mapping, database record, or network request.

**Current decision: NO-GO.** The plan is deliberately two-stage because the full Task 4C configuration requires a device-token map at startup, while the corresponding database-generated device IDs do not exist until after a controlled provisioning operation.

## 1. Verified constraints

| Constraint | Evidence | Consequence |
|---|---|---|
| Application profile IDs are database generated. | `user-service/src/main/java/com/hometracker/user_service/entity/User.java:21-30`; `V1__user_table.sql:1-9` | REFIT H1, H2, and H4 are source labels, not backend user IDs. |
| Device IDs are database generated. | `device-service/src/main/java/com/hometracker/device_service/entity/Device.java:17-28`; `V2__device_table.sql:1-12` | A device ID may be learned only from the approved creation response. |
| `GENERAL` is a supported device type. | `device-service/src/main/java/com/hometracker/device_service/model/DeviceType.java:3-15` | It is appropriate for the planned aggregate-meter representation. |
| Profile creation is an administrative gateway operation. | `api-gateway/.../SecurityConfig.java:38-47`; `user-service/.../UserController.java:25-30` | An isolated `ADMIN` identity is required for controlled setup. |
| Device creation returns a persisted device DTO. | `device-service/.../DeviceController.java:33-39`; `.../service/DeviceService.java:27-35,67-74` | The returned database ID must be captured in the controlled experiment ledger. |
| One-device cardinality is not enforced automatically. | `DeviceService.java:27-35` and inspected schema | The future operator must explicitly verify that exactly one `GENERAL` device is attached to each experiment profile. |
| Fresh User Service migrations seed demonstration rows. | `V5__seed_demo_household.sql:1-10`; `V7__seed_security_demo_user.sql:1-4` | H1/H2/H4 IDs cannot be predicted even in a fresh isolated database. |
| Device secret mappings are configuration-only. | `IngestionAuthorizationService.java:149-177` | No endpoint creates, stores, lists, or rotates device secrets. |

## 2. Recommended isolation boundary

The minimum safe future design is a **separately approved provisioning-only isolated deployment**, independent from both the existing stack and the full Task 4C telemetry stack.

```text
Isolated OIDC administrator
           |
           v
  isolated API Gateway (ADMIN JWT validation)
        /                         \
       v                           v
isolated User Service        isolated Device Service
       |                           |
       +------ isolated MySQL -----+

Returned profile IDs + returned device IDs
           |
           v
approved non-secret mapping ledger + external secret references
           |
           v
future Task 4C full deployment configuration
```

The provisioning-only environment should contain only the isolated identity dependency, API Gateway, User Service, Device Service, and a dedicated MySQL store, subject to a later design and deployment approval. It should not include replay, Ingestion Service, Usage Service, Kafka, InfluxDB, ML inference, alerting, or the existing application services. This boundary avoids creating telemetry infrastructure merely to obtain IDs, while preventing any contact with existing state.

Task 4D does not create that composition. A new OIDC service or separately operated issuer would be outside Task 4C's original eight-service static scope and needs explicit approval.

## 3. Future controlled provisioning sequence

### Phase A — approve and deploy the provisioning-only environment

Preconditions:

1. Approve isolated OIDC/Keycloak architecture, persistent identity storage, issuer URL, and JWK-set route.
2. Approve first initialization of an experiment-only MySQL volume and the known Flyway seed-data effect.
3. Approve secret generation and injection channel; no secret may be committed, printed, or copied from development.
4. Create a new, narrowly scoped isolated `ADMIN` identity through the approved identity procedure.
5. Record the new environment identity, exact image digests, approval identifiers, and rollback owner in a non-secret deployment ledger.

### Phase B — create application profiles

Using an `ADMIN` token in the isolated gateway only, future operators would create three distinct application profiles. Each profile must have a distinct experiment-only, non-personal email address because the user schema has a unique email constraint. The planned source labels must be retained as metadata in the ledger, not inferred from returned IDs.

| Source household label | Application profile | Expected returned ID | Status today |
|---|---|---:|---|
| REFIT H1 | Experiment-only profile for House 1 | Not created | Blocked / no approval |
| REFIT H2 | Experiment-only profile for House 2 | Not created | Blocked / no approval |
| REFIT H4 | Experiment-only profile for House 4 | Not created | Blocked / no approval |

Immediately after every approved create operation, capture only the returned profile ID and validate that it is unique. Do not use `1`, `2`, or `4` based on REFIT labels; demo seeds make that unsafe.

### Phase C — create exactly one aggregate device per profile

For each returned profile ID:

1. Query/verify the profile's current device list through the approved administrative workflow.
2. Confirm that no experiment aggregate meter has already been created for that profile.
3. Create one device with type `GENERAL`, a source-label-safe experiment name, and the returned application profile ID as owner.
4. Capture the returned device ID in the ledger.
5. Re-check that the profile has exactly one intended `GENERAL` aggregate-meter device.

| Source household | Profile ID | Required device type | Returned device ID | Device-secret reference | Status today |
|---|---:|---|---:|---|---|
| REFIT H1 | Not created | `GENERAL` | Not created | Not generated | Blocked |
| REFIT H2 | Not created | `GENERAL` | Not created | Not generated | Blocked |
| REFIT H4 | Not created | `GENERAL` | Not created | Not generated | Blocked |

The backend does not enforce the exact-one rule. The manual validation step is essential before a future full deployment starts.

### Phase D — optional household OIDC identities

Individual H1/H2/H4 browser identities are optional and are **not** a prerequisite for historical machine replay. If a professor demonstration requires each household to sign in separately, an authorized isolated identity administrator would, after Phase B:

1. create one distinct isolated user identity for each household;
2. assign only the `USER` role;
3. set its `homeEnergyUserId` attribute to the **returned** application profile ID; and
4. obtain a fresh token to verify the numeric claim is mapped.

No application profile automatically creates a Keycloak identity, and no backend association exists. The mapping is a controlled administrative ledger operation.

### Phase E — prepare device-bound secrets and future full configuration

Only after the three database-generated device IDs have been recorded, an approved secret-management workflow may generate three independent high-entropy device secrets. Each secret is referenced, not copied, in the experiment ledger. The future full Task 4C configuration must inject the same three `deviceId:secret` bindings into both Gateway and Ingestion Service, using the `REFIT_IOT_INGESTION_DEVICE_TOKENS` configuration path.

The replay client must receive only the single device secret required for the active house. It must not receive the OIDC administrator credential, gateway proof, internal-service credential, database credentials, or other households' device secrets.

## 4. Circular startup blocker

The Task 4C full Compose configuration deliberately requires nonempty device-token mappings when security is enabled. However, those mappings must contain real database-generated device IDs, which cannot be known before profile/device provisioning.

Therefore the following is prohibited:

- guessing or reserving device IDs;
- using REFIT house numbers as backend device IDs;
- adding a global/shared device token;
- disabling security to obtain IDs;
- starting the full Task 4C telemetry stack with placeholder device-token mappings; or
- repurposing existing development device tokens.

The future provisioning-only isolated deployment is the least invasive route that respects the current backend contract. It still requires explicit approval before implementation or execution.

## 5. Expected impact, rollback, and evidence

If approved in the future, all profile/device records must be stored in experiment-only MySQL state. Existing users, development devices, existing Keycloak identities, and baseline ML artifacts must remain untouched. A future rollback must stop the isolated composition and preserve or destroy its named experiment volumes only under a separately approved retention/deletion decision. No cleanup action is authorized now.

Required evidence before moving to any first-ingestion review:

1. approved isolated issuer and administrator bootstrap evidence;
2. three returned application profile IDs;
3. three returned `GENERAL` device IDs, one per profile;
4. cardinality/ownership verification evidence;
5. secret-reference ledger with no secret values;
6. configuration parity check showing Gateway and Ingestion Service have the same identifiers but no exposed values; and
7. explicit approval for isolated storage initialization and later request execution.
