"""Offline validation for the legacy supervised smart-meter baseline.

This script only reads the supplied CSV and historical evidence.  It writes
new validation records to the selected output directory and never alters the
repository dataset, source code, installed model, Docker state, or services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

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
LABEL_COLUMN = "Anomaly_Label"
EXPECTED_COLUMNS = ["Timestamp", *RAW_FEATURES, LABEL_COLUMN]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def row_fingerprints(frame: pd.DataFrame, columns: list[str]) -> set[str]:
    return {
        hashlib.sha256("\x1f".join(str(value) for value in row).encode("utf-8")).hexdigest()
        for row in frame.loc[:, columns].itertuples(index=False, name=None)
    }


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def historical_metrics(evidence_root: Path) -> dict[str, Any]:
    paths = {
        "provenance": evidence_root / "01_dataset" / "provenance.json",
        "training_config": evidence_root / "03_ml_training" / "training_config.json",
        "model_metadata": evidence_root / "03_ml_training" / "model_metadata.json",
        "model_comparison": evidence_root / "04_ml_evaluation" / "model_comparison.csv",
    }
    result: dict[str, Any] = {"available": {}, "values": {}, "limitations": []}
    for name, path in paths.items():
        result["available"][name] = path.is_file()
    for name in ("provenance", "training_config", "model_metadata"):
        path = paths[name]
        if path.is_file():
            result["values"][name] = json.loads(path.read_text(encoding="utf-8"))
    comparison_path = paths["model_comparison"]
    if comparison_path.is_file():
        result["values"]["model_comparison"] = pd.read_csv(comparison_path).to_dict(orient="records")
    if not all(result["available"].values()):
        result["limitations"].append("One or more historical baseline-evidence files are unavailable.")
    return result


def validate(dataset: Path, output: Path, historical_root: Path, reproduction_root: Path | None) -> None:
    raw = pd.read_csv(dataset)
    raw_timestamp = pd.to_datetime(raw.get("Timestamp"), format="%Y-%m-%d %H:%M:%S", errors="coerce")
    present_expected = [column for column in EXPECTED_COLUMNS if column in raw.columns]
    numeric = raw.reindex(columns=RAW_FEATURES).apply(pd.to_numeric, errors="coerce")
    invalid_timestamp = raw_timestamp.isna()
    invalid_numeric = numeric.isna().any(axis=1)
    invalid_energy = numeric["Electricity_Consumed"].lt(0)
    duplicate = raw.duplicated(subset=list(raw.columns), keep="first")
    valid = ~(invalid_timestamp | invalid_numeric | invalid_energy | duplicate)
    clean = raw.loc[valid].copy()
    clean.loc[:, RAW_FEATURES] = numeric.loc[clean.index, RAW_FEATURES]
    clean["_parsed_timestamp"] = raw_timestamp.loc[clean.index]
    clean = clean.sort_values("_parsed_timestamp", kind="stable").reset_index(drop=True)
    clean["target"] = clean[LABEL_COLUMN].astype(str).str.strip().str.lower().map({"normal": 0, "abnormal": 1})
    unsupported_labels = sorted(clean.loc[clean["target"].isna(), LABEL_COLUMN].astype(str).unique().tolist())
    if unsupported_labels:
        raise ValueError(f"Unsupported labels: {unsupported_labels}")
    clean["target"] = clean["target"].astype(int)
    clean["Hour"] = clean["_parsed_timestamp"].dt.hour
    clean["DayOfWeek"] = clean["_parsed_timestamp"].dt.dayofweek
    clean["ConsumptionDeviation"] = clean["Electricity_Consumed"] - clean["Avg_Past_Consumption"]

    total = len(clean)
    train_end = int(total * 0.70)
    validation_end = int(total * 0.85)
    split_frames = {
        "train": clean.iloc[:train_end].copy(),
        "validation": clean.iloc[train_end:validation_end].copy(),
        "test": clean.iloc[validation_end:].copy(),
    }
    split_summary: list[dict[str, Any]] = []
    for name, frame in split_frames.items():
        split_summary.append(
            {
                "split": name,
                "rows": int(len(frame)),
                "normal": int((frame["target"] == 0).sum()),
                "abnormal": int((frame["target"] == 1).sum()),
                "start": frame["_parsed_timestamp"].min().isoformat(),
                "end": frame["_parsed_timestamp"].max().isoformat(),
                "both_classes_present": bool(frame["target"].nunique() == 2),
            }
        )

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "check": "expected_schema",
            "status": "PASS" if list(raw.columns) == EXPECTED_COLUMNS else "FAIL",
            "observed_columns": list(raw.columns),
            "expected_columns": EXPECTED_COLUMNS,
        }
    )
    checks.extend(
        [
            {
                "check": "timestamp_parse",
                "status": "PASS" if int(invalid_timestamp.sum()) == 0 else "FAIL",
                "invalid_rows": int(invalid_timestamp.sum()),
            },
            {
                "check": "numeric_feature_parse",
                "status": "PASS" if int(invalid_numeric.sum()) == 0 else "FAIL",
                "invalid_rows": int(invalid_numeric.sum()),
            },
            {
                "check": "negative_energy",
                "status": "PASS" if int(invalid_energy.sum()) == 0 else "FAIL",
                "invalid_rows": int(invalid_energy.sum()),
            },
            {
                "check": "complete_duplicate_rows",
                "status": "PASS" if int(duplicate.sum()) == 0 else "FAIL",
                "duplicate_rows": int(duplicate.sum()),
            },
            {
                "check": "supported_binary_labels",
                "status": "PASS" if not unsupported_labels else "FAIL",
                "unsupported_labels": unsupported_labels,
            },
            {
                "check": "input_timestamp_monotonic",
                "status": "PASS" if raw_timestamp.is_monotonic_increasing else "WARN",
                "note": "The training code performs a stable chronological sort before splitting.",
            },
            {
                "check": "clean_timestamp_monotonic",
                "status": "PASS" if clean["_parsed_timestamp"].is_monotonic_increasing else "FAIL",
            },
        ]
    )

    timestamp_sets = {name: set(frame["_parsed_timestamp"].astype(str)) for name, frame in split_frames.items()}
    raw_row_sets = {name: row_fingerprints(frame, EXPECTED_COLUMNS) for name, frame in split_frames.items()}
    feature_row_sets = {name: row_fingerprints(frame, FEATURES) for name, frame in split_frames.items()}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        checks.extend(
            [
                {
                    "check": f"timestamp_overlap_{left}_{right}",
                    "status": "PASS" if not (timestamp_sets[left] & timestamp_sets[right]) else "FAIL",
                    "overlap_count": len(timestamp_sets[left] & timestamp_sets[right]),
                },
                {
                    "check": f"raw_row_fingerprint_overlap_{left}_{right}",
                    "status": "PASS" if not (raw_row_sets[left] & raw_row_sets[right]) else "FAIL",
                    "overlap_count": len(raw_row_sets[left] & raw_row_sets[right]),
                },
                {
                    "check": f"feature_row_fingerprint_overlap_{left}_{right}",
                    "status": "PASS" if not (feature_row_sets[left] & feature_row_sets[right]) else "WARN",
                    "overlap_count": len(feature_row_sets[left] & feature_row_sets[right]),
                    "note": "Identical feature vectors at distinct times are not necessarily leakage; this check is a guardrail.",
                },
            ]
        )

    split_endpoints = [(name, frame["_parsed_timestamp"].min(), frame["_parsed_timestamp"].max()) for name, frame in split_frames.items()]
    strict_order = split_endpoints[0][2] < split_endpoints[1][1] < split_endpoints[1][2] < split_endpoints[2][1]
    checks.append(
        {
            "check": "strict_chronological_split_order",
            "status": "PASS" if strict_order else "FAIL",
            "endpoints": [{"split": name, "start": start.isoformat(), "end": end.isoformat()} for name, start, end in split_endpoints],
        }
    )

    direct_target_features = []
    for feature in FEATURES:
        values = clean[feature].to_numpy()
        if np.array_equal(values, clean["target"].to_numpy()):
            direct_target_features.append(feature)
    checks.extend(
        [
            {
                "check": "target_column_excluded_from_feature_contract",
                "status": "PASS" if LABEL_COLUMN not in FEATURES and "target" not in FEATURES else "FAIL",
                "feature_contract": FEATURES,
            },
            {
                "check": "direct_target_feature_equality",
                "status": "PASS" if not direct_target_features else "FAIL",
                "matching_features": direct_target_features,
            },
            {
                "check": "derived_deviation_formula",
                "status": "PASS"
                if np.allclose(clean["ConsumptionDeviation"], clean["Electricity_Consumed"] - clean["Avg_Past_Consumption"])
                else "FAIL",
            },
            {
                "check": "dataset_provided_history_causal_provenance",
                "status": "UNRESOLVED",
                "feature": "Avg_Past_Consumption",
                "note": "The CSV does not document how this historical field was calculated. Row-level checks cannot prove it excludes future information.",
            },
            {
                "check": "label_generation_provenance",
                "status": "UNRESOLVED",
                "note": "Historical repository evidence explicitly states that source and label-generation provenance are unavailable.",
            },
        ]
    )

    historical = historical_metrics(historical_root)
    dataset_hash = sha256_file(dataset)
    provenance_hash = historical.get("values", {}).get("provenance", {}).get("sha256")
    checks.append(
        {
            "check": "historical_dataset_hash_match",
            "status": "PASS" if provenance_hash == dataset_hash else "WARN",
            "dataset_sha256": dataset_hash,
            "historical_sha256": provenance_hash,
        }
    )

    reproduction: dict[str, Any] = {"available": False, "comparison": None}
    if reproduction_root is not None:
        path = reproduction_root / "04_ml_evaluation" / "model_comparison.csv"
        if path.is_file():
            reproduction["available"] = True
            reproduced = pd.read_csv(path).sort_values("model").reset_index(drop=True)
            historical_rows = historical.get("values", {}).get("model_comparison", [])
            if historical_rows:
                historical_frame = pd.DataFrame(historical_rows).sort_values("model").reset_index(drop=True)
                same_columns = list(reproduced.columns) == list(historical_frame.columns)
                numeric_columns = [column for column in reproduced.columns if column != "model"]
                max_abs_error = {
                    column: float(np.max(np.abs(reproduced[column] - historical_frame[column])))
                    for column in numeric_columns
                } if same_columns and len(reproduced) == len(historical_frame) else {}
                reproduction["comparison"] = {
                    "same_model_order": bool(reproduced["model"].tolist() == historical_frame["model"].tolist()) if same_columns else False,
                    "same_columns": same_columns,
                    "same_rows": bool(len(reproduced) == len(historical_frame)),
                    "max_abs_error_by_metric": max_abs_error,
                    "exact_numeric_reproduction": bool(max_abs_error and all(value == 0.0 for value in max_abs_error.values())),
                }
            reproduction["metrics"] = reproduced.to_dict(orient="records")

    input_manifest = {
        "classification": "newly_generated_validation_metadata",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_copy": str(dataset),
        "size_bytes": dataset.stat().st_size,
        "sha256": dataset_hash,
        "raw_rows": int(len(raw)),
        "retained_rows": int(len(clean)),
        "timestamp_min": clean["_parsed_timestamp"].min().isoformat(),
        "timestamp_max": clean["_parsed_timestamp"].max().isoformat(),
    }
    environment = {
        "classification": "newly_generated_execution_environment",
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {name: package_version(name) for name in ["pandas", "numpy", "scikit-learn", "joblib", "matplotlib"]},
    }
    schema = {
        "classification": "newly_generated_schema_and_quality_validation",
        "raw_columns": list(raw.columns),
        "raw_dtypes": {column: str(dtype) for column, dtype in raw.dtypes.items()},
        "expected_columns": EXPECTED_COLUMNS,
        "row_counts": {"raw": int(len(raw)), "retained": int(len(clean))},
        "invalid_timestamp_rows": int(invalid_timestamp.sum()),
        "invalid_numeric_rows": int(invalid_numeric.sum()),
        "negative_energy_rows": int(invalid_energy.sum()),
        "duplicate_rows": int(duplicate.sum()),
        "label_counts": {str(key): int(value) for key, value in clean[LABEL_COLUMN].value_counts().to_dict().items()},
        "label_percentages": {str(key): float(value) for key, value in clean[LABEL_COLUMN].value_counts(normalize=True).mul(100).to_dict().items()},
    }
    split_result = {
        "classification": "newly_generated_split_and_leakage_validation",
        "split_rule": "stable chronological sort followed by 70% train, 15% validation, 15% test",
        "splits": split_summary,
        "checks": checks,
        "interpretation_boundary": [
            "PASS checks establish properties of the copied CSV and the static training contract, not external-data generalization.",
            "UNRESOLVED findings are not treated as passes.",
            "The baseline labels and their provenance are not independently verifiable from repository content.",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "input_manifest.json", input_manifest)
    write_json(output / "execution_environment.json", environment)
    write_json(output / "schema_validation.json", schema)
    write_json(output / "split_leakage_checks.json", split_result)
    write_json(output / "historical_evidence_snapshot.json", {"classification": "historical_evidence_read_only", **historical})
    write_json(output / "reproduction_comparison.json", {"classification": "newly_generated_reproduction_comparison", **reproduction})
    pd.DataFrame(
        [{"check": item["check"], "status": item["status"]} for item in checks]
    ).to_csv(output / "validation_check_status.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the supervised smart-meter baseline offline.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical-evidence-root", type=Path, required=True)
    parser.add_argument("--reproduction-evidence-root", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    validate(args.dataset, args.output, args.historical_evidence_root, args.reproduction_evidence_root)
