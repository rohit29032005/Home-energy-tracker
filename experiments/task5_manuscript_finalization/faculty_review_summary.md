# Faculty review summary

## What has been completed

The project now has a documented microservices implementation for home-energy telemetry admission, Kafka-based event transfer, InfluxDB time-series persistence, MySQL metadata/alert state, deterministic insight functions, baseline ML inference, alert deduplication, and monitoring. The revised manuscript presents these as implementation contributions with evidence boundaries rather than as production guarantees.

The repository's historical Random Forest experiment has been checked carefully. It used a 5,000-record labelled CSV and a chronological 3,500/750/750 split. The historical held-out Random Forest F1 of 0.902439 was reproduced exactly offline, together with the recorded precision, recall, ROC-AUC, and PR-AUC. This proves reproducibility of the legacy experiment on the available copied input. It does not prove performance on a real household, REFIT, or a new experiment.

The REFIT preparation work is complete at the data-processing stage. Five official cleaned files were MD5 verified. Three non-solar primary households (H1/H2/H4) passed the pre-registered quality gates. Their 14-day windows produced 468,847 retained interval records and an estimated 386.398411389 kWh using the documented actual-delta sample-hold transformation. The preprocessing pipeline was rerun twice and the generated artifacts were byte-identical. Solar-affected H3/H11 data are deliberately separated as a sensitivity cohort.

## What the paper now claims

1. A local event-driven Home Energy Tracker has been implemented with clear service responsibilities and explicit telemetry, storage, inference, alert, and monitoring paths.
2. The historical Random Forest baseline is reproducible on its supplied data and should remain labelled as a historical CSV-specific evaluation.
3. REFIT preparation is source-traceable, quality-gated, unit-documented, and deterministic.
4. The work is ready for an academic review of architecture, methodology, reproducibility, and experimental planning.

## What is not claimed

- REFIT data have not been sent to the API or replayed through Kafka, storage, ML, alerts, or notifications.
- There is no REFIT anomaly accuracy, precision, recall, F1, ROC-AUC, or latency/throughput measurement.
- A live ML endpoint smoke test verifies model loading and response formatting only; it is not an accuracy or complete end-to-end result.
- The project has not established calibrated meter accuracy, utility-bill agreement, production security, or production-scale resilience.

## Why the next experiment is gated

The current 8 GB Windows laptop cannot safely run the main stack and a separate isolated REFIT provisioning stack at the same time. The experiment needs isolated database volumes, Kafka, Keycloak identity, three test profiles/devices, and fresh non-production credentials. The device-token mapping must be verified before any recorded household measurement is submitted. These safeguards prevent replayed data from changing the existing development environment or being attributed to the wrong device.

## Recommended faculty discussion

The appropriate next academic decision is whether to approve the controlled isolated deployment and pilot replay protocol. The pilot should be small, chronological, authenticated, and completely reconciled before any full H1/H2/H4 run. A later anomaly-accuracy experiment additionally needs an independently verified aggregate-label and feature-mapping protocol. Until those gates are completed, the manuscript is suitable for faculty review as a strong engineering implementation and reproducibility report, but it is not ready for a high-tier journal submission claiming real-world anomaly performance.
