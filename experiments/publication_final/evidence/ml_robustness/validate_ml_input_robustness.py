"""Offline robustness checks for the reproduced legacy ML artifact.

No ASGI server, Kafka worker, HTTP request, Docker resource, or existing model
artifact is started or changed. The script loads the copied model once and
exercises the same Pydantic payload and in-process feature-preparation path
used by the service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd
from pydantic import ValidationError


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--ml-service-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Configure an isolated local import before app.main evaluates its globals.
    os.environ["MODEL_DIR"] = str(args.model_dir.resolve())
    os.environ["KAFKA_ENABLED"] = "false"
    os.environ["REFIT_CONTROLLED_EXPERIMENTAL_ENABLED"] = "false"
    os.environ["REFIT_CONTROLLED_KAFKA_ENABLED"] = "false"
    os.environ["ML_MODEL_N_JOBS"] = "1"
    sys.path.insert(0, str(args.ml_service_root.resolve()))

    from app.main import MODEL_STORE, TelemetryInput, predict_telemetry  # noqa: PLC0415

    args.output.mkdir(parents=True, exist_ok=True)
    MODEL_STORE.load()

    training = pd.read_csv(args.dataset)
    training_range = {
        feature: {
            "min": float(training[feature].min()),
            "max": float(training[feature].max()),
        }
        for feature in [
            "Electricity_Consumed",
            "Temperature",
            "Humidity",
            "Wind_Speed",
            "Avg_Past_Consumption",
        ]
    }

    # Exact documented Wokwi mode boundaries; inputs intentionally omit the
    # four optional contextual fields, as the simulator's telemetry contract does.
    wokwi_cases = [
        ("eco_min", 1.0),
        ("eco_max", 6.0),
        ("heavy_min", 8.0),
        ("heavy_max", 20.0),
        ("alert_min", 26.0),
        ("alert_max", 40.0),
    ]
    predictions = []
    for name, energy_kwh in wokwi_cases:
        payload = TelemetryInput.model_validate(
            {
                "deviceId": 1,
                "energyConsumed": energy_kwh,
                "timestamp": "2026-10-15T00:00:00Z",
            }
        )
        output = predict_telemetry(payload)
        predictions.append(
            {
                "case": name,
                "energyConsumed": energy_kwh,
                "outside_training_electricity_range": not (
                    training_range["Electricity_Consumed"]["min"]
                    <= energy_kwh
                    <= training_range["Electricity_Consumed"]["max"]
                ),
                "anomaly": output.anomaly,
                "anomalyProbability": output.anomaly_probability,
                "imputedFeatures": output.imputed_features,
            }
        )

    validation_cases = {
        "zero_energy_accepted": {
            "payload": {"deviceId": 1, "energyConsumed": 0, "timestamp": "2026-10-15T00:00:00Z"},
            "expected": "accept",
        },
        "negative_energy_rejected": {
            "payload": {"deviceId": 1, "energyConsumed": -0.01, "timestamp": "2026-10-15T00:00:00Z"},
            "expected": "reject",
        },
        "missing_device_rejected": {
            "payload": {"energyConsumed": 0.2, "timestamp": "2026-10-15T00:00:00Z"},
            "expected": "reject",
        },
        "unexpected_field_rejected": {
            "payload": {"deviceId": 1, "energyConsumed": 0.2, "timestamp": "2026-10-15T00:00:00Z", "extra": 1},
            "expected": "reject",
        },
        "naive_timestamp_normalized_utc": {
            "payload": {"deviceId": 1, "energyConsumed": 0.2, "timestamp": "2026-10-15T00:00:00"},
            "expected": "accept",
        },
    }
    validation_results = []
    for name, case in validation_cases.items():
        try:
            parsed = TelemetryInput.model_validate(case["payload"])
            observed = "accept"
            details = {"timestamp": parsed.timestamp.isoformat()}
        except ValidationError as exc:
            observed = "reject"
            details = {"validation_error_count": len(exc.errors())}
        validation_results.append(
            {
                "case": name,
                "expected": case["expected"],
                "observed": observed,
                "passed": observed == case["expected"],
                **details,
            }
        )

    result = {
        "experiment_id": "publication_final_experiment_1_ml_input_robustness",
        "classification": "newly_generated_offline_input_and_distribution_check",
        "execution_boundary": [
            "No ASGI server, HTTP request, Kafka worker, Docker command, database, volume, credential, or existing model artifact was used.",
            "The in-process store loaded the newly reproduced artifact and disabled Kafka and REFIT experimental branches by environment variables before import.",
            "Synthetic Wokwi-mode values are controlled interface inputs, not real household observations."
        ],
        "input": {
            "dataset_sha256": sha256(args.dataset),
            "model_directory": str(args.model_dir),
            "model_version": MODEL_STORE.metadata["model_version"],
            "decision_threshold": MODEL_STORE.metadata["decision_threshold"],
        },
        "training_feature_ranges": training_range,
        "wokwi_documented_energy_ranges_kwh": {
            "eco": [1.0, 6.0],
            "heavy": [8.0, 20.0],
            "alert_test": [26.0, 40.0],
        },
        "wokwi_controlled_predictions": predictions,
        "input_validation": validation_results,
        "interpretation": [
            "The range comparison establishes an interface-scale mismatch for energyConsumed only; it does not prove field-model behavior.",
            "The outputs are not model-accuracy measurements because the Wokwi values have no ground-truth anomaly labels.",
            "Missing contextual values are reported by the code path as imputed, rather than silently treated as observed measurements."
        ],
    }
    (args.output / "robustness_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(predictions).to_csv(args.output / "wokwi_controlled_predictions.csv", index=False)
    pd.DataFrame(validation_results).to_csv(args.output / "input_validation_results.csv", index=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
