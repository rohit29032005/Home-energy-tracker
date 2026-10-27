# Local ML API validation

**Execution date:** 2026-10-04 (local environment)

Command executed from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest ml-service\tests -q
```

Result: **3 passed** in 3.12 seconds, with one upstream FastAPI/Starlette TestClient deprecation warning.

The passing tests cover:

1. A Wokwi-compatible payload containing `deviceId`, `energyConsumed`, and `timestamp`.
2. Rejection of a negative energy value.
3. Loading the persisted model artefact for `/health` and `/predict`.

The saved model served by these tests is `random_forest-csv-20261003T205417Z`, with decision threshold `0.31`.

This is an in-process API validation only. Kafka consumption, alert propagation, and Docker-network execution were **not measured** because the Docker engine was unavailable in this environment.
