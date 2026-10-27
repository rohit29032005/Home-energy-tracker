"""Stratified bootstrap confidence intervals for the fixed held-out test set.

The saved Random Forest and its validation-selected threshold are loaded from
the isolated reproduction output. Bootstrap resampling estimates uncertainty of
test-set metrics only; it does not reselect a threshold or retrain a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


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


def metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float) -> dict[str, float]:
    predicted = (probability >= threshold).astype(int)
    return {
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "pr_auc": float(average_precision_score(y_true, probability)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.iterations < 100:
        raise ValueError("At least 100 bootstrap iterations are required")

    args.output.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    threshold = float(metadata["decision_threshold"])
    raw = pd.read_csv(args.dataset)
    raw["_timestamp"] = pd.to_datetime(raw["Timestamp"], format="%Y-%m-%d %H:%M:%S", errors="raise")
    raw = raw.sort_values("_timestamp", kind="stable").reset_index(drop=True)
    raw["target"] = raw["Anomaly_Label"].str.strip().str.lower().map({"normal": 0, "abnormal": 1}).astype(int)
    raw["Hour"] = raw["_timestamp"].dt.hour
    raw["DayOfWeek"] = raw["_timestamp"].dt.dayofweek
    raw["ConsumptionDeviation"] = raw["Electricity_Consumed"] - raw["Avg_Past_Consumption"]
    test = raw.iloc[int(len(raw) * 0.85) :].copy()

    model = joblib.load(args.model)
    forest = model.named_steps.get("model")
    if forest is not None and hasattr(forest, "n_jobs"):
        forest.n_jobs = 1
    y_true = test["target"].to_numpy()
    probability = model.predict_proba(test[FEATURES])[:, 1]
    point = metrics(y_true, probability, threshold)
    matrix = confusion_matrix(y_true, probability >= threshold).tolist()

    rng = np.random.default_rng(args.seed)
    normal = np.where(y_true == 0)[0]
    abnormal = np.where(y_true == 1)[0]
    draws = []
    for index in range(args.iterations):
        sampled = np.concatenate(
            [
                rng.choice(normal, size=len(normal), replace=True),
                rng.choice(abnormal, size=len(abnormal), replace=True),
            ]
        )
        sampled_metrics = metrics(y_true[sampled], probability[sampled], threshold)
        draws.append({"iteration": index + 1, **sampled_metrics})
    draw_frame = pd.DataFrame(draws)
    draw_frame.to_csv(args.output / "bootstrap_draws.csv", index=False)
    confidence_intervals = {
        metric: {
            "point_estimate": point[metric],
            "ci_95_lower": float(np.percentile(draw_frame[metric], 2.5)),
            "ci_95_upper": float(np.percentile(draw_frame[metric], 97.5)),
        }
        for metric in point
    }
    result = {
        "experiment_id": "publication_final_experiment_1_stratified_bootstrap_test_ci",
        "classification": "newly_generated_offline_statistical_analysis",
        "execution_boundary": [
            "No Docker command, HTTP request, Kafka action, database, volume, credential, or existing model artifact was used.",
            "The model and threshold came from the isolated reproduced artifact; the forest was set to one in-memory worker for prediction only.",
            "The test interval was not used to select the threshold or retrain the model."
        ],
        "input": {
            "dataset_sha256": sha256(args.dataset),
            "model_sha256": sha256(args.model),
            "model_version": metadata["model_version"],
            "threshold": threshold,
            "test_rows": int(len(test)),
            "test_normal": int((y_true == 0).sum()),
            "test_abnormal": int((y_true == 1).sum()),
            "bootstrap_iterations": args.iterations,
            "bootstrap_seed": args.seed,
            "resampling": "stratified within observed normal and abnormal held-out test classes",
        },
        "confusion_matrix": {
            "labels": ["Normal", "Abnormal"],
            "rows_actual_columns_predicted": matrix,
        },
        "metrics_with_95_ci": confidence_intervals,
        "interpretation": [
            "Intervals describe sampling uncertainty conditional on the supplied held-out CSV, fixed feature pipeline, fixed threshold, and fixed model artifact.",
            "They do not resolve undocumented data provenance, label provenance, causal availability of Avg_Past_Consumption, or real-household generalization."
        ],
    }
    (args.output / "bootstrap_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
