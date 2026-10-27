# Step 2 isolated REFIT experiment environment

This deployment is intentionally separate from the existing Home Energy Tracker stack. It uses the Compose project name `refit-step2`, its own bridge network, separate named volumes, loopback-only gateway/identity/mail ports, a new Keycloak realm, and fresh runtime credentials outside the repository.

## Two safe stages

1. **Provisioning stage:** Start only MySQL, Keycloak, User Service, Device Service, and API Gateway. Create the three non-production application profiles and one `GENERAL` device per profile through the secured gateway.
2. **Telemetry stage:** After real device IDs and three independent device secrets exist in the protected runtime file, start the `telemetry` Compose profile. It includes Kafka, InfluxDB, Mailpit, ML inference, Ingestion, Usage, and Alert services. Simulation remains disabled and no replay is launched by this file.

The only host-published listeners are loopback-only: Gateway `18080`, Keycloak `18081`, and later Mailpit `18025`. All service-to-service communication remains on `refit-step2-network`.

The Kafka digest is explicitly pinned. Its memory cap is an initial experiment constraint, not a production-capacity claim; it must be observed during the telemetry-stage smoke test.

Runtime credentials and device tokens must be kept in the protected external environment file. Do not add that file to Git or print its contents.

## Capacity gate

The primary stack currently consumes most of Docker Desktop's available memory. Read [prelaunch_readiness.md](prelaunch_readiness.md) before launching this composition. Do not run the isolated environment in parallel with the primary stack until Docker capacity has been increased or the primary stack is explicitly approved for a temporary, backed-up cutover.
