# Task 4F: Network, Volume, and Port Audit

## Scope

This report is based on read-only Docker metadata. Environment variables, secrets, and configuration values were not inspected.

## 1. Home Energy Tracker runtime network

| Field | Observed state |
|---|---|
| Compose project | `home-energy-tracker` |
| Network name | `home-energy-tracker_default` |
| Driver | Bridge |
| Internal | `false` |
| Attachable | `false` |
| Current active members | `mysql`, `kafka-ui` only |
| Stopped Home Energy Tracker containers | Retain configuration referencing the network but are not active members. |

This network is the existing application network. It is not the Task 4C expected isolated network `refit-task4c-network`.

## 2. Existing Home Energy Tracker mounts and named volumes

| Resource | Observed mount/volume identity | Status/importance |
|---|---|---|
| MySQL | `home-energy-tracker_db-data` mounted at `/var/lib/mysql` | Existing persistent application database; currently running and healthy. |
| InfluxDB | `home-energy-tracker_influx-data` mounted at `/var/lib/influxdb2` plus an anonymous configuration volume | Existing persistent time-series state; container currently stopped. |
| Kafka | `home-energy-tracker_kafka-data` mounted at `/var/lib/kafka/data` plus anonymous configuration/secrets mount identifiers | Existing persistent broker state; container currently stopped/OOM terminated. |
| Grafana | `home-energy-tracker_grafana-data` mounted at `/var/lib/grafana` | Existing monitoring state; container stopped. |
| Prometheus | `home-energy-tracker_prometheus-data` mounted at `/prometheus` | Existing monitoring state; container stopped. |
| Keycloak | Existing host import bind mounted at `/opt/keycloak/data/import` | Existing development identity import; container stopped. |

No Task 4F operation mounted, initialized, changed, or removed any of these resources.

## 3. Published-port inventory

The following are container port publications configured for the existing Home Energy Tracker project. A stopped container does not actively listen through its publication.

| Component | Host publication observed | Audit state |
|---|---|---|
| Frontend | `3000 -> 80` | Stopped |
| Grafana | `3001 -> 3000` | Stopped |
| Prometheus | `9090 -> 9090` | Stopped |
| Keycloak | `8180 -> 8080` | Stopped |
| API Gateway | `8080 -> 8080` | Stopped |
| Mailpit | `1025 -> 1025`, `8025 -> 8025` | Stopped |
| InfluxDB | `8072 -> 8086` | Stopped |
| Kafka UI | `8070 -> 8080` | Running, but broker unavailable |
| MySQL | `3306 -> 3306` | Running and healthy |

Other unrelated stopped containers also show historic port publications, including PostgreSQL/Redis/Qdrant ports. They are not part of Home Energy Tracker or REFIT and were not touched.

## 4. REFIT Task 4C isolation comparison

| Expected Task 4C resource | Audit observation | Result |
|---|---|---|
| Compose project `refit-task4c` | No matching labelled container | Absent |
| Network `refit-task4c-network` | No matching network | Absent |
| `refit-task4c-mysql-data` | No matching volume | Absent |
| `refit-task4c-kafka-data` | No matching volume | Absent |
| `refit-task4c-influx-data` | No matching volume | Absent |
| Loopback REFIT gateway publication | No Task 4C gateway container exists | Absent |

This matches the Task 4C–4E no-start expectation. There is no Docker evidence that the isolated REFIT composition initialized persistent stores or connected to the existing Home Energy Tracker volumes/networks.

## 5. Isolation warning

The existing `home-energy-tracker_default` network and its named volumes are live/persistent application resources. Any later REFIT execution plan must continue to avoid them. The current partially running state is not a license to reuse its MySQL, Kafka UI, ports, volume names, Keycloak import, or network.
