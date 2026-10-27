# Task 4B — Deployment-Only Validation Checklist

**Important:** This is a future validation design. None of the stages below was executed in Task 4B. All checks must complete before any deployment creation, device provisioning, token injection, or data submission is approved.

| Stage | Future read-only evidence | Pass condition | Fail condition and required action |
|---|---|---|---|
| 1. Static Compose review | Reviewed proposed isolated Compose file plus environment template, compared with `docker-compose.yml` and `docker-compose.prod.yml`. | No inherited fixed container names, shared volumes, `energy-net`, host ports, or baseline secret references. | **Fail:** revise the proposed deployment file; do not create it/run it. |
| 2. Port-conflict inspection | Read-only host-port inventory plus proposed port list. | Every proposed exposed port is unused and does not equal a current production/development binding unless explicitly reserved. | **Fail:** allocate different ports; do not stop or restart existing services. |
| 3. Network-boundary review | Static network declarations, service DNS URLs, and external-network flags. | Every experiment service uses only `refit-experiment-net`; no service joins current default/`energy-net`; no `external: true` shared network. | **Fail:** remove the cross-network attachment or change the planned deployment. |
| 4. Secret/version-control review | `git check-ignore`/repository review of the planned secret file; template contains only placeholders. | Secret file is ignored; no token/password appears in tracked files, command history artifacts, reports, or Compose YAML. | **Fail:** rotate any exposed secret and redesign secret injection before proceeding. |
| 5. Health/readiness design review | Proposed health checks and `depends_on` gates for MySQL, Kafka, InfluxDB, gateway, user/device, ingestion, and usage. | Each data dependency has a concrete readiness signal; application requests are blocked until health gates pass. | **Fail:** add or document readiness gates; do not start a deployment. |
| 6. Storage/broker isolation review | Planned MySQL database/volume, Kafka cluster/volume, Influx org/bucket/volume, and credentials. | All names/locations/credentials use a `refit-exp` namespace and differ from the current stack. | **Fail:** create a separate resource plan; never reuse baseline volumes/broker/bucket. |
| 7. ML consumer exclusion review | Proposed service list and environment settings; static scan for `KAFKA_ENABLED`/ML service. | Legacy `ml-inference-service` and alert service are absent from initial validation; no consumer can subscribe to experiment `energy-usage`. | **Fail:** remove ML/Alert from the initial plan or obtain a separate approved ML protocol. |
| 8. Data-contract review | Task 2 schema, Task 3 protocol, and future adapter design review. | Mapping remains `derived_interval_energy_kwh -> energyConsumed`; raw watts are not mapped; original/replay timestamp ledger behavior is explicit. | **Fail:** stop before writing a replay engine or payload. |
| 9. Device/token design review | Non-secret House→profile→returned-device-ID ledger template and token-reference plan. | Three profiles and three devices are planned; one token per returned device ID; no numeric ID inference. | **Fail:** correct the mapping plan; do not create profiles/tokens. |
| 10. Final approval gate | Signed/explicit approval that names the isolated deployment, three profiles/devices, three secret references, and allowed validation scope. | Approval covers only provisioning and dry-run preparation; it does not imply first event submission. | **Fail/absent:** stop. |

## Planned evidence set before an eventual deployment creation

1. Static rendered Compose configuration (no secrets shown).
2. Port inventory and collision-free allocation record.
3. Explicit network/volume/resource-name inventory.
4. Ignored-secret-file confirmation and placeholder-only public template review.
5. Health-check/depends-on matrix.
6. Broker, MySQL, and Influx separation checklist.
7. ML/Alert service exclusion proof.
8. Explicit user approval for the next stage.

## Explicit non-goals

This checklist does not authorize `docker compose up`, build, restart, device creation, token creation, endpoint calls, Kafka publication, REFIT replay, model execution, model training, anomaly generation, or cleanup.
