# Baseline ML Recovery Preparation and Local Artifact Check

**Execution date:** 2026-10-11  
**Scope:** deployable baseline Random Forest inference only; this record does
not claim that the optional REFIT controlled experiment or Docker/Kafka path
was live during this check.

## Issue isolated

The Docker image context previously included two optional experiment-artifact
directories that Windows/Docker could not read:

- `ml-service/models/refit-controlled-v1/`
- `ml-service/models/refit-controlled-v1.1/`

Those artifacts are used only by the explicitly separated controlled-REFIT
route. They are not required by the Wokwi-compatible baseline `/predict`
route.

## Recovery applied

The root `.dockerignore` now excludes only those two optional directories.
The Compose default for `REFIT_CONTROLLED_EXPERIMENTAL_ENABLED` is now `false`.
This keeps the baseline inference image buildable while making the experimental
route correctly report `DISABLED` until its artifacts are deliberately restored.
No baseline model file was changed.

## Static configuration check

Command executed from the repository root:

```powershell
docker compose config --quiet
```

Observed result: command exited successfully (Compose syntax/configuration
resolved without output).

## Local baseline-model evidence

Accessible persisted artifacts:

| Artifact | Observed state |
| --- | --- |
| `anomaly_model.joblib` | Present; 3,835,698 bytes |
| `model_metadata.json` | Present; baseline version `random_forest-csv-20261003T205417Z` |
| Model family | Random Forest pipeline |
| Input features | 8 |

The model metadata records an 8-feature supervised baseline and a decision
threshold of `0.31`. The metadata's historical held-out metrics are training
artefact metadata, not a new runtime experiment.

The following direct, local artifact check was executed using the project
virtual environment. The test intentionally set `n_jobs=1` only in memory to
avoid local parallel-worker variability; it did not modify the saved model.

```powershell
.venv\Scripts\python.exe -c "import joblib,pandas as pd; model=joblib.load('ml-service/models/anomaly_model.joblib'); model.set_params(model__n_jobs=1); frame=pd.DataFrame([{'Electricity_Consumed':0.55,'Temperature':0.50,'Humidity':0.45,'Wind_Speed':0.40,'Avg_Past_Consumption':0.50,'Hour':3,'DayOfWeek':6,'ConsumptionDeviation':0.05}]); print('BASELINE_PREDICTION_OK=' + str(round(float(model.predict_proba(frame)[0,1]),6)))"
```

Observed output:

```text
BASELINE_PREDICTION_OK=0.0
```

This proves that the accessible persisted baseline model can be deserialized
and score the stated 8-feature input in the local environment. It is not proof
of a running Docker HTTP endpoint, Kafka consumer, alert, or REFIT experiment.

The application-level inference path was then checked with the same explicit
single-worker setting:

```powershell
$env:REFIT_CONTROLLED_EXPERIMENTAL_ENABLED='false'
$env:KAFKA_ENABLED='false'
$env:ML_MODEL_N_JOBS='1'
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'ml-service'); from app.main import MODEL_STORE,TelemetryInput,predict_telemetry; MODEL_STORE.load(); payload=TelemetryInput.model_validate({'deviceId':7,'energyConsumed':0.55,'timestamp':'2024-04-14T03:30:00Z','temperature':0.50,'humidity':0.45,'windSpeed':0.40,'avgPastConsumption':0.50}); result=predict_telemetry(payload); print('APP_BASELINE_PREDICT_OK'); print(result.model_version); print(result.anomaly_probability); print(result.imputed_features)"
```

Observed output:

```text
APP_BASELINE_PREDICT_OK
random_forest-csv-20261003T205417Z
0.0
[]
```

This validates the application helper that builds the feature frame, applies
the configured worker cap, performs `predict_proba`, and returns the declared
output fields. A direct FastAPI `TestClient` lifecycle check in the current
local virtual environment stalled after the first two contract tests while
entering the test client. That local harness currently emits a Starlette
deprecation warning that calls for `httpx2`, which is absent from the virtual
environment; it is recorded as a test-environment compatibility issue rather
than being presented as a passing HTTP test.

## Current live-runtime boundary

At the end of this check, the following public host endpoints were
unreachable from the validation shell:

- `http://localhost:8080/actuator/health`
- `http://localhost:3000/`
- `http://localhost:8180/realms/home-energy/.well-known/openid-configuration`
- `http://localhost:9090/-/ready`
- `http://localhost:3001/login`

The Docker CLI also could not access the Docker Desktop named pipe from this
validation context. Therefore no new live-container claim is made by this
record.

## Reproducible live check after Docker Desktop is healthy

Run these commands from an interactive PowerShell after `docker version` shows
both **Client** and **Server** sections:

```powershell
Set-Location 'C:\Users\anju2\Desktop\Home-Energy-Tracker'
docker compose config --quiet
docker compose up -d --build ml-inference-service
docker compose ps ml-inference-service
```

The service intentionally uses Docker-internal port `8090`, so check it inside
the container rather than from host port `8090`:

```powershell
docker compose exec -T ml-inference-service python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8090/health").read().decode())'
```

Expected boundary: the response should show `status: UP` for the baseline model
and `experimentalRefitControlled.status: DISABLED` while the optional REFIT
artefacts remain excluded.

Then exercise the baseline route:

```powershell
docker compose exec -T ml-inference-service python -c 'import json,urllib.request; data=json.dumps({"deviceId":1,"energyConsumed":0.55,"timestamp":"2026-10-11T00:00:00Z"}).encode(); req=urllib.request.Request("http://127.0.0.1:8090/predict",data=data,headers={"Content-Type":"application/json"},method="POST"); print(urllib.request.urlopen(req).read().decode())'
```

Acceptance condition: the command returns a JSON prediction containing a
baseline `modelVersion`, `anomalyProbability`, `decisionThreshold`, and any
explicitly imputed feature names. Record the actual returned values before
adding them to a report or paper.

## Live Docker ML verification completed

After Docker Desktop recovered, the complete Compose stack was started and the
public Gateway, frontend, Keycloak OIDC discovery, Prometheus readiness, and
Grafana login endpoints each returned HTTP `200` from the host PowerShell.

The following checks were then run interactively inside the live
`ml-inference-service` container on 2026-10-11. Interactive execution was
used because Windows PowerShell plus `docker compose exec ... python -c` had
removed nested URL quotes from the original one-line command; that was a shell
quoting issue, not an ML service failure.

### Health response

```json
{
  "status": "UP",
  "modelVersion": "random_forest-csv-20261003T205417Z",
  "experimentalRefitControlled": {
    "status": "DISABLED",
    "detail": "disabled by REFIT_CONTROLLED_EXPERIMENTAL_ENABLED"
  },
  "kafkaWorkers": {
    "legacy": {
      "enabled": true,
      "state": "connected",
      "connectionAttempts": 12,
      "lastConnectionError": null
    },
    "experimentalRefitControlled": {
      "enabled": false,
      "state": "disabled"
    }
  }
}
```

### Wokwi-compatible baseline prediction

Input:

```json
{
  "deviceId": 1,
  "energyConsumed": 0.55,
  "timestamp": "2026-10-11T00:00:00Z"
}
```

Observed response:

```json
{
  "deviceId": 1,
  "anomaly": false,
  "anomalyProbability": 0.0,
  "modelVersion": "random_forest-csv-20261003T205417Z",
  "decisionThreshold": 0.31000000000000005,
  "timestamp": "2026-10-11T00:00:00Z",
  "imputedFeatures": [
    "Temperature",
    "Humidity",
    "Wind_Speed",
    "Avg_Past_Consumption"
  ]
}
```

The four imputed fields are expected because the simulated Wokwi contract
sends only device ID, energy consumed, and timestamp. This result proves the
live container's baseline inference endpoint and its Kafka worker connection.
It does not, by itself, rerun the separate ingestion-to-alert end-to-end
scenario after this Docker restart.
