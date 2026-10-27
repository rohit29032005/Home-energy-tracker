# Task 4H Stage R0 — Flyway Migration Impact Assessment

## Scope and decision boundary

This is a static, read-only migration assessment. No database connection, Flyway
command, migration execution, checksum check, endpoint request, or schema change
was performed.

**Migration decision: NO-GO for User Service startup.** Static source identifies
real schema/data migration risk, while live history and pending status remain
unresolved.

## Finding labels

- **VERIFIED** — directly supported by static source/configuration evidence.
- **INFERRED** — a possible startup consequence, not a live database result.
- **UNRESOLVED** — live data/history was not safely queried in Stage R0.
- **RECOMMENDED** — a future approval-gated migration safeguard; not executed.

## Evidence reviewed

- User, Device, and Alert Service application.properties files.
- User Service migration directory.
- Task 4G data-and-initialization risk assessment.
- Static source scan for baseline-on-migrate configuration.

## Verified Flyway configuration

| Classification | Finding | Supporting evidence | Impact |
|---|---|---|---|
| **VERIFIED** | User Service is the shared-schema Flyway owner; automatic Hibernate DDL is disabled and Flyway is enabled. | user-service/src/main/resources/application.properties lines 9-12. | Startup validates recorded migration history and can apply pending versions. |
| **VERIFIED** | Device Service disables Flyway. | device-service/src/main/resources/application.properties lines 9-11. | Device Service relies on shared schema managed by User Service. |
| **VERIFIED** | Alert Service disables Flyway. | alert-service/src/main/resources/application.properties lines 19-21. | Alert Service also relies on the shared schema/migration history. |
| **VERIFIED** | No active spring.flyway.baseline-on-migrate declaration was found in the reviewed production source/configuration. | Static repository scan of User/Device/Alert configuration and Compose references. | A live schema that lacks expected recorded history cannot be assumed to be safely baselined. |
| **VERIFIED** | MySQL uses an existing persistent volume and User Service is stopped. | Task 4F/4G reports. | Current database history was deliberately not queried during Stage R0. |

## Static migration inventory

| Migration | Classification | Static effect | Startup-time risk |
|---|---|---|---|
| V1 user table | **VERIFIED** | Creates the user table with alerting/threshold fields. | Can create foundational schema if absent. |
| V2 device table | **VERIFIED** | Creates device table with user foreign key and ON DELETE CASCADE. | Establishes referential/deletion behavior used by Device Service. |
| V3 alert table | **VERIFIED** | Creates alert table. | Establishes alert persistence schema. |
| V4 complete alert columns | **VERIFIED** | Adds alert message, threshold, consumed-energy, and email fields with conditional additions. | Alters alert schema if fields are absent. |
| V5 seed demo household | **VERIFIED** | INSERT IGNORE seed migration for a demo user/devices; literal values were not retained in this report. | Can write seed records if pending. |
| V6 alert deduplication columns | **VERIFIED** | Adds alert device/type/deduplication fields and creates a deduplication index. | Column/index DDL depends on Flyway once-only history rather than per-statement conditional guards. |
| V7 seed security demo user | **VERIFIED** | INSERT IGNORE seed migration for a user; literal values were not retained in this report. | Can write seed data if pending. |

Supporting evidence: user-service/src/main/resources/db/migration/V1 through V7.
A static operation scan found CREATE, ALTER, and INSERT operations across these
migrations.

## Assessed startup risks

| Classification | Risk | Reason |
|---|---|---|
| **INFERRED** | User Service startup can apply schema or seed-data changes. | Flyway is enabled and source comments/configuration describe validation plus application of pending versions. |
| **INFERRED** | An absent/inconsistent Flyway history against an already altered alert table can cause V6 failure. | V6 DDL/index behavior relies on Flyway once-only execution; live history was not verified. |
| **INFERRED** | Pending V5/V7 migrations can introduce retained demo rows. | Both migrations include INSERT IGNORE seed operations. |
| **INFERRED** | Starting Device/Alert before User Service migration readiness can expose an incomplete shared schema. | Those services disable Flyway and use the User-owned schema. |
| **UNRESOLVED** | Current flyway_schema_history, migration checksums, pending list, schema version, seed-row state, and partial-failure status. | Resolving these requires a database-aware read operation that was not authorized. |
| **UNRESOLVED** | Whether current MySQL state exactly matches the checked-in migration set. | No database query, validation, or migration was run. |
| **UNRESOLVED** | Whether a recoverable backup/rollback point exists before migrations. | No backup/test was created during Stage R0. |

## Recommended controls before a future start

1. Complete and accept the backup/rollback plan, including an isolated restore
   test, before allowing any service that can migrate the retained database.
2. Under separately approved read-only database assessment, determine Flyway
   history, pending versions, checksum drift, and schema compatibility without
   applying migrations.
3. If drift or pending migrations are found, require a specific change-control
   decision and rollback plan; do not use baseline or repair operations as a
   shortcut.
4. Start User Service only under a migration-aware approval gate, observe its
   application readiness, and assess any migration result before Device or
   Alert Service is allowed to start.
5. Keep REFIT Task 4C isolated; no REFIT profile/device provisioning should use
   or modify the existing MySQL schema during recovery.

## Stage R0 conclusion

Static evidence is sufficient to establish that Flyway is a meaningful
startup-time schema/data-change risk. It is not sufficient to establish live
migration status or safe startup. **NO-GO** remains until a backup gate and an
approved read-only Flyway history/pending-impact assessment are complete.

