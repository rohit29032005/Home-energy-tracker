"""Offline, in-process latency benchmark for the reproduced ML artifact.

This benchmark intentionally does not create an HTTP server or contact any
project service. It measures only feature preparation and ``predict_proba``
against the newly reproduced Random Forest artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


RAW_FEATURES = [
    "Electricity_Consumed",
    "Temperature",
    "Humidity",
    "Wind_Speed",
    "Avg_Past_Consumption",
]
FEATURES = RAW_FEATURES + ["Hour", "DayOfWeek", "ConsumptionDeviation"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_held_out_rows(dataset: Path) -> pd.DataFrame:
    data = pd.read_csv(dataset)
    data["_timestamp"] = pd.to_datetime(data["Timestamp"], format="%Y-%m-%d %H:%M:%S", errors="raise")
    data = data.sort_values("_timestamp", kind="stable").reset_index(drop=True)
    data["Hour"] = data["_timestamp"].dt.hour
    data["DayOfWeek"] = data["_timestamp"].dt.dayofweek
    data["ConsumptionDeviation"] = data["Electricity_Consumed"] - data["Avg_Past_Consumption"]
    return data.iloc[int(len(data) * 0.85) :].loc[:, FEATURES].copy()


def percentile(values: list[float], level: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), level))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--max-rows", type=int, default=0, help="Optional evenly spaced held-out sample limit")
    parser.add_argument("--single-worker", action="store_true", help="Set the loaded forest's in-memory n_jobs to one")
    args = parser.parse_args()

    if args.repetitions < 1:
        raise ValueError("--repetitions must be positive")

    args.output.mkdir(parents=True, exist_ok=True)
    rows = prepare_held_out_rows(args.dataset)
    total_held_out_rows = len(rows)
    if args.max_rows:
        if args.max_rows < 1:
            raise ValueError("--max-rows must be positive when supplied")
        if args.max_rows < len(rows):
            row_positions = np.linspace(0, len(rows) - 1, args.max_rows, dtype=int)
            rows = rows.iloc[row_positions].copy()
    model = joblib.load(args.model)
    benchmark_worker_mode = "artifact_default"
    if args.single_worker:
        forest = model.named_steps.get("model")
        if forest is None or not hasattr(forest, "n_jobs"):
            raise ValueError("Loaded pipeline does not expose a configurable forest n_jobs value")
        forest.n_jobs = 1
        benchmark_worker_mode = "in_memory_single_worker"

    # Warm the model and any lazy runtime state before recording observations.
    for _ in range(3):
        model.predict_proba(rows.iloc[:1])

    observations: list[dict[str, float | int]] = []
    for repetition in range(args.repetitions):
        for row_index in range(len(rows)):
            sample = rows.iloc[row_index : row_index + 1]
            started = time.perf_counter_ns()
            model.predict_proba(sample)
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
            observations.append({"repetition": repetition + 1, "row_index": row_index, "latency_ms": elapsed_ms})

    batch_seconds: list[float] = []
    for _ in range(args.repetitions):
        started = time.perf_counter_ns()
        model.predict_proba(rows)
        batch_seconds.append((time.perf_counter_ns() - started) / 1_000_000_000)

    latency_ms = [float(observation["latency_ms"]) for observation in observations]
    summary = {
        "experiment_id": "publication_final_experiment_3_offline_ml_inference_latency",
        "classification": "newly_generated_offline_microbenchmark",
        "execution_boundary": [
            "No Docker command, HTTP request, application endpoint, Kafka action, database, volume, credential, or existing model artifact was used.",
            "The benchmark loaded only the newly reproduced model under experiments/publication_final.",
            "Values are in-process local inference measurements, not service or end-to-end HTTP latency."
        ],
        "input": {
            "dataset_sha256": sha256(args.dataset),
            "model_sha256": sha256(args.model),
            "total_held_out_rows": int(total_held_out_rows),
            "held_out_rows": int(len(rows)),
            "row_selection": "all chronological held-out rows" if len(rows) == total_held_out_rows else "evenly spaced chronological held-out sample",
            "features": FEATURES,
            "repetitions": args.repetitions,
            "sample_count": len(observations),
            "worker_mode": benchmark_worker_mode,
        },
        "latency_ms": {
            "mean": float(np.mean(latency_ms)),
            "median": percentile(latency_ms, 50),
            "p95": percentile(latency_ms, 95),
            "p99": percentile(latency_ms, 99),
            "min": float(np.min(latency_ms)),
            "max": float(np.max(latency_ms)),
        },
        "batch": {
            "runs": args.repetitions,
            "rows_per_run": int(len(rows)),
            "mean_seconds": float(np.mean(batch_seconds)),
            "median_seconds": percentile(batch_seconds, 50),
            "mean_rows_per_second": float(len(rows) / np.mean(batch_seconds)),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
        },
    }
    pd.DataFrame(observations).to_csv(args.output / "single_record_latencies.csv", index=False)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
