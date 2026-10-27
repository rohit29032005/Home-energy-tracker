# ML inference service

The root `smart_meter_data.csv` is used only for supervised anomaly-model training and evaluation. The Wokwi ESP32 simulator remains a controlled live-integration telemetry source and is not used as a training or benchmark dataset.

## Local workflow

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r ml-service\requirements-dev.txt
.\.venv\Scripts\python ml-service\training\train.py
.\.venv\Scripts\uvicorn app.main:app --app-dir ml-service --host 127.0.0.1 --port 8090
```

`POST /predict` accepts the existing `deviceId`, `energyConsumed`, and `timestamp` fields. It optionally accepts `temperature`, `humidity`, `windSpeed`, and `avgPastConsumption`. Missing contextual features are imputed from training-set medians and returned in `imputedFeatures`; the service returns a model probability, never a generic confidence claim.
# Runtime packaging

The Docker image serves the evaluated artefact in `models/`; it does not train
at image-build or container-start time. To reproduce training and generate a
replacement artefact from the root dataset, install `requirements-dev.txt` and
run `python training/train.py --dataset ../smart_meter_data.csv` from this
directory. This keeps deployment deterministic while preserving a separate,
auditable training step.
