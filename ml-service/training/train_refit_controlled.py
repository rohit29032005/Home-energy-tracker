"""Train and evaluate a REFIT controlled-perturbation one-class benchmark.

This is intentionally separate from ``training/train.py`` and does not replace
the legacy supervised smart-meter artifact used by the running ML service.

The Task 4 labels are deliberately test-only.  Therefore this trainer fits
normal-only, per-household Isolation Forest detectors on the chronological
training slice, calibrates thresholds on normal validation scores, and uses
the held-out labels once for *controlled-perturbation* evaluation.  It must
never be described as real-world appliance-fault classification.

The model consumes only information reproducible from a replay meter stream:
the replayed interval-energy value, its timestamp and the interval duration.
It does not use labels, raw aggregate-power columns, REFIT Issues, IQR flags,
solar flags, source row IDs, or original/unmodified energy as model features.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

# The desktop workspace cannot write to the user's global matplotlib cache.
# Use a task-specific temporary cache before importing pyplot.
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "home-energy-tracker-task5-matplotlib")
)

import joblib
import matplotlib
import numpy as np
import pandas as pd
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


SCRIPT_VERSION = "1.1.0"
ARTIFACT_SCHEMA = "refit_controlled_v1"
DEFAULT_SEED = 20261009
PRIMARY_HOUSEHOLDS = {1, 2, 4}
SENSITIVITY_HOUSEHOLDS = {3, 11}
REQUIRED_COLUMNS = {
    "household_id",
    "source_unix",
    "timestamp_utc",
    "interval_seconds",
    "is_replayable",
    "source_quality_issue_flag",
    "dataset_split",
    "evaluation_cohort",
    "synthetic_replay_energy_kwh",
    "anomaly_label",
    "anomaly_type",
    "anomaly_event_id",
    "label_provenance",
}
MODEL_FEATURES = [
    "log1p_power_proxy_w",
    "robust_residual",
    "scaled_change",
    "trailing_variability",
    "time_of_day_sin",
    "time_of_day_cos",
]
EPSILON = 1e-12


@dataclass(frozen=True)
class LabeledEvent:
    household_id: int
    timestamp_epoch: int
    timestamp_utc: str
    interval_seconds: int
    is_replayable: bool
    source_quality_issue: bool
    dataset_split: str
    evaluation_cohort: str
    synthetic_energy_kwh: float
    anomaly_label: int
    anomaly_type: str
    anomaly_event_id: str
    label_provenance: str


@dataclass
class BinAccumulator:
    household_id: int
    bin_start_epoch: int
    energy_kwh: float = 0.0
    coverage_seconds: float = 0.0
    split_values: set[str] = field(default_factory=set)
    cohort_values: set[str] = field(default_factory=set)
    source_quality_issue: bool = False
    non_replayable: bool = False
    material_gap: bool = False
    positive_event_ids: set[str] = field(default_factory=set)
    anomaly_types: set[str] = field(default_factory=set)
    positive_coverage_seconds: float = 0.0
    contributing_rows: int = 0


@dataclass(frozen=True)
class BinRecord:
    household_id: int
    bin_start_epoch: int
    timestamp_utc: str
    dataset_split: str
    evaluation_cohort: str
    energy_kwh: float
    coverage_seconds: float
    power_proxy_w: float
    anomaly_label: int
    anomaly_types: str
    anomaly_event_ids: str
    positive_coverage_seconds: float
    quality_status: str
    stream_segment_id: int = 0


@dataclass(frozen=True)
class HouseholdTrainingResult:
    household_id: int
    cohort: str
    threshold_isolation_forest: float
    threshold_robust_residual: float
    model: Pipeline
    model_parameters: dict[str, Any]
    scale_floor_w: float
    train_rows: int
    validation_rows: int
    test_rows: int


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Fit normal-only, per-household REFIT controlled-perturbation detectors."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_dataset.csv",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_generation_manifest.json",
    )
    parser.add_argument(
        "--injection-log",
        type=Path,
        default=root / "data" / "refit" / "labeled-verified" / "anomaly_injection_log.csv",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=root / "ml-service" / "models" / "refit-controlled-v1",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=root / "evidence" / "18_refit_controlled_ml",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=root / "data" / "refit" / "ml_runs" / "refit_controlled_v1",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bin-seconds", type=int, default=300)
    parser.add_argument("--minimum-coverage-seconds", type=float, default=285.0)
    parser.add_argument("--history-bins", type=int, default=6)
    parser.add_argument("--mad-floor-relative", type=float, default=0.05)
    parser.add_argument("--mad-floor-min-w", type=float, default=1.0)
    parser.add_argument("--validation-score-quantile", type=float, default=0.99)
    parser.add_argument("--persistence-bins", type=int, default=3)
    parser.add_argument("--isolation-forest-trees", type=int, default=256)
    parser.add_argument("--isolation-forest-max-samples", type=int, default=256)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    for path in (args.dataset, args.dataset_manifest, args.injection_log):
        if not path.is_file():
            raise FileNotFoundError(f"Required Task 4 input not found: {path}")
    for output in (args.model_dir, args.evidence_dir, args.run_dir):
        if output.exists():
            raise FileExistsError(
                f"Output path already exists: {output}. Use an explicit new output directory; "
                "this trainer never overwrites evidence or model artifacts."
            )
    if args.bin_seconds != 300:
        raise ValueError("This benchmark protocol is pre-registered for UTC-aligned 300-second bins")
    if not 0 < args.minimum_coverage_seconds <= args.bin_seconds:
        raise ValueError("--minimum-coverage-seconds must be in (0, --bin-seconds]")
    if args.history_bins < 2:
        raise ValueError("--history-bins must be at least 2")
    if args.mad_floor_relative <= 0 or args.mad_floor_min_w <= 0:
        raise ValueError("MAD floor parameters must be positive")
    if not 0.5 < args.validation_score_quantile < 1.0:
        raise ValueError("--validation-score-quantile must be in (0.5, 1)")
    if args.persistence_bins < 1:
        raise ValueError("--persistence-bins must be >= 1")
    if args.isolation_forest_trees < 1 or args.isolation_forest_max_samples < 2:
        raise ValueError("Isolation Forest parameters are invalid")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def boolish(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def finite_float(value: str, field: str, row_number: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: invalid {field}={value!r}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Row {row_number}: non-finite {field}={value!r}")
    return parsed


def int_value(value: str, field: str, row_number: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: invalid {field}={value!r}") from exc


def cohort_for(household_id: int) -> str:
    if household_id in PRIMARY_HOUSEHOLDS:
        return "primary_no_documented_solar_interference"
    if household_id in SENSITIVITY_HOUSEHOLDS:
        return "sensitivity_documented_solar_interference"
    raise ValueError(f"Household {household_id} is outside the declared REFIT Task 4 cohort")


def load_task4_manifest(path: Path, dataset_path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    semantic = manifest.get("semantic_boundary", {})
    if semantic.get("official_refit_anomaly_labels_used") is not False:
        raise ValueError("Task 4 manifest does not declare controlled synthetic label semantics")
    if semantic.get("task2_source_modified") is not False:
        raise ValueError("Task 4 manifest must declare frozen Task 2 source preservation")
    expected_dataset_hash = manifest.get("output_sha256", {}).get("anomaly_dataset.csv")
    actual_dataset_hash = sha256_file(dataset_path)
    if expected_dataset_hash != actual_dataset_hash:
        raise ValueError(
            "Task 4 dataset hash does not match its generation manifest; run the Task 4 verifier first"
        )
    configuration = manifest.get("configuration", {})
    required = {"seed", "train_fraction", "validation_fraction", "households"}
    missing = required - set(configuration)
    if missing:
        raise ValueError(f"Task 4 manifest lacks configuration field(s): {', '.join(sorted(missing))}")
    if int(configuration["seed"]) != DEFAULT_SEED:
        raise ValueError(
            f"This registered Task 5 protocol expects Task 4 seed {DEFAULT_SEED}, got {configuration['seed']}"
        )
    return manifest


def parse_event(row: dict[str, str], row_number: int) -> LabeledEvent:
    household_id = int_value(row.get("household_id", ""), "household_id", row_number)
    timestamp_epoch = int_value(row.get("source_unix", ""), "source_unix", row_number)
    interval_seconds = int_value(row.get("interval_seconds", ""), "interval_seconds", row_number)
    signal = finite_float(row.get("synthetic_replay_energy_kwh", ""), "synthetic_replay_energy_kwh", row_number)
    label = int_value(row.get("anomaly_label", ""), "anomaly_label", row_number)
    if interval_seconds <= 0 or interval_seconds > 16:
        raise ValueError(f"Row {row_number}: Task 4 replayable interval must be in 1..16 seconds")
    if signal < 0:
        raise ValueError(f"Row {row_number}: synthetic replay energy must be non-negative")
    if label not in {0, 1}:
        raise ValueError(f"Row {row_number}: anomaly_label must be binary")
    split = row.get("dataset_split", "")
    if split not in {"train", "validation", "test"}:
        raise ValueError(f"Row {row_number}: unsupported split {split!r}")
    provenance = row.get("label_provenance", "")
    if label == 1 and provenance != "controlled_synthetic_perturbation":
        raise ValueError(f"Row {row_number}: positive label has invalid provenance")
    if label == 0 and provenance != "unmodified_recorded_baseline":
        raise ValueError(f"Row {row_number}: normal label has invalid provenance")
    return LabeledEvent(
        household_id=household_id,
        timestamp_epoch=timestamp_epoch,
        timestamp_utc=row.get("timestamp_utc", ""),
        interval_seconds=interval_seconds,
        is_replayable=boolish(row.get("is_replayable", "")),
        source_quality_issue=boolish(row.get("source_quality_issue_flag", "")),
        dataset_split=split,
        evaluation_cohort=row.get("evaluation_cohort", ""),
        synthetic_energy_kwh=signal,
        anomaly_label=label,
        anomaly_type=row.get("anomaly_type", ""),
        anomaly_event_id=row.get("anomaly_event_id", ""),
        label_provenance=provenance,
    )


def iter_household_events(path: Path) -> Iterator[tuple[int, list[LabeledEvent]]]:
    """Stream the large derived CSV and retain only one household at a time."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fields
        if missing:
            raise ValueError(f"Task 4 dataset is missing column(s): {', '.join(sorted(missing))}")
        current_household: int | None = None
        events: list[LabeledEvent] = []
        seen_households: set[int] = set()
        for row_number, row in enumerate(reader, start=2):
            event = parse_event(row, row_number)
            if event.evaluation_cohort != cohort_for(event.household_id):
                raise ValueError(f"Row {row_number}: unexpected evaluation cohort label")
            if current_household is None:
                current_household = event.household_id
            if event.household_id != current_household:
                if event.household_id in seen_households:
                    raise ValueError("Task 4 dataset interleaves household records")
                if not events:
                    raise AssertionError("Empty household group")
                yield current_household, events
                seen_households.add(current_household)
                current_household = event.household_id
                events = []
            if events and event.timestamp_epoch <= events[-1].timestamp_epoch:
                raise ValueError(f"Household {event.household_id} source chronology is not strictly increasing")
            events.append(event)
        if current_household is not None:
            yield current_household, events


def expected_split(index: int, total: int, train_fraction: float, validation_fraction: float) -> str:
    train_end = int(math.floor(total * train_fraction))
    validation_end = int(math.floor(total * (train_fraction + validation_fraction)))
    return "train" if index < train_end else "validation" if index < validation_end else "test"


def validate_household_splits(events: Sequence[LabeledEvent], manifest: dict[str, Any]) -> None:
    configuration = manifest["configuration"]
    train_fraction = float(configuration["train_fraction"])
    validation_fraction = float(configuration["validation_fraction"])
    household = events[0].household_id
    for index, event in enumerate(events):
        if event.dataset_split != expected_split(index, len(events), train_fraction, validation_fraction):
            raise ValueError(f"Household {household} split boundary mismatch at source index {index}")
        if event.dataset_split in {"train", "validation"} and event.anomaly_label != 0:
            raise ValueError(f"Household {household} has forbidden positive label outside test")


def bin_start(epoch_seconds: int, bin_seconds: int) -> int:
    return epoch_seconds - (epoch_seconds % bin_seconds)


def add_event_to_bins(
    bins: dict[int, BinAccumulator],
    event: LabeledEvent,
    bin_seconds: int,
) -> list[int]:
    """Allocate an interval-energy event by exact overlap with UTC five-minute bins."""
    interval_start = event.timestamp_epoch - event.interval_seconds
    interval_end = event.timestamp_epoch
    cursor = interval_start
    keys: list[int] = []
    while cursor < interval_end:
        start = bin_start(cursor, bin_seconds)
        end = start + bin_seconds
        overlap = min(interval_end, end) - cursor
        accumulator = bins.setdefault(start, BinAccumulator(event.household_id, start))
        accumulator.energy_kwh += event.synthetic_energy_kwh * (overlap / event.interval_seconds)
        accumulator.coverage_seconds += overlap
        accumulator.split_values.add(event.dataset_split)
        accumulator.cohort_values.add(event.evaluation_cohort)
        accumulator.source_quality_issue = accumulator.source_quality_issue or event.source_quality_issue
        accumulator.non_replayable = accumulator.non_replayable or not event.is_replayable
        accumulator.contributing_rows += 1
        if event.anomaly_label:
            accumulator.positive_event_ids.add(event.anomaly_event_id)
            accumulator.anomaly_types.add(event.anomaly_type)
            accumulator.positive_coverage_seconds += overlap
        keys.append(start)
        cursor += overlap
    return keys


def build_bins(events: Sequence[LabeledEvent], args: argparse.Namespace) -> list[BinRecord]:
    bins: dict[int, BinAccumulator] = {}
    previous_event: LabeledEvent | None = None
    for event in events:
        keys = add_event_to_bins(bins, event, args.bin_seconds)
        if previous_event is not None and event.timestamp_epoch - previous_event.timestamp_epoch > 16:
            previous_key = bin_start(previous_event.timestamp_epoch - 1, args.bin_seconds)
            bins[previous_key].material_gap = True
            for key in keys:
                bins[key].material_gap = True
        previous_event = event

    records: list[BinRecord] = []
    for start, accumulator in sorted(bins.items()):
        reasons: list[str] = []
        if accumulator.coverage_seconds + EPSILON < args.minimum_coverage_seconds:
            reasons.append("insufficient_coverage")
        if len(accumulator.split_values) != 1:
            reasons.append("split_boundary")
        if len(accumulator.cohort_values) != 1:
            reasons.append("cohort_inconsistency")
        if accumulator.source_quality_issue:
            reasons.append("source_quality_issue")
        if accumulator.non_replayable:
            reasons.append("non_replayable")
        if accumulator.material_gap:
            reasons.append("material_gap")
        split = next(iter(accumulator.split_values)) if len(accumulator.split_values) == 1 else "excluded"
        cohort = next(iter(accumulator.cohort_values)) if len(accumulator.cohort_values) == 1 else "excluded"
        quality_status = "eligible" if not reasons else ";".join(reasons)
        power_proxy = (
            accumulator.energy_kwh * 3_600_000.0 / accumulator.coverage_seconds
            if accumulator.coverage_seconds > 0
            else math.nan
        )
        records.append(
            BinRecord(
                household_id=accumulator.household_id,
                bin_start_epoch=start,
                timestamp_utc=datetime.fromtimestamp(start, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                dataset_split=split,
                evaluation_cohort=cohort,
                energy_kwh=accumulator.energy_kwh,
                coverage_seconds=accumulator.coverage_seconds,
                power_proxy_w=power_proxy,
                anomaly_label=int(bool(accumulator.positive_event_ids)),
                anomaly_types="|".join(sorted(accumulator.anomaly_types)),
                anomaly_event_ids="|".join(sorted(accumulator.positive_event_ids)),
                positive_coverage_seconds=accumulator.positive_coverage_seconds,
                quality_status=quality_status,
            )
        )
    return records


def quality_report_frame(records: Sequence[BinRecord]) -> pd.DataFrame:
    """Summarise quality gates without making a quality flag a model feature."""
    counter: Counter[tuple[int, str, str, str]] = Counter()
    for record in records:
        status = "eligible" if record.quality_status == "eligible" else "excluded"
        reason = "eligible" if status == "eligible" else record.quality_status
        counter[(record.household_id, record.dataset_split, status, reason)] += 1
    rows = [
        {
            "household_id": household_id,
            "dataset_split": dataset_split,
            "bin_status": status,
            "quality_reason": reason,
            "bin_count": count,
        }
        for (household_id, dataset_split, status, reason), count in sorted(counter.items())
    ]
    return pd.DataFrame(rows)


def calculate_scale_floor(records: Sequence[BinRecord], args: argparse.Namespace) -> float:
    """Derive a household robust-scale floor from normal training bins only."""
    train_power = [
        record.power_proxy_w
        for record in records
        if record.quality_status == "eligible" and record.dataset_split == "train"
    ]
    train_labels = [
        record.anomaly_label
        for record in records
        if record.quality_status == "eligible" and record.dataset_split == "train"
    ]
    if not train_power:
        raise ValueError("No eligible training bins were available to define the robust scale floor")
    if any(train_labels):
        raise ValueError("Normal-only training was violated by a positive training bin")
    median_power = float(np.median(np.asarray(train_power, dtype=float)))
    return max(args.mad_floor_min_w, median_power * args.mad_floor_relative)


def build_feature_frame(
    records: Sequence[BinRecord],
    scale_floor_w: float,
    args: argparse.Namespace,
) -> pd.DataFrame:
    """Construct causal, per-household features with an explicit warm-up state.

    The history excludes the current bin and is reset at every data-quality or
    continuity break.  Consequently, no row uses a later bin, a label, or any
    source diagnostic as a predictor.
    """
    if not records:
        raise ValueError("Cannot make feature frame from zero bins")
    household_id = records[0].household_id
    if any(record.household_id != household_id for record in records):
        raise ValueError("A feature frame must contain one household only")

    history: deque[float] = deque(maxlen=args.history_bins)
    previous_good_start: int | None = None
    segment_id = 0
    rows: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.bin_start_epoch):
        is_eligible = record.quality_status == "eligible" and math.isfinite(record.power_proxy_w)
        continuity_break = (
            not is_eligible
            or previous_good_start is None
            or record.bin_start_epoch - previous_good_start != args.bin_seconds
        )
        if continuity_break:
            segment_id += 1
            history.clear()

        row: dict[str, Any] = {
            "household_id": record.household_id,
            "bin_start_epoch": record.bin_start_epoch,
            "timestamp_utc": record.timestamp_utc,
            "dataset_split": record.dataset_split,
            "evaluation_cohort": record.evaluation_cohort,
            "energy_kwh": record.energy_kwh,
            "coverage_seconds": record.coverage_seconds,
            "power_proxy_w": record.power_proxy_w,
            "anomaly_label": record.anomaly_label,
            "anomaly_types": record.anomaly_types,
            "anomaly_event_ids": record.anomaly_event_ids,
            "positive_coverage_seconds": record.positive_coverage_seconds,
            "quality_status": record.quality_status,
            "stream_segment_id": segment_id,
            "feature_ready": False,
        }
        for feature in MODEL_FEATURES:
            row[feature] = math.nan

        if is_eligible and len(history) == args.history_bins:
            previous = history[-1]
            history_values = np.asarray(history, dtype=float)
            history_median = float(np.median(history_values))
            history_mad = float(np.median(np.abs(history_values - history_median)))
            robust_scale = max(1.4826 * history_mad, scale_floor_w)
            current = record.power_proxy_w
            second_of_day = record.bin_start_epoch % 86_400
            angle = 2.0 * math.pi * second_of_day / 86_400.0
            row.update(
                {
                    "log1p_power_proxy_w": math.log1p(current),
                    "robust_residual": (current - history_median) / robust_scale,
                    "scaled_change": (current - previous) / robust_scale,
                    "trailing_variability": (1.4826 * history_mad) / scale_floor_w,
                    "time_of_day_sin": math.sin(angle),
                    "time_of_day_cos": math.cos(angle),
                    "feature_ready": True,
                }
            )

        if is_eligible:
            history.append(record.power_proxy_w)
            previous_good_start = record.bin_start_epoch
        else:
            previous_good_start = None
        rows.append(row)

    frame = pd.DataFrame(rows)
    if set(MODEL_FEATURES) - set(frame.columns):
        raise AssertionError("Model feature contract is incomplete")
    forbidden = {
        "anomaly_label",
        "anomaly_types",
        "anomaly_event_ids",
        "dataset_split",
        "evaluation_cohort",
        "quality_status",
        "positive_coverage_seconds",
    }
    if set(MODEL_FEATURES) & forbidden:
        raise AssertionError("Label, split, or quality metadata entered the model feature contract")
    return frame


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    matrix = frame.loc[:, MODEL_FEATURES].copy()
    if matrix.empty:
        raise ValueError("No feature rows were supplied")
    if not np.isfinite(matrix.to_numpy(dtype=float)).all():
        raise ValueError("Feature matrix contains a non-finite value")
    return matrix


def isolation_scores(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    """Return an uncalibrated score where larger values mean more unusual."""
    return -np.asarray(model.decision_function(feature_matrix(frame)), dtype=float)


def validation_threshold(scores: np.ndarray, quantile: float, label: str) -> float:
    if scores.size == 0 or not np.isfinite(scores).all():
        raise ValueError(f"Cannot calibrate {label} threshold from an invalid validation score set")
    return float(np.quantile(scores, quantile))


def fit_household_detector(
    frame: pd.DataFrame,
    scale_floor_w: float,
    args: argparse.Namespace,
) -> HouseholdTrainingResult:
    household_values = frame["household_id"].unique().tolist()
    if len(household_values) != 1:
        raise ValueError("Each detector must be fit to exactly one household")
    household_id = int(household_values[0])
    cohort_values = frame["evaluation_cohort"].unique().tolist()
    if len(cohort_values) != 1:
        raise ValueError("Each detector must have one declared evaluation cohort")

    ready = frame["feature_ready"].astype(bool)
    train = frame.loc[ready & frame["dataset_split"].eq("train")].copy()
    validation = frame.loc[ready & frame["dataset_split"].eq("validation")].copy()
    test = frame.loc[ready & frame["dataset_split"].eq("test")].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError(f"Household {household_id} does not have feature-ready records in every split")
    if train["anomaly_label"].any() or validation["anomaly_label"].any():
        raise ValueError(f"Household {household_id}: labels outside held-out test attempted to enter training")
    if len(train) < 2:
        raise ValueError(f"Household {household_id}: too few normal training rows for Isolation Forest")

    max_samples = min(args.isolation_forest_max_samples, len(train))
    model = Pipeline(
        [
            ("robust_scaler", RobustScaler()),
            (
                "isolation_forest",
                IsolationForest(
                    n_estimators=args.isolation_forest_trees,
                    max_samples=max_samples,
                    contamination="auto",
                    random_state=args.seed + household_id,
                    n_jobs=1,
                ),
            ),
        ]
    )
    model.fit(feature_matrix(train))
    validation_if_scores = isolation_scores(model, validation)
    validation_baseline_scores = np.abs(validation["robust_residual"].to_numpy(dtype=float))
    return HouseholdTrainingResult(
        household_id=household_id,
        cohort=str(cohort_values[0]),
        threshold_isolation_forest=validation_threshold(
            validation_if_scores, args.validation_score_quantile, "Isolation Forest"
        ),
        threshold_robust_residual=validation_threshold(
            validation_baseline_scores, args.validation_score_quantile, "robust residual"
        ),
        model=model,
        model_parameters={
            "algorithm": "IsolationForest",
            "n_estimators": args.isolation_forest_trees,
            "max_samples": max_samples,
            "contamination": "auto",
            "random_state": args.seed + household_id,
            "scaler": "RobustScaler",
        },
        scale_floor_w=scale_floor_w,
        train_rows=len(train),
        validation_rows=len(validation),
        test_rows=len(test),
    )


def add_scores_and_persistence(
    frame: pd.DataFrame,
    result: HouseholdTrainingResult,
    args: argparse.Namespace,
) -> pd.DataFrame:
    """Apply pre-calibrated scores and a causal N-consecutive-bin alert rule."""
    scored = frame.copy().sort_values("bin_start_epoch").reset_index(drop=True)
    ready = scored["feature_ready"].astype(bool)
    scored["isolation_forest_score"] = math.nan
    scored["robust_residual_score"] = math.nan
    if ready.any():
        ready_frame = scored.loc[ready]
        scored.loc[ready, "isolation_forest_score"] = isolation_scores(result.model, ready_frame)
        scored.loc[ready, "robust_residual_score"] = np.abs(
            ready_frame["robust_residual"].to_numpy(dtype=float)
        )

    for detector, threshold in (
        ("isolation_forest", result.threshold_isolation_forest),
        ("robust_residual", result.threshold_robust_residual),
    ):
        candidate_column = f"{detector}_candidate"
        alert_column = f"{detector}_alert"
        alert_start_column = f"{detector}_alert_start"
        score_column = f"{detector}_score"
        candidates: list[bool] = []
        alerts: list[bool] = []
        alert_starts: list[bool] = []
        streak = 0
        prior_segment: int | None = None
        for row in scored.itertuples(index=False):
            usable = bool(row.feature_ready) and math.isfinite(float(getattr(row, score_column)))
            segment = int(row.stream_segment_id)
            if not usable or prior_segment is None or segment != prior_segment:
                streak = 0
            candidate = usable and float(getattr(row, score_column)) > threshold
            if candidate:
                streak += 1
            else:
                streak = 0
            alert = candidate and streak >= args.persistence_bins
            candidates.append(candidate)
            alerts.append(alert)
            alert_starts.append(alert and streak == args.persistence_bins)
            prior_segment = segment if usable else None
        scored[candidate_column] = candidates
        scored[alert_column] = alerts
        scored[alert_start_column] = alert_starts
    return scored


def optional_auc(metric_function: Any, labels: np.ndarray, scores: np.ndarray) -> float:
    """Return NaN when a score metric is undefined for a one-class evaluation set."""
    if len(np.unique(labels)) < 2:
        return math.nan
    return float(metric_function(labels, scores))


def controlled_row_metrics(
    scored: pd.DataFrame,
    detector: str,
    scope_kind: str,
    scope: str,
) -> dict[str, Any]:
    """Calculate test-only controlled-label metrics for one already-fit detector."""
    required = {f"{detector}_score", f"{detector}_alert"}
    if required - set(scored.columns):
        raise ValueError(f"Scores for {detector} are absent")
    test = scored.loc[
        scored["dataset_split"].eq("test") & scored["feature_ready"].astype(bool)
    ].copy()
    if test.empty:
        raise ValueError(f"{scope}: no held-out feature-ready bins available for controlled evaluation")
    labels = test["anomaly_label"].to_numpy(dtype=int)
    alerts = test[f"{detector}_alert"].to_numpy(dtype=bool).astype(int)
    scores = test[f"{detector}_score"].to_numpy(dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError(f"{scope}: non-finite {detector} test score")
    tn, fp, fn, tp = confusion_matrix(labels, alerts, labels=[0, 1]).ravel()
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, alerts, average="binary", zero_division=0
    )
    normal_count = int((labels == 0).sum())
    return {
        "scope_kind": scope_kind,
        "scope": scope,
        "detector": detector,
        "metric_semantics": "held-out controlled-perturbation bins only",
        "test_feature_ready_bins": int(len(test)),
        "test_unscored_bins": int(
            scored["dataset_split"].eq("test").sum() - len(test)
        ),
        "controlled_positive_bins": int(labels.sum()),
        "controlled_positive_overlap_seconds": float(test.loc[test["anomaly_label"].eq(1), "positive_coverage_seconds"].sum()),
        "controlled_positive_truth_rule": "any exact interval-overlap second within a five-minute bin",
        "unmodified_baseline_bins": normal_count,
        "true_positive_alert_bins": int(tp),
        "false_positive_alert_bins": int(fp),
        "false_negative_alert_bins": int(fn),
        "true_negative_bins": int(tn),
        "controlled_precision": float(precision),
        "controlled_recall": float(recall),
        "controlled_f1": float(f1),
        "controlled_pr_auc": optional_auc(average_precision_score, labels, scores),
        "controlled_roc_auc": optional_auc(roc_auc_score, labels, scores),
        "normal_bin_false_alert_rate": float(fp / normal_count) if normal_count else math.nan,
        "normal_bin_specificity": float(tn / normal_count) if normal_count else math.nan,
        "false_alerts_per_10k_normal_bins": float(10_000.0 * fp / normal_count)
        if normal_count
        else math.nan,
    }


INJECTION_REQUIRED_COLUMNS = {
    "household_id",
    "evaluation_cohort",
    "anomaly_event_id",
    "dataset_split",
    "start_source_unix",
    "end_source_unix",
    "start_timestamp_utc",
    "end_timestamp_utc",
    "anomaly_type",
    "duration_seconds",
    "event_row_count",
    "label",
    "label_provenance",
}


def load_injection_log(path: Path) -> pd.DataFrame:
    episodes = pd.read_csv(path)
    missing = INJECTION_REQUIRED_COLUMNS - set(episodes.columns)
    if missing:
        raise ValueError(f"Task 4 injection log is missing column(s): {', '.join(sorted(missing))}")
    if episodes.empty:
        raise ValueError("Task 4 injection log contains no controlled perturbation episodes")
    if episodes["anomaly_event_id"].duplicated().any():
        raise ValueError("Task 4 injection log contains duplicate anomaly_event_id values")
    if not episodes["dataset_split"].eq("test").all():
        raise ValueError("Task 4 controlled perturbation episodes must be test-only")
    if not episodes["label"].eq(1).all():
        raise ValueError("Task 4 injection log contains a non-positive episode")
    if not episodes["label_provenance"].eq("controlled_synthetic_perturbation").all():
        raise ValueError("Task 4 injection log has unexpected label provenance")
    episodes["household_id"] = episodes["household_id"].astype(int)
    episodes["start_source_unix"] = episodes["start_source_unix"].astype(int)
    episodes["end_source_unix"] = episodes["end_source_unix"].astype(int)
    episodes["duration_seconds"] = episodes["duration_seconds"].astype(int)
    if (episodes["end_source_unix"] < episodes["start_source_unix"]).any():
        raise ValueError("Task 4 injection log has an episode ending before it starts")
    return episodes.sort_values(["household_id", "start_source_unix", "anomaly_event_id"]).reset_index(drop=True)


def pipe_values(value: Any) -> set[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return set()
    return {item for item in str(value).split("|") if item}


def reconcile_episode_ids(scored: pd.DataFrame, episodes: pd.DataFrame) -> None:
    dataset_ids: set[str] = set()
    for value in scored.loc[scored["anomaly_label"].eq(1), "anomaly_event_ids"]:
        dataset_ids.update(pipe_values(value))
    injection_ids = set(episodes["anomaly_event_id"].astype(str))
    if dataset_ids != injection_ids:
        missing_in_dataset = sorted(injection_ids - dataset_ids)
        unexpected_dataset_ids = sorted(dataset_ids - injection_ids)
        raise ValueError(
            "Controlled episode reconciliation failed; "
            f"missing={missing_in_dataset}, unexpected={unexpected_dataset_ids}"
        )


def episode_evaluation_rows(
    scored: pd.DataFrame,
    episodes: pd.DataFrame,
    detector: str,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    """Measure episode detection only from alert bins that overlap that episode.

    The delay convention is intentionally conservative: a five-minute bin is
    actionable only when the bin closes, not when it begins.
    """
    rows: list[dict[str, Any]] = []
    alert_column = f"{detector}_alert"
    if alert_column not in scored:
        raise ValueError(f"Episode evaluation is missing {alert_column}")
    for episode in episodes.itertuples(index=False):
        household = int(episode.household_id)
        event_id = str(episode.anomaly_event_id)
        household_rows = scored.loc[
            scored["household_id"].eq(household)
            & scored["dataset_split"].eq("test")
            & scored["feature_ready"].astype(bool)
        ].copy()
        matching = household_rows.loc[
            household_rows["anomaly_event_ids"].map(lambda value: event_id in pipe_values(value))
        ].sort_values("bin_start_epoch")
        alerts = matching.loc[matching[alert_column].astype(bool)]
        evaluable = not matching.empty
        detected = not alerts.empty
        first_bin_start = int(alerts.iloc[0]["bin_start_epoch"]) if detected else math.nan
        first_available = first_bin_start + args.bin_seconds if detected else math.nan
        delay = max(0, int(first_available) - int(episode.start_source_unix)) if detected else math.nan
        rows.append(
            {
                "detector": detector,
                "household_id": household,
                "evaluation_cohort": str(episode.evaluation_cohort),
                "anomaly_event_id": event_id,
                "anomaly_type": str(episode.anomaly_type),
                "episode_start_utc": str(episode.start_timestamp_utc),
                "episode_end_utc": str(episode.end_timestamp_utc),
                "episode_duration_seconds": int(episode.duration_seconds),
                "positive_event_rows": int(episode.event_row_count),
                "evaluable_positive_bins": int(len(matching)),
                "episode_evaluable": evaluable,
                "episode_detected": detected,
                "first_alert_bin_start_epoch": first_bin_start,
                "first_alert_available_epoch": first_available,
                "bin_close_detection_delay_seconds": delay,
                "metric_semantics": "held-out controlled perturbation; alert must overlap the injected episode",
            }
        )
    return rows


def episode_summary_frame(event_rows: pd.DataFrame) -> pd.DataFrame:
    """Summarise evaluability and detection without inventing zero-event results."""
    rows: list[dict[str, Any]] = []
    types = ["sustained_high", "sustained_low", "stuck_signal"]
    cohorts = sorted(event_rows["evaluation_cohort"].unique().tolist())
    detectors = sorted(event_rows["detector"].unique().tolist())
    for detector in detectors:
        for cohort in cohorts:
            subset_cohort = event_rows.loc[
                event_rows["detector"].eq(detector)
                & event_rows["evaluation_cohort"].eq(cohort)
            ]
            for anomaly_type in ["all_controlled_episodes", *types]:
                subset = (
                    subset_cohort
                    if anomaly_type == "all_controlled_episodes"
                    else subset_cohort.loc[subset_cohort["anomaly_type"].eq(anomaly_type)]
                )
                episode_count = int(len(subset))
                evaluable_count = int(subset["episode_evaluable"].sum()) if episode_count else 0
                detected_count = int(subset["episode_detected"].sum()) if episode_count else 0
                detected_delays = subset.loc[
                    subset["episode_detected"].astype(bool), "bin_close_detection_delay_seconds"
                ].dropna()
                rows.append(
                    {
                        "detector": detector,
                        "evaluation_cohort": cohort,
                        "scenario": anomaly_type,
                        "episode_count": episode_count,
                        "evaluable_episode_count": evaluable_count,
                        "detected_episode_count": detected_count,
                        "episode_detection_rate": (
                            float(detected_count / evaluable_count) if evaluable_count else math.nan
                        ),
                        "median_bin_close_detection_delay_seconds": (
                            float(detected_delays.median()) if not detected_delays.empty else math.nan
                        ),
                        "maximum_bin_close_detection_delay_seconds": (
                            float(detected_delays.max()) if not detected_delays.empty else math.nan
                        ),
                        "result_status": (
                            "not_applicable_zero_episodes" if episode_count == 0 else "reported"
                        ),
                        "metric_semantics": "held-out controlled perturbation episodes only",
                    }
                )
    return pd.DataFrame(rows)


def save_controlled_figures(scored: pd.DataFrame, output_dir: Path) -> list[str]:
    """Write minimal, paper-ready primary-cohort controlled-evaluation figures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    primary = scored.loc[
        scored["household_id"].isin(PRIMARY_HOUSEHOLDS)
        & scored["dataset_split"].eq("test")
        & scored["feature_ready"].astype(bool)
    ].copy()
    if primary.empty or primary["anomaly_label"].nunique() < 2:
        return []
    labels = primary["anomaly_label"].to_numpy(dtype=int)
    saved: list[str] = []

    alert_values = primary["isolation_forest_alert"].to_numpy(dtype=bool).astype(int)
    figure, axis = plt.subplots(figsize=(5.6, 4.4), constrained_layout=True)
    ConfusionMatrixDisplay(
        confusion_matrix(labels, alert_values, labels=[0, 1]),
        display_labels=["Unmodified baseline", "Controlled perturbation"],
    ).plot(ax=axis, colorbar=False, cmap="Blues")
    axis.set_title("Isolation Forest: primary cohort")
    path = output_dir / "controlled_primary_confusion_matrix_isolation_forest.png"
    figure.savefig(path, dpi=220)
    plt.close(figure)
    saved.append(path.name)

    figure, axis = plt.subplots(figsize=(6.0, 4.4), constrained_layout=True)
    for detector, label, colour in (
        ("isolation_forest", "Isolation Forest score", "#1f77b4"),
        ("robust_residual", "Causal robust-residual baseline", "#d62728"),
    ):
        precision, recall, _ = precision_recall_curve(
            labels, primary[f"{detector}_score"].to_numpy(dtype=float)
        )
        axis.plot(recall, precision, label=label, color=colour, linewidth=1.8)
    axis.set_xlabel("Controlled-label recall")
    axis.set_ylabel("Controlled-label precision")
    axis.set_title("Held-out controlled-perturbation precision-recall")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1.05)
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, fontsize=8)
    path = output_dir / "controlled_primary_precision_recall.png"
    figure.savefig(path, dpi=220)
    plt.close(figure)
    saved.append(path.name)

    figure, axis = plt.subplots(figsize=(6.0, 4.4), constrained_layout=True)
    for label, colour, group in (
        ("Unmodified baseline bins", "#666666", primary.loc[primary["anomaly_label"].eq(0)]),
        ("Controlled-perturbation bins", "#d62728", primary.loc[primary["anomaly_label"].eq(1)]),
    ):
        axis.hist(
            group["isolation_forest_score"].to_numpy(dtype=float),
            bins=35,
            alpha=0.58,
            density=True,
            label=label,
            color=colour,
        )
    axis.set_xlabel("Isolation Forest anomaly score (higher is more unusual)")
    axis.set_ylabel("Density")
    axis.set_title("Primary cohort: held-out score distribution")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, fontsize=8)
    path = output_dir / "controlled_primary_score_distribution.png"
    figure.savefig(path, dpi=220)
    plt.close(figure)
    saved.append(path.name)
    return saved


def write_frame(frame: pd.DataFrame, path: Path) -> None:
    """Write a reproducible CSV result table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.12g")


def file_hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)).replace("\\", "/"): sha256_file(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def format_metric(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "N/A" if not math.isfinite(numeric) else f"{numeric:.{digits}f}"


def create_staging_directory(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))


def write_static_evidence(
    evidence_dir: Path,
    manifest: dict[str, Any],
    args: argparse.Namespace,
    total_bins: int,
    total_feature_ready_bins: int,
) -> None:
    """Record the immutable semantic and leakage-control boundary of the run."""
    configuration = manifest["configuration"]
    contract_lines = [
        "# REFIT controlled-perturbation ML dataset contract",
        "",
        "## Scope",
        "",
        "This run evaluates detection of controlled synthetic perturbations created in Task 4.",
        "It is not an evaluation against observed household faults and does not use official REFIT appliance-level anomaly labels.",
        "",
        "## Frozen source and split protocol",
        "",
        f"- Input: `{args.dataset.as_posix()}`",
        f"- Task 4 input manifest: `{args.dataset_manifest.as_posix()}`",
        f"- Task 4 seed: `{configuration['seed']}`",
        "- Household profiles: " + ", ".join(f"H{household}" for household in configuration["households"]),
        f"- Chronological split: {configuration['train_fraction']:.0%} train, {configuration['validation_fraction']:.0%} validation, remaining test.",
        "- Controlled perturbations remain test-only. Train and validation are normal-only.",
        "- H1, H2 and H4 are primary. H3 and H11 are documented-solar-interference sensitivity homes and are not pooled into primary results.",
        "",
        "## Signal and quality gate",
        "",
        "The replay-compatible signal is synthetic_replay_energy_kwh with timestamp and interval duration.",
        "Exact interval energy is aggregated into UTC-aligned five-minute bins.",
        f"A bin is scoreable only with at least {args.minimum_coverage_seconds:g} seconds of coverage, one split/cohort, no source issue, no non-replayable interval, and no material gap.",
        "An unscoreable bin is a data-quality condition, not an anomaly class.",
        "",
        "## Counts from this run",
        "",
        f"- Binned records: {total_bins}",
        f"- Feature-ready records after causal warm-up: {total_feature_ready_bins}",
    ]
    feature_lines = [
        "# Feature specification and leakage controls",
        "",
        "## Model feature vector",
        "",
        *[f"{index}. `{feature}`" for index, feature in enumerate(MODEL_FEATURES, start=1)],
        "",
        "power_proxy_w = 3,600,000 × binned_replay_energy_kwh / coverage_seconds.",
        "For the current bin, the median, MAD, prior value, and variability use only the preceding six contiguous eligible bins.",
        "Stream state resets after a quality or continuity break; current data enter history only after their features are calculated.",
        "",
        "## Explicit exclusions",
        "",
        "Never model: labels, splits, cohorts, source identifiers, original/unmodified energy, raw aggregate power, source-quality flags, REFIT Issues, IQR diagnostics, or solar flags.",
        "Household identity selects a separately trained profile; it is not a learned feature.",
        "",
        "## Model and decision policy",
        "",
        "RobustScaler and IsolationForest are fit on chronological normal training features independently per household.",
        "Each threshold is a configured quantile of normal validation scores. Held-out labels never affect fitting or threshold selection.",
        "An alert requires three consecutive threshold exceedances in one continuous stream.",
        "Isolation Forest values are anomaly scores, not probabilities. The causal robust-residual detector is retained as an interpretable baseline; neither model is selected on held-out labels.",
    ]
    (evidence_dir / "dataset_contract.md").write_text("\n".join(contract_lines) + "\n", encoding="utf-8")
    (evidence_dir / "feature_specification.md").write_text("\n".join(feature_lines) + "\n", encoding="utf-8")


def write_evaluation_summary(
    evidence_dir: Path,
    cohort_metrics: pd.DataFrame,
    scenario_metrics: pd.DataFrame,
    figure_names: Sequence[str],
) -> None:
    """Create a short, data-derived narrative without unsupported claims."""
    lines = [
        "# REFIT controlled-perturbation evaluation summary",
        "",
        "## Interpretation boundary",
        "",
        "Every value measures held-out controlled-perturbation detection on the Task 4 benchmark.",
        "It is not observed real-world fault detection accuracy or a generalisation claim for all REFIT homes.",
        "",
        "## Primary-cohort row-level results",
        "",
        "Thresholds were frozen from normal validation scores before held-out evaluation.",
        "",
        "| Detector | Controlled precision | Controlled recall | Controlled F1 | PR-AUC | ROC-AUC | False alerts / 10k normal bins |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    primary = cohort_metrics.loc[cohort_metrics["scope"].eq("primary")]
    for row in primary.itertuples(index=False):
        lines.append(
            "| {detector} | {precision} | {recall} | {f1} | {pr_auc} | {roc_auc} | {false_alerts} |".format(
                detector=row.detector,
                precision=format_metric(row.controlled_precision),
                recall=format_metric(row.controlled_recall),
                f1=format_metric(row.controlled_f1),
                pr_auc=format_metric(row.controlled_pr_auc),
                roc_auc=format_metric(row.controlled_roc_auc),
                false_alerts=format_metric(row.false_alerts_per_10k_normal_bins, 2),
            )
        )
    lines.extend(
        [
            "",
            "## Episode-level results",
            "",
            "Episode detection needs an alert bin overlapping the recorded controlled episode.",
            "Delay is measured at the close of the five-minute alert bin. A zero-event scenario is marked not applicable.",
            "",
            "| Cohort | Detector | Scenario | Episodes | Evaluable | Detected | Detection rate | Median delay (s) |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in scenario_metrics.itertuples(index=False):
        lines.append(
            "| {cohort} | {detector} | {scenario} | {episodes} | {evaluable} | {detected} | {rate} | {delay} |".format(
                cohort=row.evaluation_cohort,
                detector=row.detector,
                scenario=row.scenario,
                episodes=row.episode_count,
                evaluable=row.evaluable_episode_count,
                detected=row.detected_episode_count,
                rate=format_metric(row.episode_detection_rate),
                delay=format_metric(row.median_bin_close_detection_delay_seconds, 1),
            )
        )
    lines.extend(
        [
            "",
            "## Evidence files",
            "",
            "- per_household_metrics.csv and cohort_metrics.csv: test-only controlled-label bin metrics.",
            "- event_level_metrics.csv and per_scenario_metrics.csv: episode reconciliation and detection measures.",
            "- validation_thresholds.csv: validation-only threshold calibration.",
            "- model_comparison.csv: pre-specified Isolation Forest and causal baseline comparison; no selection on test labels.",
            "- model_manifest.json: frozen input hashes, parameters, and output hashes.",
            "",
            "Figures generated: " + (", ".join(figure_names) if figure_names else "none"),
            "",
            "H3/H11 sensitivity results remain separate in the CSV outputs and are not evidence for the primary-cohort conclusion.",
        ]
    )
    (evidence_dir / "evaluation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    validate_args(args)
    task4_manifest = load_task4_manifest(args.dataset_manifest, args.dataset)
    episodes = load_injection_log(args.injection_log)
    expected_households = {int(value) for value in task4_manifest["configuration"]["households"]}
    declared_households = PRIMARY_HOUSEHOLDS | SENSITIVITY_HOUSEHOLDS
    if expected_households != declared_households:
        raise ValueError(f"Unexpected Task 4 household configuration: {sorted(expected_households)}")
    if set(episodes["household_id"]) != expected_households:
        raise ValueError("Injection log and Task 4 household configuration do not reconcile")

    all_binned: list[BinRecord] = []
    frames_by_household: dict[int, pd.DataFrame] = {}
    results_by_household: dict[int, HouseholdTrainingResult] = {}
    seen_households: set[int] = set()
    for household_id, events in iter_household_events(args.dataset):
        if household_id not in expected_households:
            raise ValueError(f"Unexpected household H{household_id} in Task 4 dataset")
        if household_id in seen_households:
            raise ValueError(f"Household H{household_id} was encountered twice")
        validate_household_splits(events, task4_manifest)
        binned = build_bins(events, args)
        if any(
            record.anomaly_label
            for record in binned
            if record.dataset_split in {"train", "validation"}
        ):
            raise ValueError(f"Binning moved a positive label outside test for H{household_id}")
        scale_floor = calculate_scale_floor(binned, args)
        features = build_feature_frame(binned, scale_floor, args)
        result = fit_household_detector(features, scale_floor, args)
        frames_by_household[household_id] = add_scores_and_persistence(features, result, args)
        results_by_household[household_id] = result
        all_binned.extend(binned)
        seen_households.add(household_id)
    if seen_households != expected_households:
        raise ValueError(f"Dataset households do not match expected cohort: {sorted(seen_households)}")

    scored = pd.concat(
        [frames_by_household[household_id] for household_id in sorted(frames_by_household)],
        ignore_index=True,
    )
    reconcile_episode_ids(scored, episodes)
    household_metric_rows: list[dict[str, Any]] = []
    cohort_metric_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for detector in ("isolation_forest", "robust_residual"):
        for household_id in sorted(frames_by_household):
            household_metric_rows.append(
                controlled_row_metrics(
                    frames_by_household[household_id], detector, "household", f"H{household_id}"
                )
            )
        for cohort_name, households in (
            ("primary", PRIMARY_HOUSEHOLDS),
            ("sensitivity_documented_solar_interference", SENSITIVITY_HOUSEHOLDS),
        ):
            cohort_frame = scored.loc[scored["household_id"].isin(households)]
            cohort_metric_rows.append(
                controlled_row_metrics(cohort_frame, detector, "cohort", cohort_name)
            )
        event_rows.extend(episode_evaluation_rows(scored, episodes, detector, args))

    household_metrics = pd.DataFrame(household_metric_rows)
    cohort_metrics = pd.DataFrame(cohort_metric_rows)
    event_metrics = pd.DataFrame(event_rows)
    scenario_metrics = episode_summary_frame(event_metrics)
    threshold_rows: list[dict[str, Any]] = []
    for result in results_by_household.values():
        for detector, threshold in (
            ("isolation_forest", result.threshold_isolation_forest),
            ("robust_residual", result.threshold_robust_residual),
        ):
            threshold_rows.append(
                {
                    "household_id": result.household_id,
                    "evaluation_cohort": result.cohort,
                    "detector": detector,
                    "validation_score_quantile": args.validation_score_quantile,
                    "threshold": threshold,
                    "normal_train_feature_rows": result.train_rows,
                    "normal_validation_feature_rows": result.validation_rows,
                    "held_out_test_feature_rows": result.test_rows,
                    "scale_floor_w": result.scale_floor_w,
                    "decision_policy": f"{args.persistence_bins} consecutive candidate bins",
                }
            )
    thresholds = pd.DataFrame(threshold_rows).sort_values(["household_id", "detector"])
    model_comparison = cohort_metrics.copy()
    model_comparison["selection_policy"] = "No detector selected or tuned on held-out controlled labels"

    model_stage = create_staging_directory(args.model_dir)
    evidence_stage = create_staging_directory(args.evidence_dir)
    run_stage = create_staging_directory(args.run_dir)
    stages = [(model_stage, args.model_dir), (evidence_stage, args.evidence_dir), (run_stage, args.run_dir)]
    try:
        binned_frame = pd.DataFrame([record.__dict__ for record in all_binned])
        write_frame(quality_report_frame(all_binned), evidence_stage / "bin_quality_report.csv")
        write_frame(thresholds, evidence_stage / "validation_thresholds.csv")
        write_frame(household_metrics, evidence_stage / "per_household_metrics.csv")
        write_frame(cohort_metrics, evidence_stage / "cohort_metrics.csv")
        write_frame(scenario_metrics, evidence_stage / "per_scenario_metrics.csv")
        write_frame(event_metrics, evidence_stage / "event_level_metrics.csv")
        write_frame(model_comparison, evidence_stage / "model_comparison.csv")
        write_frame(binned_frame, run_stage / "binned_records.csv")
        write_frame(scored.loc[scored["dataset_split"].eq("test")].copy(), run_stage / "test_predictions.csv")
        write_frame(scored, run_stage / "all_scored_bins.csv")
        write_static_evidence(
            evidence_stage,
            task4_manifest,
            args,
            total_bins=len(binned_frame),
            total_feature_ready_bins=int(scored["feature_ready"].sum()),
        )
        figure_names = save_controlled_figures(scored, evidence_stage)
        write_evaluation_summary(evidence_stage, cohort_metrics, scenario_metrics, figure_names)

        model_metadata = {
            "artifact_schema": ARTIFACT_SCHEMA,
            "training_script": str(Path(__file__).relative_to(Path(__file__).resolve().parents[2])),
            "script_version": SCRIPT_VERSION,
            "seed": args.seed,
            "semantic_boundary": {
                "evaluation_name": "controlled_perturbation_detection",
                "not_real_world_fault_accuracy": True,
                "official_refit_anomaly_labels_used": False,
                "test_labels_used_for_fit_or_threshold": False,
                "legacy_service_artifact_replaced": False,
            },
            "input_files": {
                "anomaly_dataset": {"path": str(args.dataset), "sha256": sha256_file(args.dataset)},
                "task4_manifest": {"path": str(args.dataset_manifest), "sha256": sha256_file(args.dataset_manifest)},
                "injection_log": {"path": str(args.injection_log), "sha256": sha256_file(args.injection_log)},
            },
            "feature_names": MODEL_FEATURES,
            "binning": {
                "bin_seconds": args.bin_seconds,
                "minimum_coverage_seconds": args.minimum_coverage_seconds,
                "history_bins": args.history_bins,
                "history_is_past_only": True,
                "persistence_bins": args.persistence_bins,
            },
            "cohorts": {
                "primary_households": sorted(PRIMARY_HOUSEHOLDS),
                "sensitivity_households": sorted(SENSITIVITY_HOUSEHOLDS),
            },
            "household_models": {
                str(household_id): {
                    "cohort": result.cohort,
                    "model_parameters": result.model_parameters,
                    "threshold_isolation_forest": result.threshold_isolation_forest,
                    "threshold_robust_residual": result.threshold_robust_residual,
                    "scale_floor_w": result.scale_floor_w,
                    "normal_train_feature_rows": result.train_rows,
                    "normal_validation_feature_rows": result.validation_rows,
                    "held_out_test_feature_rows": result.test_rows,
                }
                for household_id, result in sorted(results_by_household.items())
            },
        }
        write_json(model_stage / "model_metadata.json", model_metadata)
        joblib.dump(
            {
                "artifact_schema": ARTIFACT_SCHEMA,
                "feature_names": MODEL_FEATURES,
                "models_by_household": {
                    str(household_id): result.model
                    for household_id, result in sorted(results_by_household.items())
                },
                "metadata": model_metadata,
            },
            model_stage / "isolation_forest_by_household.joblib",
        )
        training_config = {
            "script_version": SCRIPT_VERSION,
            "seed": args.seed,
            "arguments": {
                key: (str(value) if isinstance(value, Path) else value)
                for key, value in vars(args).items()
            },
            "python_version": sys.version,
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "scikit_learn_version": sklearn.__version__,
        }
        write_json(evidence_stage / "training_config.json", training_config)
        run_manifest = {
            "artifact_schema": ARTIFACT_SCHEMA,
            "script_version": SCRIPT_VERSION,
            "input_sha256": model_metadata["input_files"],
            "output_sha256": {
                "model": file_hashes(model_stage),
                "evidence_before_manifest": file_hashes(evidence_stage),
                "run": file_hashes(run_stage),
            },
            "result_boundary": "controlled synthetic perturbation detection only",
        }
        write_json(evidence_stage / "model_manifest.json", run_manifest)
        for stage, target in stages:
            stage.replace(target)
    except Exception:
        for stage, _target in stages:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)
        raise

    primary_results = cohort_metrics.loc[cohort_metrics["scope"].eq("primary")]
    print("PASS: trained isolated REFIT controlled-perturbation benchmark artifacts")
    print(f"  binned records: {len(all_binned):,}")
    print(f"  feature-ready records: {int(scored['feature_ready'].sum()):,}")
    print(f"  held-out controlled episodes: {len(episodes):,}")
    for row in primary_results.itertuples(index=False):
        print(
            f"  primary {row.detector}: F1={format_metric(row.controlled_f1)}, "
            f"precision={format_metric(row.controlled_precision)}, "
            f"recall={format_metric(row.controlled_recall)}"
        )
    print(f"  model artifact: {args.model_dir}")
    print(f"  evidence: {args.evidence_dir}")
    print(f"  scored-bin run data: {args.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
