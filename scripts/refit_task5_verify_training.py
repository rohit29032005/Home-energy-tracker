#!/usr/bin/env python3
"""Read-only verifier for the Task 5 REFIT controlled-perturbation artifacts.

The verifier intentionally checks artifact provenance, leakage boundaries, and
structural reconciliation only.  It does not recompute, select, or interpret
any model-performance result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any


ARTIFACT_SCHEMA = "refit_controlled_v1"
EXPECTED_HOUSEHOLD_KEYS = frozenset({"1", "2", "3", "4", "11"})
EXPECTED_PRIMARY_HOUSEHOLDS = frozenset({"1", "2", "4"})
EXPECTED_SENSITIVITY_HOUSEHOLDS = frozenset({"3", "11"})
EXPECTED_DETECTORS = frozenset({"isolation_forest", "robust_residual"})
PRIMARY_COHORT = "primary_no_documented_solar_interference"
SENSITIVITY_COHORT = "sensitivity_documented_solar_interference"
EXPECTED_COHORT_SCOPES = frozenset({"primary", "sensitivity_documented_solar_interference"})
CONTROLLED_RESULT_BOUNDARY = "controlled synthetic perturbation detection only"

MODEL_REQUIRED_FILES = frozenset(
    {
        "model_metadata.json",
        "isolation_forest_by_household.joblib",
    }
)
EVIDENCE_REQUIRED_FILES = frozenset(
    {
        "bin_quality_report.csv",
        "validation_thresholds.csv",
        "per_household_metrics.csv",
        "cohort_metrics.csv",
        "per_scenario_metrics.csv",
        "event_level_metrics.csv",
        "model_comparison.csv",
        "dataset_contract.md",
        "feature_specification.md",
        "controlled_primary_confusion_matrix_isolation_forest.png",
        "controlled_primary_precision_recall.png",
        "controlled_primary_score_distribution.png",
        "evaluation_summary.md",
        "training_config.json",
        "model_manifest.json",
    }
)
RUN_REQUIRED_FILES = frozenset(
    {
        "binned_records.csv",
        "test_predictions.csv",
        "all_scored_bins.csv",
    }
)

# A model may use replay-compatible measurements and causal time features, but
# never labels, split/cohort metadata, quality markers, source identifiers, or
# other source-only shortcuts.  ``id`` is deliberately a whole-token check so
# innocuous feature names are not rejected just because they contain those two
# letters as part of another word.
FORBIDDEN_FEATURE_FRAGMENTS = (
    "label",
    "anomal",
    "positive",
    "negative",
    "target",
    "ground_truth",
    "truth",
    "class",
    "split",
    "cohort",
    "train",
    "validation",
    "test",
    "fold",
    "quality",
    "issue",
    "flag",
    "source",
    "original",
    "unmodified",
    "raw_aggregate",
    "aggregate_power",
    "iqr",
    "solar",
    "replayable",
    "household",
    "refit",
    "event",
    "episode",
)
FORBIDDEN_FEATURE_TOKENS = frozenset({"id", "identifier", "row", "record"})


class VerificationFailure(ValueError):
    """A failed integrity or semantic-boundary check."""


@dataclass(frozen=True)
class VerificationSummary:
    event_count: int
    feature_count: int


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Verify existing Task 5 REFIT controlled-perturbation artifacts without writing files."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_dataset.csv",
        help="Current final Task 4 anomaly dataset.",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_generation_manifest.json",
        help="Current final Task 4 generation manifest.",
    )
    parser.add_argument(
        "--injection-log",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_injection_log.csv",
        help="Current final Task 4 controlled-perturbation log.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=root / "ml-service" / "models" / "refit-controlled-v1",
        help="Task 5 model-artifact directory.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=root / "evidence" / "18_refit_controlled_ml",
        help="Task 5 evidence-artifact directory.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=root / "data" / "refit" / "ml_runs" / "refit_controlled_v1",
        help="Task 5 scored-run directory.",
    )
    parser.add_argument(
        "--expected-event-count",
        type=int,
        default=40,
        help="Expected controlled Task 4 episode count for this registered v1 run (default: 40).",
    )
    parser.add_argument(
        "--validation-score-quantile",
        type=float,
        default=0.99,
        help="Pre-registered normal-validation quantile for this run (default: 0.99).",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_files(root: Path, names: Sequence[str], scope: str) -> None:
    missing = sorted(name for name in names if not (root / name).is_file())
    if missing:
        raise VerificationFailure(f"Missing required {scope} artifact(s): {', '.join(missing)}")


def load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationFailure(f"Cannot read {description} JSON at {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise VerificationFailure(f"{description} must contain a JSON object: {path}")
    return loaded


def require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationFailure(f"{context} must be an object")
    return value


def require_list_of_strings(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise VerificationFailure(f"{context} must be a non-empty list of non-empty strings")
    return value


def require_csv(path: Path, required_fields: set[str], description: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(required_fields - fieldnames)
            if missing:
                raise VerificationFailure(
                    f"{description} is missing required column(s): {', '.join(missing)}"
                )
            rows = list(reader)
    except OSError as exc:
        raise VerificationFailure(f"Cannot read {description} at {path}: {exc}") from exc
    if not rows:
        raise VerificationFailure(f"{description} has no data rows")
    return rows


def parse_float(value: Any, context: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise VerificationFailure(f"{context} is not numeric: {value!r}") from exc
    if not math.isfinite(numeric):
        raise VerificationFailure(f"{context} is not finite: {value!r}")
    return numeric


def parse_nonnegative_int(value: Any, context: str) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise VerificationFailure(f"{context} is not an integer: {value!r}") from exc
    if parsed < 0 or str(parsed) != str(value).strip():
        raise VerificationFailure(f"{context} is not a non-negative canonical integer: {value!r}")
    return parsed


def household_key(value: Any, context: str) -> str:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise VerificationFailure(f"{context} is not a household ID: {value!r}") from exc
    if parsed <= 0:
        raise VerificationFailure(f"{context} is not a positive household ID: {value!r}")
    return str(parsed)


def ensure_exact_keys(actual: set[str], expected: frozenset[str], context: str) -> None:
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise VerificationFailure(f"{context} household keys do not reconcile ({'; '.join(details)})")


def validate_input_hashes(
    metadata: Mapping[str, Any],
    dataset: Path,
    dataset_manifest: Path,
    injection_log: Path,
    context: str,
) -> None:
    declared = require_mapping(metadata.get("input_files", metadata.get("input_sha256")), f"{context}.input files")
    actual_paths = {
        "anomaly_dataset": dataset,
        "task4_manifest": dataset_manifest,
        "injection_log": injection_log,
    }
    if set(declared) != set(actual_paths):
        raise VerificationFailure(
            f"{context} must declare exactly the Task 4 input hashes {sorted(actual_paths)}; "
            f"got {sorted(str(key) for key in declared)}"
        )
    for name, path in actual_paths.items():
        record = require_mapping(declared[name], f"{context}.{name}")
        expected_hash = record.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise VerificationFailure(f"{context}.{name} lacks a valid SHA-256")
        actual_hash = sha256_file(path)
        if expected_hash.lower() != actual_hash:
            raise VerificationFailure(
                f"{context}.{name} SHA-256 does not match the current final Task 4 file "
                f"({expected_hash} != {actual_hash})"
            )


def feature_has_forbidden_shortcut(name: str) -> bool:
    normalized = name.lower().replace("-", "_").replace(" ", "_")
    if any(fragment in normalized for fragment in FORBIDDEN_FEATURE_FRAGMENTS):
        return True
    tokens = {token for token in normalized.split("_") if token}
    return bool(tokens & FORBIDDEN_FEATURE_TOKENS)


def validate_feature_names(features: list[str]) -> None:
    if len(features) != len(set(features)):
        raise VerificationFailure("Model feature names contain duplicates")
    forbidden = sorted(name for name in features if feature_has_forbidden_shortcut(name))
    if forbidden:
        raise VerificationFailure(
            "Model feature contract contains label/split/quality/source shortcut name(s): "
            + ", ".join(forbidden)
        )


def validate_semantic_boundary(metadata: Mapping[str, Any], run_manifest: Mapping[str, Any]) -> None:
    boundary = require_mapping(metadata.get("semantic_boundary"), "model metadata semantic_boundary")
    expected_flags = {
        "not_real_world_fault_accuracy": True,
        "official_refit_anomaly_labels_used": False,
        "test_labels_used_for_fit_or_threshold": False,
        "legacy_service_artifact_replaced": False,
    }
    for name, expected in expected_flags.items():
        if boundary.get(name) is not expected:
            raise VerificationFailure(
                f"Semantic boundary flag {name!r} must be {expected!r}; got {boundary.get(name)!r}"
            )
    if boundary.get("evaluation_name") != "controlled_perturbation_detection":
        raise VerificationFailure("Semantic boundary does not identify controlled-perturbation detection")
    if run_manifest.get("result_boundary") != CONTROLLED_RESULT_BOUNDARY:
        raise VerificationFailure("Run manifest does not state the controlled-only result boundary")


def relative_artifact_path(root: Path, filename: Any, scope: str) -> Path:
    if not isinstance(filename, str) or not filename or PurePath(filename).name != filename:
        raise VerificationFailure(f"{scope} manifest contains an unsafe artifact filename: {filename!r}")
    return root / filename


def validate_manifest_output_hashes(
    run_manifest: Mapping[str, Any], model_dir: Path, evidence_dir: Path, run_dir: Path
) -> None:
    output_hashes = require_mapping(run_manifest.get("output_sha256"), "run manifest output_sha256")
    roots = {
        "model": (model_dir, MODEL_REQUIRED_FILES),
        "evidence_before_manifest": (evidence_dir, EVIDENCE_REQUIRED_FILES - {"model_manifest.json"}),
        "run": (run_dir, RUN_REQUIRED_FILES),
    }
    if set(output_hashes) != set(roots):
        raise VerificationFailure(
            "Run manifest output groups must be model, evidence_before_manifest, and run"
        )
    for group, (root, required) in roots.items():
        declared = require_mapping(output_hashes[group], f"run manifest output_sha256.{group}")
        missing = sorted(required - set(declared))
        if missing:
            raise VerificationFailure(f"Run manifest {group} hashes missing required file(s): {', '.join(missing)}")
        for filename, expected_hash in declared.items():
            artifact = relative_artifact_path(root, filename, group)
            if not artifact.is_file():
                raise VerificationFailure(f"Run manifest references a missing {group} artifact: {artifact}")
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                raise VerificationFailure(f"Run manifest has an invalid SHA-256 for {group}/{filename}")
            actual_hash = sha256_file(artifact)
            if expected_hash.lower() != actual_hash:
                raise VerificationFailure(
                    f"Run manifest SHA-256 mismatch for {group}/{filename}: {expected_hash} != {actual_hash}"
                )


def validate_task4_manifest(task4_manifest: Mapping[str, Any], dataset: Path, injection_log: Path) -> None:
    configuration = require_mapping(task4_manifest.get("configuration"), "Task 4 manifest configuration")
    households = configuration.get("households")
    if not isinstance(households, list):
        raise VerificationFailure("Task 4 manifest configuration.households must be a list")
    household_keys = {household_key(value, "Task 4 manifest household") for value in households}
    ensure_exact_keys(household_keys, EXPECTED_HOUSEHOLD_KEYS, "Task 4 manifest")

    outputs = require_mapping(task4_manifest.get("output_sha256"), "Task 4 manifest output_sha256")
    for filename, path in {
        "anomaly_dataset.csv": dataset,
        "anomaly_injection_log.csv": injection_log,
    }.items():
        expected_hash = outputs.get(filename)
        if not isinstance(expected_hash, str) or expected_hash.lower() != sha256_file(path):
            raise VerificationFailure(f"Task 4 manifest output hash does not match current {filename}")


def validate_model_schema(
    metadata: Mapping[str, Any], model_path: Path, task4_manifest: Mapping[str, Any]
) -> list[str]:
    if metadata.get("artifact_schema") != ARTIFACT_SCHEMA:
        raise VerificationFailure("Model metadata artifact_schema is not refit_controlled_v1")

    features = require_list_of_strings(metadata.get("feature_names"), "model metadata feature_names")
    validate_feature_names(features)

    cohorts = require_mapping(metadata.get("cohorts"), "model metadata cohorts")
    primary = {household_key(value, "primary cohort household") for value in cohorts.get("primary_households", [])}
    sensitivity = {
        household_key(value, "sensitivity cohort household") for value in cohorts.get("sensitivity_households", [])
    }
    if primary != EXPECTED_PRIMARY_HOUSEHOLDS or sensitivity != EXPECTED_SENSITIVITY_HOUSEHOLDS:
        raise VerificationFailure(
            "Model metadata cohorts must keep H1/H2/H4 primary and H3/H11 sensitivity separate"
        )
    if primary & sensitivity or primary | sensitivity != EXPECTED_HOUSEHOLD_KEYS:
        raise VerificationFailure("Model metadata cohort memberships do not form the registered household partition")

    household_models = require_mapping(metadata.get("household_models"), "model metadata household_models")
    metadata_keys = {str(key) for key in household_models}
    ensure_exact_keys(metadata_keys, EXPECTED_HOUSEHOLD_KEYS, "Model metadata")
    expected_cohorts = {
        **{household: PRIMARY_COHORT for household in EXPECTED_PRIMARY_HOUSEHOLDS},
        **{household: SENSITIVITY_COHORT for household in EXPECTED_SENSITIVITY_HOUSEHOLDS},
    }
    for household in EXPECTED_HOUSEHOLD_KEYS:
        record = require_mapping(household_models[household], f"model metadata household_models.{household}")
        if record.get("cohort") != expected_cohorts[household]:
            raise VerificationFailure(f"Model metadata household {household} has the wrong evaluation cohort")
        for count_name in (
            "normal_train_feature_rows",
            "normal_validation_feature_rows",
            "held_out_test_feature_rows",
        ):
            if parse_nonnegative_int(record.get(count_name), f"model metadata H{household} {count_name}") == 0:
                raise VerificationFailure(f"Model metadata H{household} has no {count_name}")

    try:
        import joblib
    except ImportError as exc:
        raise VerificationFailure("joblib is required to inspect the Task 5 model artifact") from exc
    try:
        artifact = joblib.load(model_path)
    except Exception as exc:  # joblib may raise several serializer-specific exception types.
        raise VerificationFailure(f"Cannot load model joblib artifact at {model_path}: {exc}") from exc
    if not isinstance(artifact, Mapping):
        raise VerificationFailure("Model joblib artifact must be a mapping")
    required_joblib_keys = {"artifact_schema", "feature_names", "models_by_household", "metadata"}
    missing = sorted(required_joblib_keys - set(artifact))
    if missing:
        raise VerificationFailure(f"Model joblib artifact is missing schema key(s): {', '.join(missing)}")
    if artifact.get("artifact_schema") != ARTIFACT_SCHEMA:
        raise VerificationFailure("Model joblib artifact_schema does not reconcile with model metadata")
    joblib_features = artifact.get("feature_names")
    if joblib_features != features:
        raise VerificationFailure("Model joblib feature_names do not reconcile with model metadata")
    if artifact.get("metadata") != metadata:
        raise VerificationFailure("Model joblib embedded metadata does not reconcile with model_metadata.json")

    models = require_mapping(artifact.get("models_by_household"), "model joblib models_by_household")
    model_keys = {str(key) for key in models}
    ensure_exact_keys(model_keys, EXPECTED_HOUSEHOLD_KEYS, "Model joblib")
    if model_keys != metadata_keys:
        raise VerificationFailure("Model joblib and model metadata household keys do not reconcile")
    for household in EXPECTED_HOUSEHOLD_KEYS:
        model = models[household]
        feature_names_in = getattr(model, "feature_names_in_", None)
        if feature_names_in is not None and list(feature_names_in) != features:
            raise VerificationFailure(f"Model joblib H{household} fitted feature names do not match its schema")

    task4_configuration = require_mapping(task4_manifest.get("configuration"), "Task 4 manifest configuration")
    task4_keys = {
        household_key(value, "Task 4 manifest household")
        for value in task4_configuration.get("households", [])
    }
    if task4_keys != model_keys:
        raise VerificationFailure("Model household keys do not reconcile with Task 4 household configuration")
    return features


def validate_injection_log(path: Path, expected_event_count: int) -> dict[str, dict[str, str]]:
    required = {
        "household_id",
        "evaluation_cohort",
        "anomaly_event_id",
        "dataset_split",
        "anomaly_type",
        "label",
        "label_provenance",
    }
    rows = require_csv(path, required, "Task 4 injection log")
    by_id: dict[str, dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        event_id = row["anomaly_event_id"].strip()
        if not event_id or event_id in by_id:
            raise VerificationFailure(f"Task 4 injection log has a missing or duplicate event ID at row {row_number}")
        household = household_key(row["household_id"], f"Task 4 injection log row {row_number}")
        if household not in EXPECTED_HOUSEHOLD_KEYS:
            raise VerificationFailure(f"Task 4 injection log row {row_number} has an unexpected household H{household}")
        if row["dataset_split"].strip() != "test" or row["label"].strip() != "1":
            raise VerificationFailure(f"Task 4 injection log event {event_id} is not a held-out positive test event")
        if row["label_provenance"].strip() != "controlled_synthetic_perturbation":
            raise VerificationFailure(f"Task 4 injection log event {event_id} has incorrect label provenance")
        by_id[event_id] = row
    if len(by_id) != expected_event_count:
        raise VerificationFailure(
            f"Task 4 injection log has {len(by_id)} events; expected {expected_event_count} for this v1 verification"
        )
    return by_id


def parse_event_ids(value: str, context: str) -> set[str]:
    raw = (value or "").strip()
    if not raw:
        return set()
    pieces = [piece.strip() for piece in raw.split("|")]
    if not all(pieces):
        raise VerificationFailure(f"{context} contains an empty anomaly event ID")
    return set(pieces)


def validate_test_predictions(
    path: Path,
    injection_log: Mapping[str, Mapping[str, str]],
    expected_event_count: int,
) -> None:
    required = {
        "household_id",
        "dataset_split",
        "evaluation_cohort",
        "anomaly_label",
        "anomaly_event_ids",
    }
    rows = require_csv(path, required, "Task 5 test_predictions.csv")
    observed_event_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        split = row["dataset_split"].strip()
        label = row["anomaly_label"].strip()
        if label not in {"0", "1"}:
            raise VerificationFailure(f"test_predictions.csv has non-binary anomaly_label at row {row_number}")
        if label == "1" and split != "test":
            raise VerificationFailure(f"Positive label appears outside the test split at row {row_number}")
        if split != "test":
            raise VerificationFailure(f"test_predictions.csv contains a non-test row at row {row_number}: {split!r}")
        event_ids = parse_event_ids(row["anomaly_event_ids"], f"test_predictions.csv row {row_number}")
        if label == "0":
            if event_ids:
                raise VerificationFailure(
                    f"Negative test prediction at row {row_number} carries controlled event ID(s)"
                )
            continue

        if not event_ids:
            raise VerificationFailure(f"Positive test prediction at row {row_number} lacks an anomaly event ID")
        household = household_key(row["household_id"], f"test_predictions.csv row {row_number}")
        for event_id in event_ids:
            log_row = injection_log.get(event_id)
            if log_row is None:
                raise VerificationFailure(
                    f"Positive test prediction event ID {event_id!r} is absent from the injection log"
                )
            log_household = household_key(log_row["household_id"], f"injection log event {event_id}")
            if household != log_household:
                raise VerificationFailure(
                    f"Positive test prediction event {event_id} is assigned to H{household}, not logged H{log_household}"
                )
            if row["evaluation_cohort"].strip() != log_row["evaluation_cohort"].strip():
                raise VerificationFailure(
                    f"Positive test prediction event {event_id} has a cohort that does not reconcile with the injection log"
                )
            observed_event_ids.add(event_id)
    expected_event_ids = set(injection_log)
    if observed_event_ids != expected_event_ids:
        missing = sorted(expected_event_ids - observed_event_ids)
        unexpected = sorted(observed_event_ids - expected_event_ids)
        details: list[str] = []
        if missing:
            details.append(f"missing from test predictions={missing}")
        if unexpected:
            details.append(f"not in injection log={unexpected}")
        raise VerificationFailure(
            "Positive event IDs do not reconcile with the "
            f"{expected_event_count}-event injection log ({'; '.join(details)})"
        )


def validate_thresholds(
    path: Path,
    training_config: Mapping[str, Any],
    metadata: Mapping[str, Any],
    expected_quantile: float,
) -> None:
    arguments = require_mapping(training_config.get("arguments"), "training_config arguments")
    configured_quantile = parse_float(
        arguments.get("validation_score_quantile"), "training_config validation_score_quantile"
    )
    if not math.isclose(configured_quantile, expected_quantile, rel_tol=0.0, abs_tol=1e-12):
        raise VerificationFailure(
            f"training_config validation score quantile is {configured_quantile:g}, not configured {expected_quantile:g}"
        )
    required = {
        "household_id",
        "detector",
        "validation_score_quantile",
        "threshold",
    }
    rows = require_csv(path, required, "validation thresholds")
    threshold_rows: dict[tuple[str, str], dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        household = household_key(row["household_id"], f"validation thresholds row {row_number}")
        detector = row["detector"].strip()
        key = (household, detector)
        if key in threshold_rows:
            raise VerificationFailure(f"validation thresholds has duplicate row for H{household}/{detector}")
        threshold_rows[key] = row
        quantile = parse_float(row["validation_score_quantile"], f"validation thresholds row {row_number} quantile")
        if not math.isclose(quantile, expected_quantile, rel_tol=0.0, abs_tol=1e-12):
            raise VerificationFailure(
                f"validation thresholds row {row_number} uses {quantile:g}, not configured {expected_quantile:g}"
            )
        parse_float(row["threshold"], f"validation thresholds row {row_number} threshold")
    expected_pairs = {(household, detector) for household in EXPECTED_HOUSEHOLD_KEYS for detector in EXPECTED_DETECTORS}
    if set(threshold_rows) != expected_pairs:
        raise VerificationFailure("validation threshold rows do not cover exactly both detectors for H1/H2/H3/H4/H11")

    household_models = require_mapping(metadata.get("household_models"), "model metadata household_models")
    threshold_fields = {
        "isolation_forest": "threshold_isolation_forest",
        "robust_residual": "threshold_robust_residual",
    }
    for (household, detector), row in threshold_rows.items():
        metadata_threshold = parse_float(
            require_mapping(household_models[household], f"model metadata H{household}").get(
                threshold_fields[detector]
            ),
            f"model metadata H{household} {threshold_fields[detector]}",
        )
        csv_threshold = parse_float(row["threshold"], f"validation thresholds H{household}/{detector}")
        if not math.isclose(csv_threshold, metadata_threshold, rel_tol=1e-9, abs_tol=1e-9):
            raise VerificationFailure(
                f"validation threshold for H{household}/{detector} does not reconcile with model metadata"
            )


def validate_cohort_metrics(path: Path) -> None:
    required = {"scope_kind", "scope", "detector", "metric_semantics"}
    rows = require_csv(path, required, "cohort metrics")
    pairs: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        if row["scope_kind"].strip() != "cohort":
            raise VerificationFailure(f"cohort metrics row {row_number} is not labelled as a cohort result")
        scope = row["scope"].strip()
        detector = row["detector"].strip()
        if scope not in EXPECTED_COHORT_SCOPES:
            raise VerificationFailure(
                f"cohort metrics row {row_number} has pooled or unexpected cohort scope {scope!r}"
            )
        if detector not in EXPECTED_DETECTORS:
            raise VerificationFailure(f"cohort metrics row {row_number} has unexpected detector {detector!r}")
        if (scope, detector) in pairs:
            raise VerificationFailure(f"cohort metrics has a duplicate result for {scope}/{detector}")
        pairs.add((scope, detector))
    expected_pairs = {(scope, detector) for scope in EXPECTED_COHORT_SCOPES for detector in EXPECTED_DETECTORS}
    if pairs != expected_pairs:
        raise VerificationFailure(
            "cohort metrics must report primary and documented-solar sensitivity cohorts separately for both detectors"
        )


def is_na(value: str) -> bool:
    return value.strip().lower() in {"", "n/a", "na", "not_applicable", "not applicable"}


def validate_zero_episode_scenarios(path: Path) -> None:
    required = {
        "detector",
        "evaluation_cohort",
        "scenario",
        "episode_count",
        "evaluable_episode_count",
        "detected_episode_count",
        "episode_detection_rate",
        "median_bin_close_detection_delay_seconds",
        "maximum_bin_close_detection_delay_seconds",
        "result_status",
    }
    rows = require_csv(path, required, "per-scenario metrics")
    expected_pairs = {
        (detector, cohort)
        for detector in EXPECTED_DETECTORS
        for cohort in (PRIMARY_COHORT, SENSITIVITY_COHORT)
    }
    stuck_rows: dict[tuple[str, str], dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        if row["scenario"].strip() != "stuck_signal":
            continue
        key = (row["detector"].strip(), row["evaluation_cohort"].strip())
        if key in stuck_rows:
            raise VerificationFailure(f"per-scenario metrics has duplicate stuck_signal row at row {row_number}")
        stuck_rows[key] = row
    if set(stuck_rows) != expected_pairs:
        raise VerificationFailure(
            "per-scenario metrics must contain a stuck_signal row for each detector and each separate cohort"
        )
    for (detector, cohort), row in stuck_rows.items():
        context = f"per-scenario stuck_signal {detector}/{cohort}"
        for column in ("episode_count", "evaluable_episode_count", "detected_episode_count"):
            if parse_nonnegative_int(row[column], f"{context} {column}") != 0:
                raise VerificationFailure(f"{context} is not a zero-episode scenario")
        if row["result_status"].strip().lower() not in {
            "not_applicable_zero_episodes",
            "n/a",
            "not applicable",
        }:
            raise VerificationFailure(f"{context} is not marked N/A for zero episodes")
        for column in (
            "episode_detection_rate",
            "median_bin_close_detection_delay_seconds",
            "maximum_bin_close_detection_delay_seconds",
        ):
            if not is_na(row[column]):
                raise VerificationFailure(f"{context} invents a {column} result instead of N/A")


def verify(args: argparse.Namespace) -> VerificationSummary:
    if args.expected_event_count <= 0:
        raise VerificationFailure("--expected-event-count must be positive")
    if not 0.5 < args.validation_score_quantile < 1.0:
        raise VerificationFailure("--validation-score-quantile must be in (0.5, 1)")
    for path in (args.dataset, args.dataset_manifest, args.injection_log):
        if not path.is_file():
            raise VerificationFailure(f"Required current Task 4 input is missing: {path}")
    require_files(args.model_dir, MODEL_REQUIRED_FILES, "model")
    require_files(args.evidence_dir, EVIDENCE_REQUIRED_FILES, "evidence")
    require_files(args.run_dir, RUN_REQUIRED_FILES, "run")

    metadata = load_json(args.model_dir / "model_metadata.json", "model metadata")
    run_manifest = load_json(args.evidence_dir / "model_manifest.json", "Task 5 run manifest")
    training_config = load_json(args.evidence_dir / "training_config.json", "training configuration")
    task4_manifest = load_json(args.dataset_manifest, "Task 4 generation manifest")

    validate_input_hashes(metadata, args.dataset, args.dataset_manifest, args.injection_log, "model metadata")
    validate_input_hashes(run_manifest, args.dataset, args.dataset_manifest, args.injection_log, "run manifest")
    validate_task4_manifest(task4_manifest, args.dataset, args.injection_log)
    validate_semantic_boundary(metadata, run_manifest)
    validate_manifest_output_hashes(run_manifest, args.model_dir, args.evidence_dir, args.run_dir)
    features = validate_model_schema(
        metadata,
        args.model_dir / "isolation_forest_by_household.joblib",
        task4_manifest,
    )
    injection_log = validate_injection_log(args.injection_log, args.expected_event_count)
    validate_test_predictions(
        args.run_dir / "test_predictions.csv",
        injection_log,
        args.expected_event_count,
    )
    validate_thresholds(
        args.evidence_dir / "validation_thresholds.csv",
        training_config,
        metadata,
        args.validation_score_quantile,
    )
    validate_cohort_metrics(args.evidence_dir / "cohort_metrics.csv")
    validate_zero_episode_scenarios(args.evidence_dir / "per_scenario_metrics.csv")
    return VerificationSummary(event_count=len(injection_log), feature_count=len(features))


def main() -> int:
    args = parse_args()
    try:
        summary = verify(args)
    except VerificationFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Keep malformed artifacts from emitting a misleading PASS.
        print(f"FAIL: unexpected verifier error: {exc}", file=sys.stderr)
        return 1

    print("PASS: verified Task 5 REFIT controlled-perturbation v1 artifacts")
    print(
        "  required files: "
        f"model={len(MODEL_REQUIRED_FILES)}, evidence={len(EVIDENCE_REQUIRED_FILES)}, run={len(RUN_REQUIRED_FILES)}"
    )
    print("  input hashes: current final Task 4 dataset, manifest, and injection log match")
    print("  household models: 1, 2, 3, 4, 11")
    print(f"  controlled event IDs reconciled: {summary.event_count}")
    print(f"  feature contract: {summary.feature_count} names contain no prohibited leakage shortcuts")
    print(f"  validation score quantile: {args.validation_score_quantile:g}")
    print("  primary and sensitivity cohorts remain separate; zero-event stuck_signal results are N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
