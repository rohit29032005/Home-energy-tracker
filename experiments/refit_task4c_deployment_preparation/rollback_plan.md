# Task 4C — Future Experiment Rollback and Cleanup Plan

**This is a future-only plan. Task 4C performed no deployment action and therefore nothing is to be removed now.**

## Preconditions before any future cleanup

1. Confirm the target Compose project is `refit-task4c` and is not the existing development or production project.
2. Confirm the exact experiment-only network and volume names: `refit-task4c-network`, `refit-task4c-mysql-data`, `refit-task4c-kafka-data`, and `refit-task4c-influx-data`.
3. Confirm any future profile/device IDs were created in the isolated MySQL database, not the shared application database.
4. Preserve approved non-secret reconciliation evidence before cleanup. Do not delete evidence that a later research protocol requires to retain.
5. Obtain explicit cleanup authorization; no broad Docker cleanup command is permitted.

## Future rollback sequence

1. Stop any approved replay process first and reconcile submitted, failed, and ambiguous request records. Do not delete infrastructure while a sender may still submit data.
2. Remove the experiment device-token map from the isolated runtime secret source and rotate/revoke the three experiment credentials. Never change the existing Wokwi or shared-stack mappings.
3. Stop only explicitly identified Task 4C containers through a future approved, project-scoped procedure. Do not use `docker compose down` against the repository root files.
4. If future profile/device records need removal, use the supported authorized application workflow against the isolated gateway/database. Do not issue direct SQL deletion against shared resources.
5. Treat InfluxDB and Kafka data as independent cleanup domains. Application record deletion does not erase points or topics. Delete only after confirming the isolated organization/bucket, broker, topic, time range, and device IDs.
6. Remove only the verified Task 4C named volumes and `refit-task4c-network` after the data-retention decision. Never use a global prune/reset command.
7. If an isolated OIDC provider is added later, revoke its experiment client/administrator/device-related credentials and delete only its experiment realm/storage after authorization.

## Guardrails

- Never target `db-data`, `kafka-data`, `influx-data`, any `*-prod` volume, `energy-net`, or the existing development default network.
- Never use the source-house numbers H1/H2/H4 as a Docker resource identifier without confirming the actual generated application IDs.
- Never assume a successful HTTP response proves all asynchronous Kafka/Influx effects have completed; reconcile before cleanup.
- If target isolation cannot be proven, stop and request review rather than attempting cleanup.
