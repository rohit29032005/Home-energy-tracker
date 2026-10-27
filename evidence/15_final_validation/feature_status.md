# Current Feature Status

| Feature | Implemented | Historical live validation | Current evidence |
|---|---|---|---|
| Dataset audit and provenance | Yes | Yes | `evidence/01_dataset/` |
| Chronological preprocessing and ML training | Yes | Yes | `evidence/02_preprocessing/`, `evidence/03_ml_training/`, `evidence/04_ml_evaluation/` |
| FastAPI ML inference and Kafka worker | Yes | Historical legacy runtime capture; 18 current local tests on 2026-10-10 | `evidence/05_ml_integration/`, `evidence/13_end_to_end/`, `evidence/10_resilience/` |
| JWT, role, ownership, device-bound machine-token, and gateway-proof controls | Yes | Historical JWT/role/ownership/machine-token baseline; current focused gateway proof/device-binding tests: 8 gateway and 12 ingestion, plus protected downstream service tests on 2026-10-11 | `evidence/06_security/` |
| Private user/device service caller authentication | Yes | 8 device-service and 7 user-service focused verifier/controller tests; 3 usage-service and 2 alert-service outgoing-token mock-HTTP tests; no current Docker route test | `evidence/06_security/private_service_caller_authentication_tests.md` |
| Usage, alert, and insight direct HTTP boundary authentication | Yes | 10 usage authorization tests; 4 alert controller authorization tests inside an 11-test alert run; 4 insight controller and 1 insight-to-usage client test inside a 17-test Insight run, all on 2026-10-11; no current Docker route test | `evidence/06_security/gateway_protected_downstream_services_20261011.md` |
| Gateway/ingestion authorization-status regression | Fixed | Focused local authorization tests; no current Docker route test | `evidence/06_security/telemetry_device_binding_tests.md` |
| Alert deduplication | Yes | Historical live deduplication capture; 5 current local deduplication/delivery-failure tests on 2026-10-11 | `evidence/07_alert_deduplication/` |
| Email notification capture | Yes | Yes | `evidence/13_end_to_end/review2_e2e_results_20261005-214326.json` |
| Prometheus/Grafana observability | Yes | Historical 8/8 targets up; current development/production config parsed statically | `evidence/08_observability/` |
| k6 ingestion load scenario | Yes | Yes, 450/450 accepted | `evidence/09_performance/` |
| Fault-injection recovery runner | Yes | Yes, container-state recovery for Mailpit and ML inference only | `evidence/10_resilience/` |
| Frontend production container | Yes | Yes, HTTP 200 | `evidence/12_integration_tests/runtime_dashboard_api_validation_20261005.md` |
| Frontend role-aware account creation | Yes | Local lint and production build passed after USER/Admin UI gating; browser role acceptance not currently rerun | `evidence/12_integration_tests/frontend_authorization_ui_validation_20261011.md` |
| End-to-end telemetry to email | Yes | Historical dated run passed; no current Docker re-run | `evidence/13_end_to_end/review2_e2e_results_20261005-214326.json` |
