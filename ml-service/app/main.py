"""FastAPI inference service for the empirically trained anomaly classifier.

The service intentionally reports a model probability, not a misleading generic
"confidence". Context fields absent from live Wokwi telemetry are imputed with
training-set medians and are listed in the response.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.refit_controlled import RefitControlledEngine, RefitControlledError

LOGGER = logging.getLogger("ml_inference")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path(os.getenv("MODEL_DIR", SERVICE_ROOT / "models"))
MODEL_PATH = MODEL_DIR / "anomaly_model.joblib"
METADATA_PATH = MODEL_DIR / "model_metadata.json"
REFIT_CONTROLLED_MODEL_DIR = Path(
    os.getenv("REFIT_CONTROLLED_MODEL_DIR", SERVICE_ROOT / "models" / "refit-controlled-v1.1")
)
REFIT_CONTROLLED_EXPERIMENTAL_ENABLED = (
    os.getenv("REFIT_CONTROLLED_EXPERIMENTAL_ENABLED", "true").lower() == "true"
)
REFIT_CONTROLLED_KAFKA_ENABLED = (
    os.getenv("REFIT_CONTROLLED_KAFKA_ENABLED", "false").lower() == "true"
)


def _configured_model_n_jobs() -> int:
    """Return a safe inference-worker count for the persisted Random Forest.

    The trained artefact stores ``n_jobs=-1``, which can oversubscribe a
    constrained Windows or Docker Desktop host for a single telemetry request.
    Keep one worker by default and let an operator deliberately override the
    setting after sizing the deployment.
    """

    raw_value = os.getenv("ML_MODEL_N_JOBS", "1").strip()
    try:
        configured_value = int(raw_value)
    except ValueError:
        LOGGER.warning("Invalid ML_MODEL_N_JOBS=%r; using 1", raw_value)
        return 1
    if configured_value == 0:
        LOGGER.warning("ML_MODEL_N_JOBS cannot be 0; using 1")
        return 1
    return configured_value
LEGACY_KAFKA_WORKER: Any | None = None
REFIT_CONTROLLED_KAFKA_WORKER: Any | None = None

PREDICTION_COUNTER = Counter(
    "ml_inference_predictions_total",
    "Number of completed anomaly predictions",
    ["prediction"],
)
PREDICTION_FAILURES = Counter(
    "ml_inference_prediction_failures_total",
    "Number of inference failures",
)
PREDICTION_LATENCY = Histogram(
    "ml_inference_latency_seconds",
    "Time spent producing anomaly predictions",
)
REFIT_CONTROLLED_EVENTS = Counter(
    "refit_controlled_experimental_events_total",
    "Experimental REFIT controlled-model meter events by input state",
    ["input_state"],
)
REFIT_CONTROLLED_CLOSED_BINS = Counter(
    "refit_controlled_experimental_closed_bins_total",
    "Experimental REFIT controlled-model closed bins by state",
    ["state"],
)


class TelemetryInput(BaseModel):
    """Telemetry accepted from the API or Kafka worker.

    `deviceId`, `energyConsumed`, and `timestamp` match the pre-existing Wokwi
    contract. The remaining fields are optional context from a richer meter or
    gateway; their absence is made explicit in the response.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    device_id: int = Field(alias="deviceId", ge=1)
    energy_consumed: float = Field(alias="energyConsumed", ge=0)
    timestamp: datetime
    temperature: float | None = Field(default=None, alias="temperature")
    humidity: float | None = Field(default=None, alias="humidity")
    wind_speed: float | None = Field(default=None, alias="windSpeed")
    avg_past_consumption: float | None = Field(default=None, alias="avgPastConsumption")

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PredictionOutput(BaseModel):
    device_id: int = Field(alias="deviceId")
    anomaly: bool
    anomaly_probability: float = Field(alias="anomalyProbability")
    model_version: str = Field(alias="modelVersion")
    decision_threshold: float = Field(alias="decisionThreshold")
    timestamp: datetime
    imputed_features: list[str] = Field(alias="imputedFeatures")

    model_config = ConfigDict(populate_by_name=True)


class RefitControlledTelemetryInput(BaseModel):
    """Explicit replay contract for the separate REFIT experimental adapter.

    The caller selects a declared REFIT profile and caller-owned stream key.
    This deliberately does not accept a Wokwi `deviceId` as a profile mapping.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    refit_profile_id: Literal[1, 2, 3, 4, 11] = Field(alias="refitProfileId")
    stream_id: str = Field(alias="streamId", min_length=1, max_length=160)
    energy_consumed: float = Field(alias="energyConsumed", ge=0)
    timestamp: datetime
    interval_seconds: int = Field(alias="intervalSeconds", ge=1, le=16)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone, for example Z")
        return value.astimezone(timezone.utc)


class ModelStore:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.metadata: dict[str, Any] | None = None

    def load(self) -> None:
        if not MODEL_PATH.exists() or not METADATA_PATH.exists():
            raise FileNotFoundError(
                "Trained model artifacts are unavailable. Run ml-service/training/train.py first."
            )
        self.model = joblib.load(MODEL_PATH)
        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        parameters = self.model.get_params(deep=True) if hasattr(self.model, "get_params") else {}
        if "model__n_jobs" in parameters:
            self.model.set_params(model__n_jobs=_configured_model_n_jobs())
        LOGGER.info("Loaded model version %s from %s", self.metadata["model_version"], MODEL_PATH)

    @property
    def ready(self) -> bool:
        return self.model is not None and self.metadata is not None


MODEL_STORE = ModelStore()


class RefitControlledStore:
    """Optional model store isolated from the legacy Wokwi-compatible model."""

    def __init__(self) -> None:
        self.engine: RefitControlledEngine | None = None
        self.error: str | None = None

    def load(self) -> None:
        if not REFIT_CONTROLLED_EXPERIMENTAL_ENABLED:
            self.error = "disabled by REFIT_CONTROLLED_EXPERIMENTAL_ENABLED"
            return
        try:
            self.engine = RefitControlledEngine.load(REFIT_CONTROLLED_MODEL_DIR)
            self.error = None
            LOGGER.info(
                "Loaded isolated experimental REFIT controlled artifact %s from %s",
                self.engine.model_version,
                REFIT_CONTROLLED_MODEL_DIR,
            )
        except Exception as exc:
            self.engine = None
            self.error = str(exc)
            LOGGER.exception("Experimental REFIT controlled artifact is unavailable")

    @property
    def ready(self) -> bool:
        return self.engine is not None


REFIT_CONTROLLED_STORE = RefitControlledStore()


def _feature_frame(payload: TelemetryInput) -> tuple[pd.DataFrame, list[str]]:
    if not MODEL_STORE.ready:
        raise RuntimeError("Model is not loaded")
    assert MODEL_STORE.metadata is not None

    defaults = MODEL_STORE.metadata["feature_defaults"]
    values = {
        "Electricity_Consumed": payload.energy_consumed,
        "Temperature": payload.temperature,
        "Humidity": payload.humidity,
        "Wind_Speed": payload.wind_speed,
        "Avg_Past_Consumption": payload.avg_past_consumption,
    }
    imputed = [name for name, value in values.items() if value is None]
    for name in imputed:
        values[name] = defaults[name]

    timestamp = payload.timestamp.astimezone(timezone.utc)
    values["Hour"] = timestamp.hour
    values["DayOfWeek"] = timestamp.weekday()
    values["ConsumptionDeviation"] = values["Electricity_Consumed"] - values["Avg_Past_Consumption"]

    feature_names = MODEL_STORE.metadata["features"]
    return pd.DataFrame([{name: values[name] for name in feature_names}]), imputed


def predict_telemetry(payload: TelemetryInput) -> PredictionOutput:
    if not MODEL_STORE.ready:
        raise RuntimeError("Model is not loaded")
    assert MODEL_STORE.model is not None
    assert MODEL_STORE.metadata is not None

    frame, imputed = _feature_frame(payload)
    probability = float(MODEL_STORE.model.predict_proba(frame)[0, 1])
    threshold = float(MODEL_STORE.metadata["decision_threshold"])
    anomaly = probability >= threshold
    PREDICTION_COUNTER.labels(prediction=str(anomaly).lower()).inc()
    return PredictionOutput(
        device_id=payload.device_id,
        anomaly=anomaly,
        anomaly_probability=round(probability, 6),
        model_version=MODEL_STORE.metadata["model_version"],
        decision_threshold=threshold,
        timestamp=payload.timestamp,
        imputed_features=imputed,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global LEGACY_KAFKA_WORKER, REFIT_CONTROLLED_KAFKA_WORKER
    try:
        MODEL_STORE.load()
    except Exception:
        LOGGER.exception("Model startup failed; prediction endpoint will return 503")
    REFIT_CONTROLLED_STORE.load()
    worker = None
    if os.getenv("KAFKA_ENABLED", "false").lower() == "true":
        from app.kafka_worker import KafkaInferenceWorker

        worker = KafkaInferenceWorker()
        worker.start()
        LEGACY_KAFKA_WORKER = worker
    refit_worker = None
    if REFIT_CONTROLLED_KAFKA_ENABLED and REFIT_CONTROLLED_STORE.ready:
        from app.refit_kafka_worker import RefitControlledKafkaWorker

        assert REFIT_CONTROLLED_STORE.engine is not None
        refit_worker = RefitControlledKafkaWorker(REFIT_CONTROLLED_STORE.engine)
        refit_worker.start()
        REFIT_CONTROLLED_KAFKA_WORKER = refit_worker
    elif REFIT_CONTROLLED_KAFKA_ENABLED:
        LOGGER.warning(
            "REFIT_CONTROLLED_KAFKA_ENABLED is true but the isolated experimental artifact is unavailable"
        )
    yield
    if worker is not None:
        worker.stop()
    LEGACY_KAFKA_WORKER = None
    if refit_worker is not None:
        refit_worker.stop()
    REFIT_CONTROLLED_KAFKA_WORKER = None


app = FastAPI(
    title="Home Energy Tracker ML Inference",
    version="1.1.0",
    description=(
        "Legacy supervised inference plus an explicit, isolated REFIT controlled-perturbation "
        "experimental adapter. The two model contracts are intentionally separate."
    ),
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, Any]:
    if not MODEL_STORE.ready:
        raise HTTPException(status_code=503, detail="Model artifacts are unavailable")
    assert MODEL_STORE.metadata is not None
    refit_status = (
        {
            "status": "UP",
            "modelVersion": REFIT_CONTROLLED_STORE.engine.model_version,
            "profileIds": list(REFIT_CONTROLLED_STORE.engine.profile_ids),
            "scope": "experimental_controlled_perturbation_benchmark",
        }
        if REFIT_CONTROLLED_STORE.ready
        else {
            "status": "DISABLED" if not REFIT_CONTROLLED_EXPERIMENTAL_ENABLED else "UNAVAILABLE",
            "detail": REFIT_CONTROLLED_STORE.error,
        }
    )
    return {
        "status": "UP",
        "modelVersion": MODEL_STORE.metadata["model_version"],
        "experimentalRefitControlled": refit_status,
        "kafkaWorkers": {
            "legacy": _worker_health(
                LEGACY_KAFKA_WORKER,
                os.getenv("KAFKA_ENABLED", "false").lower() == "true",
            ),
            "experimentalRefitControlled": _worker_health(
                REFIT_CONTROLLED_KAFKA_WORKER,
                REFIT_CONTROLLED_KAFKA_ENABLED and REFIT_CONTROLLED_STORE.ready,
            ),
        },
    }


def _worker_health(worker: Any | None, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "state": "disabled"}
    if worker is None:
        return {"enabled": True, "state": "starting"}
    status = worker.status
    return {
        "enabled": True,
        "state": "connected" if status["connected"] else "reconnecting",
        "connectionAttempts": status["connectionAttempts"],
        "lastConnectionError": status["lastConnectionError"],
    }


@app.post("/predict", response_model=PredictionOutput)
def predict(payload: TelemetryInput) -> PredictionOutput:
    if not MODEL_STORE.ready:
        raise HTTPException(status_code=503, detail="Model artifacts are unavailable")
    started = time.perf_counter()
    try:
        return predict_telemetry(payload)
    except Exception as exc:
        PREDICTION_FAILURES.inc()
        LOGGER.exception("Prediction failed for device %s", payload.device_id)
        raise HTTPException(status_code=500, detail="Prediction failed") from exc
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - started)


@app.post("/experimental/refit-controlled/predict")
def predict_refit_controlled(payload: RefitControlledTelemetryInput) -> dict[str, Any]:
    """Score an explicitly mapped REFIT replay stream after causal bin closure.

    This endpoint is deliberately separate from `/predict`. It returns
    uncalibrated anomaly scores and explicit warm-up/coverage state, never a
    probability. It does not publish an alert or Kafka event automatically.
    """
    if not REFIT_CONTROLLED_STORE.ready:
        raise HTTPException(
            status_code=503,
            detail="Experimental REFIT controlled model artifacts are unavailable",
        )
    assert REFIT_CONTROLLED_STORE.engine is not None
    started = time.perf_counter()
    try:
        result = REFIT_CONTROLLED_STORE.engine.ingest(
            profile_id=int(payload.refit_profile_id),
            stream_id=payload.stream_id,
            energy_kwh=payload.energy_consumed,
            timestamp=payload.timestamp,
            interval_seconds=payload.interval_seconds,
        )
        REFIT_CONTROLLED_EVENTS.labels(input_state=result.input_state).inc()
        for closed_bin in result.closed_bins:
            REFIT_CONTROLLED_CLOSED_BINS.labels(state=closed_bin.status).inc()
        return {
            "modelVersion": REFIT_CONTROLLED_STORE.engine.model_version,
            "modelScope": "experimental_controlled_perturbation_benchmark",
            "result": result.as_dict(),
        }
    except RefitControlledError as exc:
        PREDICTION_FAILURES.inc()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        PREDICTION_FAILURES.inc()
        LOGGER.exception("Experimental REFIT prediction failed for stream %s", payload.stream_id)
        raise HTTPException(status_code=500, detail="Experimental REFIT prediction failed") from exc
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - started)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
