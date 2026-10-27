# Task 4B — Security, Cleanup, and Rollback Plan

**Status:** Design only. No credential, device, database, container, network, or cleanup operation has been performed.

## 1. Verified authorization model

| Control | Verified behavior | Evidence |
|---|---|---|
| Profile creation | The User controller creates profiles through its protected `POST` route. | `user-service/.../controller/UserController.java:25-30` |
| Device creation | Device creation accepts only normal device metadata and `userId`; no credential is created. | `device-service/.../dto/DeviceDto.java`; `.../service/DeviceService.java:27-35`; `.../controller/DeviceController.java:33-38` |
| JWT ownership | Gateway and service ownership checks restrict ordinary users to their owned profile resources; an administrator can provision records. | `api-gateway/.../OwnershipGatewayFilter.java:67-106`; `device-service/.../security/OwnershipVerifier.java:42-76` |
| Machine authentication | The gateway recognizes configured device tokens; downstream ingestion binds a token to the body `deviceId`. | `api-gateway/.../IotIngestionTokenFilter.java:61-140`; `ingestion-service/.../IngestionAuthorizationService.java:84-146` |
| Token storage | Mapping is configuration-backed at startup; no token lifecycle API/table is present. | `IngestionAuthorizationService.java:42-81, 149-177`; `ingestion-service/src/main/resources/application.properties:16` |

## 2. Least-privilege future credential plan

### Profiles and devices

Create, only after explicit approval, three isolated application profiles and one device per profile:

```text
REFIT H1 profile -> REFIT H1 Aggregate Meter -> H1 device token
REFIT H2 profile -> REFIT H2 Aggregate Meter -> H2 device token
REFIT H4 profile -> REFIT H4 Aggregate Meter -> H4 device token
```

Each profile must have `alerting=false`. A separate profile per source household is required because the current usage/alert logic groups by `userId` (`usage-service/.../UsageService.java:112-180, 194-278`).

### Credentials

- Generate one distinct, high-entropy secret per newly returned backend device ID.
- Configure only these three values in the isolated environment as device-bound entries; do not reuse tokens across IDs because the parser rejects token reuse (`IngestionAuthorizationService.java:149-177`).
- Maintain `INGESTION_AUTH_REQUIRED=true` and `IOT_INGESTION_LEGACY_GLOBAL_TOKEN_ENABLED=false` in the future isolated environment.
- Give the future replay process only its three device-token references. It must not receive admin JWTs, internal gateway/service tokens, existing Wokwi credentials, database passwords, or Influx/Kafka administrator tokens.
- Use a Keycloak identity only if UI/JWT administration is needed. It is not required for a device-token replay. If used, create the application profile first and assign the returned ID to the `home_energy_user_id` claim afterward; no automatic synchronization was found.

## 3. Secret injection and version-control controls

### Verified repository controls

`.gitignore` excludes `.env`, `.env.local`, `.env.*`, private key formats, and `real_data_replay/replay.env`, while explicitly allowing the two tracked example files (`.gitignore:23-33, 50`). `.env.example` and `.env.production.example` expose variable names including `IOT_INGESTION_DEVICE_TOKENS` but must never contain a future experiment token.

### Future requirement

Use a separate untracked secret source, for example an excluded `refit-experiment.env` outside version control or an approved secret manager. Create a future public template only with placeholders such as:

```text
MYSQL_PASSWORD=<SET_IN_SECRET_STORE>
INFLUX_TOKEN=<SET_IN_SECRET_STORE>
IOT_INGESTION_DEVICE_TOKENS=<H1_DEVICE_ID>:<H1_TOKEN>,<H2_DEVICE_ID>:<H2_TOKEN>,<H4_DEVICE_ID>:<H4_TOKEN>
INTERNAL_GATEWAY_TOKEN=<SET_IN_SECRET_STORE>
```

This illustration has no real values. Task 4B does not create the secret file or alter either existing example file.

## 4. Network and data-access restrictions

1. Create an explicit `refit-experiment-net` bridge network. Do not attach any experiment service to the development default network or production `energy-net`.
2. Keep MySQL, Kafka, InfluxDB, Usage, Device, User, Alert, and ML service ports internal by default. Expose only a uniquely assigned gateway/UI port if administrative access is approved.
3. Give the isolated gateway an isolated Keycloak issuer/JWK configuration. The development default points to `localhost:8180` (`docker-compose.yml:287-288`) and must not be inherited unexamined.
4. Use a separate broker, MySQL instance, Influx instance, volumes, and credentials. Matching service names are acceptable only inside the isolated network.
5. Do not use the Wokwi host-local endpoint from `iot-simulator/include/config.h.example` for REFIT replay.
6. Omit ML, Alert, Prometheus, and Grafana during minimum deployment validation unless each is separately isolated and justified.

## 5. Log and metric separation

The future Compose project/container/log prefix must use a unique experiment identifier such as `refit-exp`. If monitoring is later enabled, it needs a separate Prometheus data volume and Grafana instance; the checked-in Prometheus configuration statically scrapes service DNS names (`docker/prometheus/prometheus.yml`) and sharing it would merge experiment and baseline metrics.

The non-secret replay ledger must include future run ID, REFIT household, returned backend device ID, source file/row, original timestamp, generated replay timestamp, payload hash or redacted payload fingerprint, HTTP outcome, and ambiguity status. It must never log device-token values.

## 6. Future cleanup and rollback plan

### Preconditions before cleanup

1. Stop the approved replay process.
2. Reconcile its submitted, failed, and ambiguous receipt counts; do not delete evidence before reconciliation is complete.
3. Confirm the targeted Compose project, network, volumes, Kafka broker, Influx org/bucket, and generated device IDs are all marked `refit-exp` and are not shared resources.
4. Obtain explicit deletion approval for the exact experiment resources.

### Ordered rollback procedure

1. Remove the three device-token entries from the isolated secret source and restart only the isolated gateway/ingestion pair, preventing future machine ingress.
2. Preserve approved non-secret run receipts and static deployment evidence.
3. Remove only scoped experiment telemetry from the isolated Influx bucket, if an approved deletion method exists. No application-scoped Influx delete endpoint was found; this remains a privileged operational action.
4. Remove only scoped experiment Kafka topics/volumes/broker state, if they are truly separate. Never purge a shared `energy-usage` topic.
5. Delete the three isolated device records and their three profiles through the approved application workflow. The user-to-device foreign key cascades device rows (`user-service/src/main/resources/db/migration/V2__device_table.sql:9-11`), but it does not erase Influx data.
6. Remove optional isolated Keycloak identities and rotate/delete the three experiment secrets.
7. Remove only verified experiment containers, network, and volumes. Never run a broad Docker volume reset.

### Known cleanup limitation

Alert rows have no demonstrated foreign-key cascade (`V3__alert_table.sql`), and Kafka/Influx data do not cascade with device/user deletion. This is another reason to exclude Alert/ML during initial validation and to isolate broker/database state before any future events.

## 7. Security decision

**GO FOR DEPLOYMENT PLANNING ONLY.** The minimum design is defensible only with separate infrastructure and secrets.  
**NO-GO for execution.** The current stack must not receive the experiment profiles, token map, or events.
