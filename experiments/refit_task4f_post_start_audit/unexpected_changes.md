# Task 4F: Unexpected Changes and Comparison with Task 4C–4E

## Comparison basis

Tasks 4C–4E established that no REFIT deployment had been started, no REFIT persistent stores should exist, and the existing Home Energy Tracker stack must remain unchanged. This Task 4F audit checked Docker runtime metadata only.

## Expected state that was confirmed

| Expected from prior tasks | Current audit observation | Assessment |
|---|---|---|
| No `refit-task4c` Compose project/container | No matching Compose-labelled container exists. | Confirmed. |
| No `refit-task4c-network` | No matching Docker network exists. | Confirmed. |
| No Task 4C MySQL/Kafka/Influx named volumes | No matching Docker volumes exist. | Confirmed. |
| No REFIT stack start or persistent-store initialization | No Task 4C runtime resources are present. | Confirmed by Docker metadata. |
| Existing application must not be modified by REFIT work | This audit performed no Docker lifecycle action or file/configuration edit. | Confirmed for Task 4F actions. |

## Unexpected or blocking runtime state

| ID | Finding | Evidence | Impact |
|---|---|---|---|
| U-01 | Existing Home Energy Tracker stack is partially down. | Only `mysql` and `kafka-ui` are running; Gateway, Keycloak, frontend, business services, InfluxDB, monitoring, Alert, and ML are exited. | Existing application is not ready and should not be used as a reference for a new REFIT deployment. |
| U-02 | Kafka broker was OOM-killed. | Docker state shows exit `137` and `OOMKilled=true` for `kafka`. | Existing event pipeline is unavailable; requires separate diagnosis. |
| U-03 | Kafka UI restarted without a working broker. | `kafka-ui` is running while Kafka is stopped; redacted log review shows failed broker resolution/connectivity. | UI availability is misleading and not a health signal for Kafka. |
| U-04 | Fifteen Home Energy Tracker containers exited at nearly the same timestamp with code `255`. | Docker state metadata shows same-time, non-OOM, empty-error exits. | Suggests shared lifecycle interruption, but root cause is unproven. |
| U-05 | Docker aggregate container summary conflicts with direct enumeration. | `docker info` reported 16 running containers, while direct `docker ps -a` showed two running containers. | Docker summary metadata should not be relied on until separately investigated. |
| U-06 | Historic unrelated stopped/created containers exist. | Trustid, her, Redis, and Qdrant containers are present but not part of Home Energy Tracker/REFIT. | Avoid broad cleanup/prune commands; they could affect unrelated work. |

## Changes explicitly not observed

- No Task 4C REFIT container, network, volume, port binding, or Compose label appeared.
- No REFIT Keycloak/OIDC realm container or isolated identity storage appeared.
- No REFIT MySQL/InfluxDB/Kafka initialization artifact appeared.
- No evidence was found that REFIT H1/H2/H4 profiles, devices, or device-bound mappings were created through Docker runtime state.
- No existing Home Energy Tracker Compose/source/environment file was modified by this audit.

## Interpretation

The absence of REFIT resources is good and matches the prior no-start decision. The existing project's partial restart state is nevertheless an unexpected operational condition. It makes a separate clean REFIT execution plan even more important and rules out proceeding based on the assumption that the current existing stack is healthy.
