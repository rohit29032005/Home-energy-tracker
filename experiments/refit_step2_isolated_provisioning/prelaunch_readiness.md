# Step 2 Isolated Environment — Pre-launch Readiness

## Verified configuration status

- **Compose project:** `refit-step2`, with a dedicated bridge network and four dedicated named volumes.
- **Existing experiment resources:** no `refit-step2` container, network, or volume existed during the preflight.
- **Runtime credential channel:** a fresh 22-variable runtime environment file was generated outside the repository in an ACL-restricted local folder. No credential values are recorded here or in source control.
- **Device-token mapping:** intentionally empty. The mapping must be created only after the three isolated application profiles and their database-generated device IDs are verified.
- **Static Compose validation:** `docker compose ... config --quiet` passed using the protected runtime file.
- **Loopback ports:** `18025`, `18080`, and `18081` were free at preflight.
- **Telemetry safety defaults:** disabled from this staging point: no replay launch, no synthetic simulation, no legacy global ingestion token, and no device token mapping.

## Runtime capacity gate

Docker Desktop reports **3.696 GiB** total memory. The recovered primary Home Energy Tracker stack currently has 15 running containers using approximately **2,890 MiB** in aggregate according to `docker stats --no-stream`, leaving roughly **0.87 GiB** of observed headroom.

The isolated provisioning stage requires an additional MySQL instance, Keycloak instance, three Java services, and a gateway. Starting it beside the primary stack would not be responsible on the current allocation: comparable services in the primary stack alone materially exceed the observed spare memory, and the primary Kafka broker previously terminated with `OOMKilled=true`.

## Required human choice before launch

No isolated container should start until one option is explicitly approved:

1. **Temporary cutover:** stop the already-backed-up primary Home Energy Tracker stack, then start the isolated provisioning stage. This makes the existing application temporarily unavailable and needs a separate lifecycle approval.
2. **Increase Docker Desktop capacity:** increase the Docker memory allocation enough to run both stacks, then restart Docker Desktop. The exact safe allocation must be rechecked after the restart; this document does not claim a specific minimum.
3. **Use a separate host:** run the isolated experiment on a machine with sufficient reserved capacity.

## Explicit non-actions

No isolated Docker resource was created or started. No Keycloak realm, profile, application device, device secret mapping, ingestion event, REFIT replay, database initialization, alert, or model operation was executed.

## Next gated action after a capacity decision

Start only the **provisioning stage** (MySQL, Keycloak, User Service, Device Service, API Gateway), verify readiness, and create three non-production profiles and one `GENERAL` aggregate-meter device per profile through the secured gateway. The telemetry profile remains off until the resulting IDs and independent device-bound credentials are verified.
