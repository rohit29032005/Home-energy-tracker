# Task 4F: Docker Runtime Status

## Audit scope

This audit used read-only Docker Engine inspection only. It did not start, stop, build, pull, restart, recreate, inspect environment variables, change a resource, send an HTTP request, or expose any credential/token/secret.

## Docker Engine availability

| Check | Observed result | Interpretation |
|---|---|---|
| Docker client version | `29.7.2` | Docker CLI is installed. |
| Docker Engine server version | `29.7.2` | Docker Desktop/Engine was reachable for read-only inspection. |
| Engine platform | Docker Desktop, `x86_64` | Linux container engine is available through the active Docker context. |
| Direct container enumeration | 2 currently running containers; 34 created/exited containers enumerated | This is the authoritative inventory used in this report. |
| Docker Engine aggregate summary | `running=16`, `stopped=20` | This conflicts with direct `docker ps -a` enumeration and is recorded as an unexplained Docker metadata inconsistency. |

The Engine is available, but Engine availability does not mean the Home Energy Tracker application is healthy or that any REFIT deployment is authorized.

## Existing Home Energy Tracker stack

The existing stack is identified by Compose project label `home-energy-tracker` and configuration path `C:\Users\anju2\Desktop\Home-Energy-Tracker\docker-compose.yml`. It has 17 known project containers.

| State | Count | Components |
|---|---:|---|
| Running | 2 | `mysql` (healthy), `kafka-ui` (running) |
| Exited | 15 | Kafka plus Gateway, Keycloak, frontend, all business services, InfluxDB, monitoring, ML, Alert, and Mailpit services |
| Healthy end-to-end application path | 0 | Gateway, Keycloak, frontend, Kafka, User/Device/Ingestion/Usage services are not running. |

Restart policies explain why two infrastructure-adjacent containers started while most services remained down:

| Container | Restart policy | Current state |
|---|---|---|
| `mysql` | `always` | Running and Docker-healthcheck healthy. |
| `kafka-ui` | `unless-stopped` | Running, but its dependent Kafka broker is stopped. |
| Remaining Home Energy Tracker containers | `no` | Not restarted automatically after the observed lifecycle interruption. |

## REFIT Task 4C status

The following read-only filtered checks all returned no resources:

- no container with Compose project label `refit-task4c`;
- no container name matching REFIT resources;
- no network named `refit-task4c-network`; and
- no volume named or Compose-labelled for `refit-task4c`.

Therefore the isolated REFIT Task 4C deployment was **not** started accidentally. No Task 4C persistent-store initialization, profile/device provisioning, device-secret mapping, ingestion, replay, or model execution is evidenced by Docker runtime state.

## Current audit conclusion

Docker Engine is running, but the existing Home Energy Tracker stack is partially down and Kafka has a recorded OOM termination. This is an unexpected state that must be handled by a separately authorized existing-stack diagnosis/recovery task. It does not permit REFIT deployment, bootstrap, or replay.
