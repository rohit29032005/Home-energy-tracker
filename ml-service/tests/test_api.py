from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import TelemetryInput, app


def test_telemetry_accepts_existing_wokwi_contract() -> None:
    payload = TelemetryInput.model_validate({
        "deviceId": 1,
        "energyConsumed": 0.5,
        "timestamp": "2024-01-01T00:00:00Z",
    })
    assert payload.device_id == 1
    assert payload.energy_consumed == 0.5
    assert payload.timestamp == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_telemetry_rejects_negative_energy() -> None:
    try:
        TelemetryInput.model_validate({
            "deviceId": 1,
            "energyConsumed": -0.1,
            "timestamp": "2024-01-01T00:00:00Z",
        })
    except ValueError:
        return
    raise AssertionError("Negative energy must be rejected")


def test_health_and_prediction_use_trained_artifacts() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        result = client.post("/predict", json={
            "deviceId": 7,
            "energyConsumed": 0.55,
            "timestamp": "2024-04-14T03:30:00Z",
            "temperature": 0.50,
            "humidity": 0.45,
            "windSpeed": 0.40,
            "avgPastConsumption": 0.50,
        })
    assert result.status_code == 200
    body = result.json()
    assert body["modelVersion"].startswith("random_forest-csv-")
    assert 0.0 <= body["anomalyProbability"] <= 1.0
    assert body["imputedFeatures"] == []


def test_refit_experimental_route_requires_explicit_profile_and_returns_scores_not_probability() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        response = client.post("/experimental/refit-controlled/predict", json={
            "refitProfileId": 1,
            "streamId": "test-explicit-refit-stream",
            "energyConsumed": 0.0003,
            "timestamp": "2026-01-01T00:00:08Z",
            "intervalSeconds": 8,
        })
        implicit_mapping_attempt = client.post("/experimental/refit-controlled/predict", json={
            "deviceId": 1,
            "streamId": "test-explicit-refit-stream",
            "energyConsumed": 0.0003,
            "timestamp": "2026-01-01T00:00:16Z",
            "intervalSeconds": 8,
        })

    assert health.status_code == 200
    assert health.json()["experimentalRefitControlled"]["status"] == "UP"
    assert health.json()["kafkaWorkers"]["legacy"] == {"enabled": False, "state": "disabled"}
    assert response.status_code == 200
    body = response.json()
    assert body["modelScope"] == "experimental_controlled_perturbation_benchmark"
    assert body["result"]["refitProfileId"] == 1
    assert body["result"]["streamId"] == "test-explicit-refit-stream"
    assert "anomalyProbability" not in body
    assert implicit_mapping_attempt.status_code == 422
