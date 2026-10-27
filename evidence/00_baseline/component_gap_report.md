# Component and gap map

| Component | Existing responsibility | Observed baseline state | Upgrade decision |
| --- | --- | --- | --- |
| React/Vite frontend | Dashboard and simulated-reading controls through `/api/v1`. | Source present; local npm command unavailable in this environment. | Keep; add only ML-result presentation after API integration is validated. |
| API Gateway | Routes public `/api/v1` paths to seven services; Actuator/Prometheus dependencies already present. | `SecurityConfig` is an empty class. | Add configurable Keycloak JWT validation and route-level authorization. |
| User service | MySQL household profiles and alert threshold settings. | Existing CRUD and Flyway-owned shared schema. | Preserve contract; add security-aware ownership support only where required. |
| Device service | MySQL device registration and lookup. | Existing CRUD, no ownership enforcement at gateway/service boundary. | Preserve contract; enforce ownership for authenticated gateway requests. |
| Ingestion service | Validates and publishes telemetry to `energy-usage`. | Kafka producer exists; payload has only device, energy, timestamp. | Preserve Wokwi-compatible fields; extend payload with optional contextual ML features. |
| Usage service | Kafka consumption, InfluxDB persistence, hour aggregation, threshold event generation. | Works independently from alert persistence but emits repeated threshold events each aggregation cycle. | Preserve persistence path; avoid changing deterministic insight semantics; connect ML result to alert evaluation through a separate event. |
| Alert service | Consumes threshold events, stores alerts, sends email. | No deduplication; duplicate inputs can create duplicate alerts. | Add configurable deduplication and tests. |
| Insight service | Deterministic forecast/ranking/standby outputs, optional Ollama narrative. | No supervised ML logic. | Keep deterministic analytics and label them distinctly from ML. |
| MySQL | Shared relational metadata and alert table. | Migrations owned by user service. | Add forward-only migration for alert deduplication metadata. |
| InfluxDB | `energy_usage` time-series measurement. | Used by usage service. | Retain; no claim of physical-meter calibration. |
| Kafka | `energy-usage` and `energy-alerts` event transport. | Producers/consumers present, no ML topic. | Add a dedicated anomaly-result topic and traceable error handling. |
| Wokwi simulator | Controlled ESP32 integration source. | Uses the existing ingestion JSON contract. | Preserve as controlled integration input; do not use its readings for ML evaluation. |
| ML anomaly detection | None. | Root CSV is labeled and suitable for supervised evaluation after audit. | Add a separate FastAPI inference service, reproducible preprocessing/training, and Kafka integration. |
| Observability | Actuator and Prometheus registry dependencies are broadly present. | No Compose Prometheus/Grafana configuration or evidence run. | Add usable metrics configuration and only claim runtime metrics after a live run. |
