# Task 4D: Database Initialization Impact Review

## Scope and decision

This report analyzes what a future isolated deployment would initialize. It does not initialize MySQL, InfluxDB, Keycloak, Kafka, Flyway, volumes, or any database record.

**Current decision: NO-GO.** Starting the experiment-only infrastructure would create persistent state and still requires separate explicit approval.

## 1. Isolated MySQL impact

### Verified application migration behavior

| Item | Evidence | Effect in a future fresh experiment database |
|---|---|---|
| Flyway ownership | `user-service/src/main/resources/application.properties:9-12` | User Service enables Flyway and becomes the migration authority. Device Service has Flyway disabled. |
| User schema | `user-service/src/main/resources/db/migration/V1__user_table.sql:1-9` | A user/profile table with database-generated IDs and a unique email constraint is created. |
| Device schema | `user-service/src/main/resources/db/migration/V2__device_table.sql:1-12` | Device records use generated IDs and reference profile ownership. |
| Alert schema evolution | `V3`, `V4`, and `V6` user-service migration files | Existing alert-related schema changes are also applied to a fresh database. |
| Demo seed data | `V5__seed_demo_household.sql:1-10`; `V7__seed_security_demo_user.sql:1-4` | Demonstration profile/device records are inserted; experiment profile/device IDs are not predictable. |
| Docker init script | `docker/mysql/init.sql:1-4` | The inspected init script is not the principal schema source; application Flyway migrations determine schema/seed effects. |

### Proposed future isolation rule

The Task 4C definition uses experiment-only database names and named volumes. A later provisioning-only composition must use different experiment-only names/volumes from both the existing stack and the future full telemetry stack, unless a deliberate, approved handoff is required. It must never mount or point at the existing MySQL storage.

First launch of a new isolated MySQL volume is material: it creates database state, application users, Flyway history, schemas, and seed records. That is why no container start is authorized in Task 4D.

### Profile/device identifier impact

Because auto-increment IDs and seed rows coexist, operators cannot reserve H1/H2/H4 as database IDs. The only safe future mapping is:

```text
REFIT source label -> returned application profile ID -> returned GENERAL device ID -> external secret reference
```

This mapping must be captured from approved API responses after creation, not inferred from schema order or source household label.

## 2. Isolated Keycloak/OIDC identity-store impact

The existing development Keycloak Compose block uses development import mode and has no explicit persistent database/volume declared (`docker-compose.yml:96-109`). A future isolated issuer therefore needs an approved decision for persistent realm/user/role/client/signing state. First initialization would create at least:

- an isolated realm;
- isolated roles and token claim mapper;
- isolated clients and permitted callbacks;
- a bootstrap administrator identity; and
- issuer signing/identity-store state.

None of this may be imported from or connected to the development `home-energy` realm. It is a separate persistent identity initialization event and requires approval before deployment.

## 3. Isolated InfluxDB impact

The static Task 4C design identifies separate InfluxDB configuration and a named volume. A first start would initialize experiment org/bucket metadata, bootstrap credentials, and time-series storage. This is persistent data creation even if no replay events are submitted.

Future authorization requirements:

1. approve first initialization and volume retention policy;
2. generate isolated bootstrap material through the approved secret mechanism;
3. establish the experiment org/bucket; and
4. provide Usage Service a scoped writer credential after bootstrap if the platform supports it, rather than retaining a broad bootstrap/admin credential for ordinary operation.

No organization, bucket, token, volume, or time-series point was created during Task 4D.

## 4. Kafka impact

The Task 4C static configuration uses an isolated named Kafka volume and no host-exposed Kafka port. A first start would still create Kafka metadata/log data and topics as the services operate. The current design's Kafka image pinning and transport-authentication posture must be reviewed before runtime; the inspected configuration does not establish a verified SASL/TLS setup.

No Kafka broker, topic, consumer group, or event was started or created during Task 4D.

## 5. Data-retention and rollback decisions required before deployment

| Decision | Why it must be approved first |
|---|---|
| MySQL volume retention or deletion policy | Profile/device records and Flyway state are persistent experiment data. |
| Keycloak identity-store retention policy | Realm/users/roles/mappings may be security records and must survive or be deliberately retired. |
| InfluxDB retention policy | Historical replay data can be large and needs a defined experiment retention period. |
| Kafka log retention policy | Event data and consumer state may be retained on disk. |
| Seed-data handling | Existing Flyway seeds affect ID allocation and may need documented containment in the research protocol. |
| Cleanup authority | Deletion is destructive and cannot occur without clear ownership and approval. |

## 6. Approval gates

Before any first container start, obtain approval for all of the following:

1. isolated infrastructure names, volumes, and network boundaries;
2. migration/seed-data impact;
3. isolated Keycloak persistence and bootstrap path;
4. secret generation/injection; 
5. InfluxDB and Kafka initialization scope;
6. data retention and eventual cleanup plan; and
7. the precise provisioning-only deployment composition.

Until those approvals are granted, the correct state is planning only.
