# Task 4C — Configuration Difference and Preservation Report

## Original files preserved

Task 4C created files only under `experiments/refit_task4c_deployment_preparation/`. It did not edit, stage, reset, or restore the existing Compose files.

The worktree already contained changes before Task 4C began. That pre-existing state was preserved and is not represented as a clean baseline.

| File | SHA-256 captured before Task 4C writes | Post-write verification |
|---|---|---|
| `docker-compose.yml` | `D3DE1644FC07816562283724C0C63AE79F9E022881A802466392B3D4EF6BF9E7` | Same SHA-256 after Task 4C writes |
| `docker-compose.prod.yml` | `556C33763701AF29BDCC3293BC27171BE4BC9D7B879505350B917123DCC9A4B6` | Same SHA-256 after Task 4C writes |

## Material differences

| Concern | Existing development/production configuration | Task 4C experiment configuration |
|---|---|---|
| Location | Root `docker-compose.yml` and `docker-compose.prod.yml` | New `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml` |
| Service scope | Full application includes frontend, ML, Alert, Insight, identity provider, mail, and monitoring components | Exactly eight approved services only |
| Explicit container names | Present (`mysql`, `kafka`, `api-gateway`, and `home-energy-*-prod`) | None |
| Stateful volumes | `db-data`, `kafka-data`, `influx-data`, and `*-prod` volumes | `refit-task4c-mysql-data`, `refit-task4c-kafka-data`, `refit-task4c-influx-data` |
| Network | Dev implicit default; production `energy-net` | Explicit `refit-task4c-network` only |
| Host ports | Existing files expose MySQL, Kafka, InfluxDB, Gateway, UI, and monitoring ports | Only loopback gateway port 18080; every other service is internal |
| Kafka | Existing brokers use current cluster identifiers and shared broker state | Fresh `RefitTask4cClusterId01` and distinct storage |
| Influx | Existing `hometracker`/`usage-bucket` defaults | `refit_experiment`/`refit_experiment_usage` |
| Security | Dev file has local defaults including existing Keycloak values | Required REFIT-only OIDC variables, auth enabled, no Wokwi fallback, no legacy global device token |
| ML/alerts | Existing Compose starts ML and Alert workers | Both excluded; no replay/event service is declared |

## Source compatibility facts

- All five application Dockerfiles can be referenced from the new directory through `../../<service>/Dockerfile`; `docker compose config` resolves only their paths and does not build them.
- Internal URLs remain service DNS names, but those names resolve only on the dedicated Task 4C network when the configuration is eventually started.
- The Gateway source still declares Alert and Insight routes. Task 4C makes those routes fail closed rather than routing them to the current stack.
- The Task 4C compose must not be merged with either original Compose file. Running `docker compose -f docker-compose.yml -f docker-compose.refit.yml ...` would invalidate the isolation design.
