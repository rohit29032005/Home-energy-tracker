# Maintenance and Recovery Plan for an 8 GB Windows Laptop

**Status:** Planning only — no Docker lifecycle, database, credential, profile, device, or telemetry action was executed while preparing this plan.

**Decision:** **NO-GO — TEMPORARY MAIN-STACK STOP NOT YET AUTHORIZED.** A conditional GO is possible only after the pre-stop gates in this document receive explicit approval.

## 1. Verified primary-stack scope

Docker labels and `docker compose ls` identify the primary application as the Compose project **`home-energy-tracker`**, using:

```text
C:\Users\anju2\Desktop\Home-Energy-Tracker\docker-compose.yml
```

At the planning audit, the project had 15 running containers:

| Compose service | Current container state | Role in the running application |
|---|---|---|
| `mysql` | Up, Docker health `healthy` | Relational application data |
| `kafka` | Up | Event broker |
| `kafka-ui` | Up | Kafka administration UI |
| `influxdb` | Up, Docker health `healthy` | Time-series storage |
| `mailpit` | Up, Docker health `healthy` | Non-production mail sink |
| `keycloak` | Up | Development identity provider |
| `user-service` | Up | User-profile service |
| `device-service` | Up | Device service |
| `ingestion-service` | Up | Telemetry ingestion |
| `ml-inference-service` | Up | Baseline inference |
| `usage-service` | Up | Usage processing |
| `alert-service` | Up | Alert processing |
| `insight-service` | Up | Insight service |
| `api-gateway` | Up | Public API entry point |
| `frontend` | Up | Web application |

`prometheus` and `grafana` belong to the same project but were already stopped before this planning task. They must remain stopped during both the maintenance window and the later primary-stack restoration unless separately approved.

### Persistent-state evidence

| State | Compose-managed volume / mount | Implication of `docker compose stop` |
|---|---|---|
| MySQL | `home-energy-tracker_db-data` → `/var/lib/mysql` | The named volume remains attached and is not deleted. |
| Kafka | `home-energy-tracker_kafka-data` → `/var/lib/kafka/data` | The named volume remains attached and is not deleted. |
| InfluxDB | `home-energy-tracker_influx-data` → `/var/lib/influxdb2` | The named volume remains attached and is not deleted. |
| Prometheus | `home-energy-tracker_prometheus-data` | Remains untouched while Prometheus stays stopped. |
| Grafana | `home-energy-tracker_grafana-data` | Remains untouched while Grafana stays stopped. |
| Keycloak | Read-only realm-import bind mount only; no named persistent data volume was observed | `stop` preserves the existing Keycloak container writable layer. **Do not use `down`, remove, recreate, or prune commands**, or live Keycloak state may be lost. |

`docker compose stop` stops existing containers; it does **not** remove containers, named volumes, networks, or databases. The following actions are expressly outside this plan because they can alter or delete state: `docker compose down`, `docker compose down -v`, `docker rm`, `docker volume rm`, `docker system prune`, image rebuilds, and container recreation.

## 2. Capacity assessment

Docker Desktop currently reports **3.696 GiB** of allocatable memory. The 15 running primary containers use approximately **2,890 MiB** in aggregate according to `docker stats --no-stream`.

The isolated provisioning stage needs only these five services:

| Isolated provisioning service | Analogous observed primary-container memory | Why essential |
|---|---:|---|
| MySQL | 224.1 MiB | Isolated application database and Flyway state |
| Keycloak | 358.7 MiB | Isolated OIDC issuer and administrator bootstrap |
| User Service | 209.8 MiB | Creates non-production profiles |
| Device Service | 209.8 MiB | Creates and verifies aggregate-meter devices |
| API Gateway | 210.6 MiB | Secured provisioning path |
| **Observed analogue total** | **1,213.0 MiB (~1.18 GiB)** | Minimum functional provisioning stage |

This is an evidence-based working-set estimate, not a reserved memory limit or a capacity guarantee. It excludes Docker/Windows overhead and uses the current primary containers only as analogous measurements. It nevertheless demonstrates that running both stacks together is unsafe on the present 3.696 GiB Docker allocation: the primary stack leaves only about 0.87 GiB of observed headroom, less than the observed analogue total for the isolated provisioning stage.

The later isolated **telemetry** profile (Kafka, InfluxDB, Mailpit, ML, Ingestion, Usage, and Alert services) is **not included** in this maintenance plan and requires a separate memory assessment before it is started.

## 3. Mandatory pre-stop gates

Before any maintenance command, all of the following need explicit human approval or verified evidence:

1. **Outage approval:** acknowledge that the primary web application, API, Wokwi ingestion path, and local demonstration services will be unavailable while the isolated provisioning stage runs.
2. **Fresh recovery-point decision:** the Step 1 backup is documented, but it predates the current maintenance window. No current consistent backup/restore test has been verified. Approve a fresh, MySQL-aware backup procedure and an isolated restore-test policy before treating the window as recoverable.
3. **Baseline manifest:** record the exact project status, service state, memory, published ports, and named volumes immediately before the stop. The target baseline is 15 services up and `prometheus`/`grafana` stopped.
4. **No-concurrency rule:** confirm that the isolated deployment is limited to the five-service provisioning stage; the primary project stays stopped while that stage runs.
5. **No destructive fallback:** agree that failures will preserve containers and volumes for diagnosis. No `down`, `-v`, delete, reset, prune, migration, replay, or credential reuse is permitted.

## 4. Approved-execution sequence (for later use only)

The commands in this section are documented for a future approved maintenance window. They were **not run** during this planning task.

### 4.1 Pre-stop read-only checks

```powershell
docker compose --project-name home-energy-tracker --file .\docker-compose.yml ps -a
docker stats --no-stream
docker volume ls --filter label=com.docker.compose.project=home-energy-tracker
docker network ls --filter label=com.docker.compose.project=home-energy-tracker
```

Confirm MySQL, InfluxDB, and Mailpit still report `healthy`; inspect the current Kafka container state; and preserve the output in a maintenance manifest without recording secrets.

### 4.2 Graceful, scoped stop

Stop only the 15 services that are currently running; do not touch the already stopped observability services and do not use `down`:

```powershell
docker compose --project-name home-energy-tracker --file .\docker-compose.yml stop --timeout 30 frontend api-gateway insight-service alert-service usage-service ml-inference-service ingestion-service device-service user-service keycloak mailpit influxdb kafka-ui kafka mysql
```

The ordering quiesces public entry points and downstream consumers before Kafka and MySQL. `--timeout 30` provides a bounded graceful-shutdown period. After the command, verify `docker compose ... ps -a` reports the 15 target services as stopped and that the named volumes still exist.

### 4.3 Isolated-stage boundary

Only after that validation may the separate `refit-step2` **provisioning** stage be considered for launch. The stage must use its dedicated volumes and network and must not start its telemetry profile. Its failure must not lead to deletion of either project’s volumes.

### 4.4 Restore the primary stack without recreating it

When the approved isolated window ends, stop the isolated project without removing it, then start the original primary containers in stages. The following use `start`, not `up`, so the existing containers and their writable layers/attached volumes are reused rather than recreated.

```powershell
# Stage R1: storage, broker, identity, and local mail sink
docker compose --project-name home-energy-tracker --file .\docker-compose.yml start mysql kafka influxdb mailpit keycloak

# Stage R2: wait for storage/broker readiness, then core services
docker compose --project-name home-energy-tracker --file .\docker-compose.yml start user-service device-service ml-inference-service kafka-ui

# Stage R3: event consumers and business processing
docker compose --project-name home-energy-tracker --file .\docker-compose.yml start ingestion-service usage-service alert-service

# Stage R4: dependent API and UI
docker compose --project-name home-energy-tracker --file .\docker-compose.yml start insight-service api-gateway frontend
```

Do **not** include `prometheus` or `grafana`; their pre-window state was stopped. Do not advance to a later stage until the required health evidence below is collected.

## 5. Post-restart health and data-preservation checks

All checks below are read-only health/metadata checks for a future approved execution.

| Stage | Check | Acceptance criterion |
|---|---|---|
| R1 — MySQL | `docker inspect -f '{{.State.Health.Status}}' mysql` | `healthy` before User/Device/Alert services start. |
| R1 — InfluxDB | `docker inspect -f '{{.State.Health.Status}}' influxdb` and `Invoke-WebRequest http://localhost:8072/health` | Container reports `healthy`; HTTP status is 200. |
| R1 — Kafka | `docker inspect -f '{{.State.Status}} {{.State.OOMKilled}}' kafka`; sanitized broker logs; then a read-only topic-list check from the container | `running`, `OOMKilled=false`, broker reports started, and metadata request succeeds. Do not continue on an OOM or broker-start failure. |
| R1 — Keycloak | `Invoke-WebRequest http://localhost:8180/realms/home-energy/.well-known/openid-configuration` | HTTP 200 before Gateway readiness is evaluated. |
| R2/R3 — internal services | Read-only `/actuator/health` checks over the Docker network | User, Device, Ingestion, Usage, Alert, Insight, and Gateway each return HTTP 200. |
| R4 — public application | `Invoke-WebRequest http://localhost:3000/` and `Invoke-WebRequest http://localhost:8080/actuator/health` | Both return HTTP 200. |
| Final state | `docker compose ... ps -a`, `docker stats --no-stream`, named-volume inventory | 15 intended primary services up; Prometheus/Grafana remain stopped; volumes still present; no unexpected OOM state. |

For the Kafka metadata check, use only a read-only command such as `kafka-topics.sh --bootstrap-server localhost:9092 --list` inside the broker after it is running. It must not create topics or alter retention/configuration.

## 6. Failure containment and recovery

### If the isolated provisioning stack fails

1. Do not delete its containers, volumes, or network; capture a sanitized `ps -a`, non-secret container state, and bounded diagnostic evidence.
2. Do not start the telemetry profile, create profiles/devices, generate mappings, submit events, or retry blindly.
3. Stop only the isolated containers if the approved maintenance scope permits it; do not use `down -v`.
4. Restore the primary stack using stages R1–R4 above and run the post-restart checks.
5. If primary recovery succeeds, record the isolated attempt as failed and keep its state intact for review.

### If the primary stack does not recover

1. Stop advancing the recovery sequence. Preserve all primary containers, networks, and volumes; do not remove/recreate anything.
2. If MySQL is not healthy, do not start database-dependent services and do not run Flyway/migration/database repair commands.
3. If Kafka is OOM-killed or fails broker readiness, do not enter a restart loop, enable replay, or start telemetry consumers. Collect non-secret resource and container-state evidence for a separate capacity decision.
4. If Keycloak fails, do not recreate it: its observed state is container-layer dependent and an isolated restore test has not been verified.
5. Escalate to a separate, explicitly authorized rollback/restore procedure. The existing Step 1 backup is evidence of a prior backup, not a verified current rollback point or restore test.

## 7. GO/NO-GO recommendation

**Current recommendation: NO-GO — maintenance execution is not authorized yet.**

A narrow conditional GO for Option A is reasonable only when the human operator explicitly approves the outage, a fresh recovery-point procedure, the no-concurrency rule, and the prohibition on destructive cleanup. The approved operation must be limited to the five-service isolated provisioning stage; the primary stack cannot be brought back concurrently on the current Docker memory allocation.

If the goal is to continue from provisioning into REFIT validation/replay later, a second maintenance window or a higher-capacity/other host is required. This plan does not authorize that later telemetry stage.
