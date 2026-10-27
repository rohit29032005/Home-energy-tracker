"""Reproducible, leakage-safe supervised anomaly-model training pipeline.

The root CSV is intentionally used only for empirical ML training/evaluation.
Wokwi remains a controlled integration input and is not mixed into this data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LOGGER = logging.getLogger("ml_training")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RAW_FEATURES = [
    "Electricity_Consumed",
    "Temperature",
    "Humidity",
    "Wind_Speed",
    "Avg_Past_Consumption",
]
FEATURES = RAW_FEATURES + ["Hour", "DayOfWeek", "ConsumptionDeviation"]
LABEL_COLUMN = "Anomaly_Label"
RANDOM_SEED = 42


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def frame_to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in frame.iterrows():
        output.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(output)


def dataset_hash(dataset: Path) -> str:
    return hashlib.sha256(dataset.read_bytes()).hexdigest()


def audit_and_clean(dataset: Path, evidence_root: Path) -> pd.DataFrame:
    raw = pd.read_csv(dataset)
    original_rows = len(raw)
    raw["_parsed_timestamp"] = pd.to_datetime(raw["Timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    numeric = raw[RAW_FEATURES].apply(pd.to_numeric, errors="coerce")
    invalid_timestamp = raw["_parsed_timestamp"].isna()
    invalid_numeric = numeric.isna().any(axis=1)
    invalid_energy = numeric["Electricity_Consumed"].lt(0)
    invalid_rows = invalid_timestamp | invalid_numeric | invalid_energy
    duplicate_rows = raw.duplicated(subset=[column for column in raw.columns if column != "_parsed_timestamp"], keep="first")
    clean = raw.loc[~invalid_rows & ~duplicate_rows].copy()
    clean.loc[:, RAW_FEATURES] = numeric.loc[clean.index, RAW_FEATURES]
    clean = clean.sort_values("_parsed_timestamp", kind="stable").reset_index(drop=True)
    clean["target"] = clean[LABEL_COLUMN].str.strip().str.lower().map({"normal": 0, "abnormal": 1})
    if clean["target"].isna().any():
        values = sorted(clean.loc[clean["target"].isna(), LABEL_COLUMN].astype(str).unique())
        raise ValueError(f"Unsupported anomaly labels: {values}")
    clean["target"] = clean["target"].astype(int)

    intervals = clean["_parsed_timestamp"].diff().dt.total_seconds().div(60).dropna()
    class_counts = clean[LABEL_COLUMN].value_counts().rename_axis("label").reset_index(name="count")
    class_counts["percentage"] = class_counts["count"].div(len(clean)).mul(100).round(4)
    statistics = clean[RAW_FEATURES].describe().transpose().reset_index(names="feature")
    missing = raw.isna().sum().rename_axis("column").reset_index(name="missing_values")
    schema = pd.DataFrame({"column": raw.columns, "dtype": [str(dtype) for dtype in raw.dtypes]})

    dataset_dir = evidence_root / "01_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    class_counts.to_csv(dataset_dir / "class_distribution.csv", index=False)
    statistics.to_csv(dataset_dir / "dataset_statistics.csv", index=False)
    missing.to_csv(dataset_dir / "missing_values.csv", index=False)
    schema.to_csv(dataset_dir / "schema.csv", index=False)
    (dataset_dir / "schema.txt").write_text("\n".join(f"{row.column}: {row.dtype}" for row in schema.itertuples()) + "\n", encoding="utf-8")

    provenance = {
        "filename": dataset.name,
        "size_bytes": dataset.stat().st_size,
        "sha256": dataset_hash(dataset),
        "source": "Not available in repository metadata; source and license cannot be verified from the file alone.",
        "dataset_version_or_date": "Not available in repository metadata.",
    }
    write_json(dataset_dir / "provenance.json", provenance)
    audit = f"""# Dataset audit

## Identity and provenance

- Filename: `{dataset.name}`
- Size: {dataset.stat().st_size} bytes
- SHA-256: `{provenance['sha256']}`
- Source/license/version: not available in the CSV or repository metadata; no provenance claim is made.

## Structure

- Raw data rows: {original_rows}
- Retained rows after valid-row and duplicate checks: {len(clean)}
- Columns: {len(raw.columns) - 1}
- Timestamp range: {clean['_parsed_timestamp'].min()} to {clean['_parsed_timestamp'].max()}
- Sampling interval: median {intervals.median():.1f} minutes; unique observed intervals: {sorted(intervals.unique().tolist())}
- Duplicate rows: {int(duplicate_rows.sum())}
- Invalid timestamp rows: {int(invalid_timestamp.sum())}
- Invalid numeric rows: {int(invalid_numeric.sum())}
- Negative electricity rows: {int(invalid_energy.sum())}
- Entity identifier columns: none are present; the dataset is a single unlabeled entity stream.

## Labels

The label column is `{LABEL_COLUMN}` with values `Normal` and `Abnormal`; it is binary after encoding `Normal=0`, `Abnormal=1`.

{frame_to_markdown(class_counts)}

## Suitability

The dataset has a timestamp, numeric consumption/environmental attributes, and a binary anomaly label. It is suitable for supervised anomaly classification with a chronological split. No claim is made about the original label-generation process because that provenance is not present in the repository.
"""
    (dataset_dir / "dataset_audit.md").write_text(audit, encoding="utf-8")
    return clean


def engineer_features(clean: pd.DataFrame, evidence_root: Path) -> pd.DataFrame:
    features = clean.copy()
    features["Hour"] = features["_parsed_timestamp"].dt.hour
    features["DayOfWeek"] = features["_parsed_timestamp"].dt.dayofweek
    # This uses only the current measurement and the dataset-provided historical value.
    features["ConsumptionDeviation"] = features["Electricity_Consumed"] - features["Avg_Past_Consumption"]
    preprocessing_dir = evidence_root / "02_preprocessing"
    preprocessing_dir.mkdir(parents=True, exist_ok=True)
    (preprocessing_dir / "feature_list.txt").write_text("\n".join(FEATURES) + "\n", encoding="utf-8")
    (preprocessing_dir / "preprocessing_report.md").write_text(
        """# Preprocessing report

1. Parsed `Timestamp` using the observed `%Y-%m-%d %H:%M:%S` format.
2. Checked numeric conversion, missing values, negative electricity values, and complete duplicate rows.
3. Removed only invalid or duplicate rows found by the audit.
4. Sorted records chronologically with a stable sort.
5. Encoded `Normal` as 0 and `Abnormal` as 1.
6. Derived `Hour` and `DayOfWeek` from the same row timestamp.
7. Derived `ConsumptionDeviation = Electricity_Consumed - Avg_Past_Consumption` from fields available on the same row.

The pipeline does not calculate lags or rolling windows. It never uses a later timestamp to construct a feature for an earlier timestamp. `Avg_Past_Consumption` is retained as a dataset-provided historical field; its source construction cannot be independently verified from the repository.
""",
        encoding="utf-8",
    )
    return features


def chronological_split(features: pd.DataFrame, evidence_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total = len(features)
    train_end = int(total * 0.70)
    validation_end = int(total * 0.85)
    train = features.iloc[:train_end].copy()
    validation = features.iloc[train_end:validation_end].copy()
    test = features.iloc[validation_end:].copy()
    rows = []
    for name, split in (("train", train), ("validation", validation), ("test", test)):
        counts = split["target"].value_counts().to_dict()
        if len(counts) != 2:
            raise ValueError(f"{name} split does not contain both classes: {counts}")
        rows.append({
            "split": name,
            "rows": len(split),
            "normal": int(counts.get(0, 0)),
            "abnormal": int(counts.get(1, 0)),
            "start": split["_parsed_timestamp"].min().isoformat(),
            "end": split["_parsed_timestamp"].max().isoformat(),
        })
    split_frame = pd.DataFrame(rows)
    split_frame.to_csv(evidence_root / "02_preprocessing" / "chronological_split.csv", index=False)
    return train, validation, test


def select_threshold(y_true: pd.Series, probabilities: np.ndarray) -> tuple[float, float]:
    candidates = np.arange(0.05, 0.96, 0.01)
    scored = [(float(threshold), f1_score(y_true, probabilities >= threshold, zero_division=0)) for threshold in candidates]
    # Highest F1; then prefer a larger threshold to reduce equal-score false positives.
    return max(scored, key=lambda result: (result[1], result[0]))


def evaluate(name: str, pipeline: Pipeline, train: pd.DataFrame, validation: pd.DataFrame, test: pd.DataFrame, evidence_root: Path) -> dict[str, Any]:
    pipeline.fit(train[FEATURES], train["target"])
    validation_probability = pipeline.predict_proba(validation[FEATURES])[:, 1]
    threshold, validation_f1 = select_threshold(validation["target"], validation_probability)
    test_probability = pipeline.predict_proba(test[FEATURES])[:, 1]
    test_prediction = (test_probability >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(test["target"], test_prediction, average="binary", zero_division=0)
    metrics = {
        "model": name,
        "decision_threshold": threshold,
        "validation_f1": validation_f1,
        "test_precision": float(precision),
        "test_recall": float(recall),
        "test_f1": float(f1),
        "test_roc_auc": float(roc_auc_score(test["target"], test_probability)),
        "test_pr_auc": float(average_precision_score(test["target"], test_probability)),
    }
    evaluation_dir = evidence_root / "04_ml_evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    report = classification_report(test["target"], test_prediction, target_names=["Normal", "Abnormal"], zero_division=0)
    (evaluation_dir / f"classification_report_{name}.txt").write_text(report, encoding="utf-8")
    write_json(evaluation_dir / f"metrics_{name}.json", metrics)

    cm = confusion_matrix(test["target"], test_prediction)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(cm, display_labels=["Normal", "Abnormal"]).plot(ax=ax, colorbar=False)
    ax.set_title(f"{name} test confusion matrix")
    fig.tight_layout()
    fig.savefig(evaluation_dir / f"confusion_matrix_{name}.png", dpi=180)
    plt.close(fig)

    fpr, tpr, _ = roc_curve(test["target"], test_probability)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"ROC-AUC={metrics['test_roc_auc']:.4f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title=f"{name} ROC curve")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(evaluation_dir / f"roc_curve_{name}.png", dpi=180)
    plt.close(fig)

    pr_precision, pr_recall, _ = precision_recall_curve(test["target"], test_probability)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(pr_recall, pr_precision, label=f"PR-AUC={metrics['test_pr_auc']:.4f}")
    ax.set(xlabel="Recall", ylabel="Precision", title=f"{name} precision-recall curve")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(evaluation_dir / f"precision_recall_curve_{name}.png", dpi=180)
    plt.close(fig)
    return {"metrics": metrics, "pipeline": pipeline}


def train_models(features: pd.DataFrame, model_dir: Path, evidence_root: Path) -> None:
    train, validation, test = chronological_split(features, evidence_root)
    models: dict[str, tuple[Pipeline, dict[str, Any]]] = {
        "logistic_regression": (
            Pipeline([
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)),
            ]),
            {"class_weight": "balanced", "max_iter": 1000, "random_state": RANDOM_SEED},
        ),
        "random_forest": (
            Pipeline([
                ("model", RandomForestClassifier(
                    n_estimators=300,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=RANDOM_SEED,
                    n_jobs=-1,
                )),
            ]),
            {"n_estimators": 300, "min_samples_leaf": 2, "class_weight": "balanced_subsample", "random_state": RANDOM_SEED},
        ),
    }
    evaluated: dict[str, dict[str, Any]] = {}
    for name, (pipeline, _) in models.items():
        LOGGER.info("Training %s", name)
        evaluated[name] = evaluate(name, pipeline, train, validation, test, evidence_root)

    selected_name = max(
        evaluated,
        key=lambda name: (
            evaluated[name]["metrics"]["validation_f1"],
            evaluated[name]["metrics"]["test_pr_auc"],
        ),
    )
    selected = evaluated[selected_name]
    comparison = pd.DataFrame([result["metrics"] for result in evaluated.values()]).sort_values("validation_f1", ascending=False)
    evaluation_dir = evidence_root / "04_ml_evaluation"
    comparison.to_csv(evaluation_dir / "model_comparison.csv", index=False)
    (evaluation_dir / "evaluation_summary.md").write_text(
        "# ML evaluation summary\n\n"
        "Models were selected by validation F1 after tuning their decision threshold on the validation interval. "
        "The test interval was not used for threshold selection. The selected model is "
        f"`{selected_name}`.\n\n{frame_to_markdown(comparison.round(6))}\n",
        encoding="utf-8",
    )

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected["pipeline"], model_dir / "anomaly_model.joblib")
    metadata = {
        "model_version": f"{selected_name}-csv-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "selected_model": selected_name,
        "features": FEATURES,
        "feature_defaults": {feature: float(train[feature].median()) for feature in RAW_FEATURES},
        "decision_threshold": selected["metrics"]["decision_threshold"],
        "selection_criterion": "validation F1; test metrics are reported but not used as the primary selection criterion",
        "split_strategy": "chronological 70% train, 15% validation, 15% held-out test",
        "random_seed": RANDOM_SEED,
        "training_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "test_metrics": selected["metrics"],
        "model_parameters": models[selected_name][1],
    }
    write_json(model_dir / "model_metadata.json", metadata)
    training_dir = evidence_root / "03_ml_training"
    training_dir.mkdir(parents=True, exist_ok=True)
    write_json(training_dir / "training_config.json", {
        "features": FEATURES,
        "split_strategy": metadata["split_strategy"],
        "class_imbalance_handling": "class weights applied during training; no resampling was used",
        "random_seed": RANDOM_SEED,
        "candidate_models": {name: params for name, (_, params) in models.items()},
    })
    write_json(training_dir / "model_metadata.json", metadata)
    (training_dir / "feature_list.txt").write_text("\n".join(FEATURES) + "\n", encoding="utf-8")
    (training_dir / "training_log.txt").write_text(
        f"Selected model: {selected_name}\n"
        f"Selection criterion: validation F1\n"
        f"Validation F1: {selected['metrics']['validation_f1']:.6f}\n"
        f"Decision threshold: {selected['metrics']['decision_threshold']:.2f}\n"
        "Class imbalance handling: class weights only; no resampling.\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Train Home Energy Tracker anomaly models")
    parser.add_argument("--dataset", type=Path, default=root / "smart_meter_data.csv")
    parser.add_argument("--model-dir", type=Path, default=root / "ml-service" / "models")
    parser.add_argument("--evidence-root", type=Path, default=root / "evidence")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean = audit_and_clean(args.dataset, args.evidence_root)
    features = engineer_features(clean, args.evidence_root)
    train_models(features, args.model_dir, args.evidence_root)
    LOGGER.info("Training completed successfully")


if __name__ == "__main__":
    main()
