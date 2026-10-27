#!/usr/bin/env python3
"""Build an auditable controlled-perturbation evaluation dataset from Task 2 REFIT events.

This script is deliberately conservative.  It does not alter the frozen Task 2
source dataset, use REFIT's ``Issues`` field as a label, or claim that injected
events are genuine household faults.  The generated labels describe only
controlled synthetic perturbations applied to real recorded aggregate-load
baseline events.  They are suitable for a later *controlled-perturbation*
evaluation, not for reporting real-world anomaly-detection accuracy.

Why this exists
---------------
The selected Task 1/2 cohort is H1, H2, H3, H4 and H11.  The University of
Strathclyde appliance-level REFIT anomaly resource covers H1, H10, H16, H18
and H20, and its exact local schema/timestamp mapping was not auditable in this
environment.  It is therefore not a five-house aggregate-event ground truth.

Methodology safeguards
----------------------
* Each household is split chronologically before any perturbation is selected.
  The default train and validation partitions remain unmodified; only the
  held-out test partition receives controlled perturbations.
* H1/H2/H4 are marked as the primary cohort.  H3/H11 are retained as a clearly
  marked solar-interference sensitivity cohort, never silently pooled.
* Episodes request 5--15 minutes of continuous replayable events (with at
  most one final <=16-second sampling endpoint), are kept
  away from source-quality-marked events and material timing gaps, and never
  overlap or cross a split boundary.
* Magnitudes are calibrated from training-partition quantiles for the same
  household.  Energy remains non-negative, and the original interval-energy
  field remains untouched in the generated copy.
* A fixed seed, complete episode log, source hash and output hashes make the
  result reproducible.

The input unit is ``estimated_interval_energy_kwh``: a Task 2 trapezoidal
estimate derived from recorded REFIT active power.  It is not a direct meter
increment.  See ``data/refit/processed/preprocessing_summary.md``.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import random
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


SCRIPT_VERSION = "1.0.0"
DEFAULT_SEED = 20261009
PRIMARY_HOUSEHOLDS = {1, 2, 4}
SOLAR_SENSITIVITY_HOUSEHOLDS = {3, 11}
SUPPORTED_TYPES = ("sustained_high", "sustained_low", "stuck_signal")
MAX_CONTIGUOUS_GAP_SECONDS = 16
EPSILON = 1e-15


@dataclass
class Event:
    """One frozen Task 2 output event plus Task 4 derived state."""

    row: dict[str, str]
    household_id: int
    timestamp_epoch: int
    energy_kwh: float
    row_index: int
    split: str = ""
    synthetic_energy_kwh: float = 0.0
    anomaly_label: int = 0
    anomaly_type: str = "normal"
    anomaly_event_id: str = ""

    def __post_init__(self) -> None:
        self.synthetic_energy_kwh = self.energy_kwh


@dataclass(frozen=True)
class HouseholdCalibration:
    household_id: int
    train_row_count: int
    p10_kwh: float
    p50_kwh: float
    p90_kwh: float
    p95_kwh: float
    p995_kwh: float


@dataclass(frozen=True)
class EpisodeCandidate:
    start_index: int
    end_index: int
    actual_duration_seconds: int
    timestamps: tuple[int, int]

    @property
    def row_count(self) -> int:
        return self.end_index - self.start_index + 1


@dataclass(frozen=True)
class EpisodeTransformation:
    anomaly_type: str
    modified_values: tuple[float, ...]
    magnitude_parameter: dict[str, Any]


@dataclass(frozen=True)
class ScenarioControls:
    """Explicit, CLI-configurable magnitude controls for each synthetic scenario."""

    high_multipliers: tuple[float, ...]
    low_multipliers: tuple[float, ...]
    stuck_min_relative_spread: float


@dataclass
class HouseholdResult:
    household_id: int
    cohort: str
    total_rows: int
    split_counts: dict[str, int]
    target_test_anomalous_rows: int
    achieved_test_anomalous_rows: int
    episodes: list[dict[str, Any]] = field(default_factory=list)
    calibration: HouseholdCalibration | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a chronologically held-out, controlled synthetic-perturbation "
            "dataset from the frozen Task 2 REFIT interval-energy events."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/refit/processed/cleaned_dataset.csv"),
        help="Frozen Task 2 cleaned dataset; it is read only.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/refit/labeled-verified"),
        help="New output directory. It must not already exist.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Fixed generation seed.")
    parser.add_argument(
        "--train-fraction",
        type=float,
        default=0.70,
        help="Chronological household fraction reserved for unmodified training.",
    )
    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=0.15,
        help="Chronological household fraction reserved for unmodified validation/calibration.",
    )
    parser.add_argument(
        "--test-anomaly-rate",
        type=float,
        default=0.03,
        help="Target fraction of each household's held-out test rows labelled as synthetic perturbations.",
    )
    parser.add_argument(
        "--min-duration-seconds",
        type=int,
        default=300,
        help="Minimum continuous perturbation episode duration (default: 5 minutes).",
    )
    parser.add_argument(
        "--max-duration-seconds",
        type=int,
        default=900,
        help="Maximum continuous perturbation episode duration (default: 15 minutes).",
    )
    parser.add_argument(
        "--guard-seconds",
        type=int,
        default=300,
        help="Exclusion buffer around source-quality markers, timing gaps, and other injected episodes.",
    )
    parser.add_argument(
        "--anomaly-types",
        default=",".join(SUPPORTED_TYPES),
        help="Comma-separated subset of sustained_high,sustained_low,stuck_signal.",
    )
    parser.add_argument(
        "--high-multipliers",
        default="1.40,1.60,1.80,2.00",
        help="Comma-separated sustained-high multipliers; every value must be > 1.",
    )
    parser.add_argument(
        "--low-multipliers",
        default="0.25,0.40,0.55,0.70",
        help="Comma-separated sustained-low multipliers; every value must be in (0, 1).",
    )
    parser.add_argument(
        "--stuck-min-relative-spread",
        type=float,
        default=0.35,
        help="Minimum (max-min)/mean required before a stuck-signal episode can be injected.",
    )
    parser.add_argument(
        "--households",
        default="1,2,3,4,11",
        help="Comma-separated household IDs. Default is the frozen Task 1/2 cohort.",
    )
    parser.add_argument(
        "--max-attempts-per-household",
        type=int,
        default=25000,
        help="Fail safely if this many episode candidates cannot meet a household target.",
    )
    return parser.parse_args()


def parse_id_list(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise ValueError("--households must be a comma-separated list of integer IDs") from exc
    if not parsed:
        raise ValueError("--households cannot be empty")
    return parsed


def parse_types(value: str) -> tuple[str, ...]:
    parsed = tuple(item.strip() for item in value.split(",") if item.strip())
    if not parsed:
        raise ValueError("--anomaly-types cannot be empty")
    unknown = set(parsed) - set(SUPPORTED_TYPES)
    if unknown:
        raise ValueError(f"Unsupported anomaly type(s): {', '.join(sorted(unknown))}")
    return parsed


def parse_multiplier_list(value: str, name: str, predicate: Any) -> tuple[float, ...]:
    try:
        parsed = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a comma-separated list of finite numbers") from exc
    if not parsed or any(not math.isfinite(item) or not predicate(item) for item in parsed):
        raise ValueError(f"{name} contains an invalid multiplier")
    return parsed


def controls_from_args(args: argparse.Namespace) -> ScenarioControls:
    return ScenarioControls(
        high_multipliers=parse_multiplier_list(args.high_multipliers, "--high-multipliers", lambda item: item > 1.0),
        low_multipliers=parse_multiplier_list(args.low_multipliers, "--low-multipliers", lambda item: 0.0 < item < 1.0),
        stuck_min_relative_spread=args.stuck_min_relative_spread,
    )


def validate_args(args: argparse.Namespace) -> tuple[tuple[int, ...], tuple[str, ...], ScenarioControls]:
    households = parse_id_list(args.households)
    anomaly_types = parse_types(args.anomaly_types)
    if not args.input.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input}")
    if args.output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {args.output_dir}. "
            "Choose a new --output-dir; this script never overwrites generated evidence."
        )
    if not (0.0 < args.train_fraction < 1.0):
        raise ValueError("--train-fraction must be in (0, 1)")
    if not (0.0 <= args.validation_fraction < 1.0):
        raise ValueError("--validation-fraction must be in [0, 1)")
    if args.train_fraction + args.validation_fraction >= 1.0:
        raise ValueError("train + validation fractions must leave a non-empty chronological test partition")
    if not (0.0 <= args.test_anomaly_rate < 1.0):
        raise ValueError("--test-anomaly-rate must be in [0, 1)")
    if args.min_duration_seconds < 300:
        raise ValueError("--min-duration-seconds must be at least 300 seconds (five minutes)")
    if args.max_duration_seconds < args.min_duration_seconds:
        raise ValueError("--max-duration-seconds must be >= --min-duration-seconds")
    if args.max_duration_seconds - args.min_duration_seconds < MAX_CONTIGUOUS_GAP_SECONDS:
        raise ValueError(
            "--max-duration-seconds must exceed --min-duration-seconds by at least 16 seconds "
            "so a continuous sampled endpoint can satisfy the minimum duration without exceeding the cap"
        )
    if args.guard_seconds < 0:
        raise ValueError("--guard-seconds must be non-negative")
    if args.max_attempts_per_household < 1:
        raise ValueError("--max-attempts-per-household must be >= 1")
    controls = controls_from_args(args)
    if not math.isfinite(controls.stuck_min_relative_spread) or controls.stuck_min_relative_spread <= 0:
        raise ValueError("--stuck-min-relative-spread must be finite and > 0")
    return households, anomaly_types, controls


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def as_int(value: str, field: str, row_number: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: invalid integer {field}={value!r}") from exc
    return parsed


def as_nonnegative_float(value: str, field: str, row_number: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: invalid float {field}={value!r}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"Row {row_number}: {field} must be finite and non-negative, got {value!r}")
    return parsed


def boolish(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def float_text(value: float) -> str:
    """Round-trip representation, without display rounding of generated energy."""
    return repr(value)


def quantile_linear(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a quantile from no values")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("Quantile probability must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def cohort_for(household_id: int) -> str:
    if household_id in PRIMARY_HOUSEHOLDS:
        return "primary_no_documented_solar_interference"
    if household_id in SOLAR_SENSITIVITY_HOUSEHOLDS:
        return "sensitivity_documented_solar_interference"
    return "additional_requested_household"


def read_source_fields(input_path: Path) -> list[str]:
    """Read and validate the immutable Task 2 CSV schema without loading rows."""
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        required = {
            "household_id",
            "source_unix",
            "estimated_interval_energy_kwh",
            "source_quality_issue_flag",
            "interval_seconds",
        }
        missing = required - set(fields)
        if missing:
            raise ValueError(f"Input is missing Task 2 column(s): {', '.join(sorted(missing))}")
    return fields


def load_one_household(input_path: Path, household_id: int) -> list[Event]:
    """Load one household at a time to keep the 795k-row source memory-safe.

    The complete input is intentionally re-scanned for each selected household.
    That adds disk I/O but prevents the generator from holding five full
    CSV-record dictionaries in memory at once. It preserves chronology and
    deterministic output while being safer for a student workstation.
    """
    events: list[Event] = []
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            current_household_id = as_int(row.get("household_id", ""), "household_id", row_number)
            if current_household_id != household_id:
                continue
            timestamp_epoch = as_int(row.get("source_unix", ""), "source_unix", row_number)
            energy_kwh = as_nonnegative_float(
                row.get("estimated_interval_energy_kwh", ""),
                "estimated_interval_energy_kwh",
                row_number,
            )
            if events and timestamp_epoch <= events[-1].timestamp_epoch:
                raise ValueError(
                    f"Input chronology is not strictly increasing for household {household_id}: "
                    f"{timestamp_epoch} after {events[-1].timestamp_epoch}"
                )
            events.append(
                Event(
                    row=row,
                    household_id=household_id,
                    timestamp_epoch=timestamp_epoch,
                    energy_kwh=energy_kwh,
                    row_index=len(events),
                )
            )
    if not events:
        raise ValueError(f"Requested household {household_id} is not present in input")
    return events


def assign_chronological_splits(events: list[Event], train_fraction: float, validation_fraction: float) -> dict[str, int]:
    """Assign train/validation/test by source time order, never random row sampling."""
    count = len(events)
    train_end = int(math.floor(count * train_fraction))
    validation_end = int(math.floor(count * (train_fraction + validation_fraction)))
    if train_end < 1 or validation_end <= train_end or validation_end >= count:
        raise ValueError(
            f"Household {events[0].household_id if events else '?'} cannot support the requested chronological split"
        )
    for index, event in enumerate(events):
        event.split = "train" if index < train_end else "validation" if index < validation_end else "test"
    return {"train": train_end, "validation": validation_end - train_end, "test": count - validation_end}


def calibration_from_train(events: list[Event]) -> HouseholdCalibration:
    train_values = [event.energy_kwh for event in events if event.split == "train"]
    household_id = events[0].household_id
    return HouseholdCalibration(
        household_id=household_id,
        train_row_count=len(train_values),
        p10_kwh=quantile_linear(train_values, 0.10),
        p50_kwh=quantile_linear(train_values, 0.50),
        p90_kwh=quantile_linear(train_values, 0.90),
        p95_kwh=quantile_linear(train_values, 0.95),
        p995_kwh=quantile_linear(train_values, 0.995),
    )


def bad_timestamps(events: list[Event]) -> list[int]:
    """Return source-quality markers / material timing discontinuities, never labels."""
    bad: list[int] = []
    previous: Event | None = None
    for event in events:
        if boolish(event.row.get("source_quality_issue_flag", "")):
            bad.append(event.timestamp_epoch)
        if previous is not None and event.timestamp_epoch - previous.timestamp_epoch > MAX_CONTIGUOUS_GAP_SECONDS:
            bad.extend((previous.timestamp_epoch, event.timestamp_epoch))
        previous = event
    return sorted(set(bad))


def timestamp_near_any(timestamp_values: Sequence[int], left: int, right: int) -> bool:
    """True if a sorted timestamp list has a member in inclusive [left, right]."""
    position = bisect.bisect_left(timestamp_values, left)
    return position < len(timestamp_values) and timestamp_values[position] <= right


def build_candidate(
    events: list[Event],
    start_index: int,
    requested_duration_seconds: int,
    min_duration_seconds: int,
    max_duration_seconds: int,
    bad_times: Sequence[int],
    guard_seconds: int,
) -> EpisodeCandidate | None:
    """Build a continuous, quality-clear held-out episode starting at one event."""
    if start_index >= len(events) or events[start_index].split != "test":
        return None
    start = events[start_index]
    if boolish(start.row.get("source_quality_issue_flag", "")) or not boolish(start.row.get("is_replayable", "")):
        return None
    if timestamp_near_any(bad_times, start.timestamp_epoch - guard_seconds, start.timestamp_epoch + guard_seconds):
        return None

    cutoff = start.timestamp_epoch + requested_duration_seconds
    end_index = start_index
    previous_timestamp = start.timestamp_epoch
    for index in range(start_index + 1, len(events)):
        event = events[index]
        if event.split != "test":
            return None
        if boolish(event.row.get("source_quality_issue_flag", "")) or not boolish(event.row.get("is_replayable", "")):
            return None
        if event.timestamp_epoch - previous_timestamp > MAX_CONTIGUOUS_GAP_SECONDS:
            return None
        if event.timestamp_epoch > cutoff:
            # Include the first continuously observed endpoint after the
            # requested duration. With nominal 8-second REFIT sampling this
            # prevents a nominal five-minute episode from stopping at 296 s.
            # Request durations are chosen at least one admissible gap below
            # the configured maximum; the cap below is nevertheless enforced.
            end_index = index
            previous_timestamp = event.timestamp_epoch
            break
        end_index = index
        previous_timestamp = event.timestamp_epoch

    end = events[end_index]
    actual_duration = end.timestamp_epoch - start.timestamp_epoch
    if actual_duration < min_duration_seconds or actual_duration > max_duration_seconds:
        return None
    if timestamp_near_any(
        bad_times,
        start.timestamp_epoch - guard_seconds,
        end.timestamp_epoch + guard_seconds,
    ):
        return None
    return EpisodeCandidate(
        start_index=start_index,
        end_index=end_index,
        actual_duration_seconds=actual_duration,
        timestamps=(start.timestamp_epoch, end.timestamp_epoch),
    )


def transform_values(
    anomaly_type: str,
    original_values: Sequence[float],
    calibration: HouseholdCalibration,
    controls: ScenarioControls,
    rng: random.Random,
) -> EpisodeTransformation | None:
    """Return a physically interpretable, non-negative perturbation or None.

    The quantiles are calculated from the chronological *training* partition
    only.  The high-load ceiling deliberately stays within the observed
    training 99.5th percentile; this is a controlled signal perturbation, not
    an attempt to invent an impossible household load.
    """
    if not original_values or any(value < 0 or not math.isfinite(value) for value in original_values):
        return None

    if anomaly_type == "sustained_high":
        multiplier = rng.choice(controls.high_multipliers)
        cap = calibration.p995_kwh
        if cap <= EPSILON:
            return None
        # Avoid flattening at the cap and reject near-zero/no-op signal runs.
        if any(value <= EPSILON or value * multiplier >= cap * (1.0 - 1e-12) for value in original_values):
            return None
        modified = tuple(value * multiplier for value in original_values)
        return EpisodeTransformation(
            anomaly_type=anomaly_type,
            modified_values=modified,
            magnitude_parameter={
                "multiplier": multiplier,
                "upper_cap_reference": "training_p995_kwh",
                "upper_cap_kwh": cap,
            },
        )

    if anomaly_type == "sustained_low":
        multiplier = rng.choice(controls.low_multipliers)
        if sum(original_values) / len(original_values) < max(calibration.p50_kwh, EPSILON):
            return None
        if any(value <= EPSILON for value in original_values):
            return None
        modified = tuple(value * multiplier for value in original_values)
        return EpisodeTransformation(
            anomaly_type=anomaly_type,
            modified_values=modified,
            magnitude_parameter={"multiplier": multiplier, "lower_bound_kwh": 0.0},
        )

    if anomaly_type == "stuck_signal":
        held_value = original_values[0]
        if held_value <= EPSILON:
            return None
        mean = sum(original_values) / len(original_values)
        spread = max(original_values) - min(original_values)
        if mean <= EPSILON or spread / mean < controls.stuck_min_relative_spread:
            return None
        modified = tuple(held_value for _ in original_values)
        change = sum(abs(after - before) for before, after in zip(original_values, modified))
        if change <= EPSILON:
            return None
        return EpisodeTransformation(
            anomaly_type=anomaly_type,
            modified_values=modified,
            magnitude_parameter={
                "held_value_kwh": held_value,
                "minimum_relative_spread": controls.stuck_min_relative_spread,
                "mechanism": "constant_output_over_continuous_episode",
            },
        )

    raise ValueError(f"Unsupported anomaly type {anomaly_type!r}")


def window_collides(candidate: EpisodeCandidate, protected_windows: Sequence[tuple[int, int]], guard_seconds: int) -> bool:
    candidate_left = candidate.timestamps[0] - guard_seconds
    candidate_right = candidate.timestamps[1] + guard_seconds
    return any(candidate_left <= protected_right and candidate_right >= protected_left for protected_left, protected_right in protected_windows)


def inject_household(
    events: list[Event],
    calibration: HouseholdCalibration,
    target_rate: float,
    min_duration_seconds: int,
    max_duration_seconds: int,
    guard_seconds: int,
    anomaly_types: Sequence[str],
    controls: ScenarioControls,
    base_seed: int,
    max_attempts: int,
) -> HouseholdResult:
    """Inject sparse episodes exclusively in the chronological test partition."""
    household_id = events[0].household_id
    split_counts = dict(Counter(event.split for event in events))
    test_indices = [index for index, event in enumerate(events) if event.split == "test"]
    if not test_indices:
        raise ValueError(f"Household {household_id} has no held-out test events")
    target_rows = int(round(len(test_indices) * target_rate))
    household_seed = base_seed + household_id * 100_003
    rng = random.Random(household_seed)
    result = HouseholdResult(
        household_id=household_id,
        cohort=cohort_for(household_id),
        total_rows=len(events),
        split_counts=split_counts,
        target_test_anomalous_rows=target_rows,
        achieved_test_anomalous_rows=0,
        calibration=calibration,
    )
    if target_rows == 0:
        return result

    bad_times = bad_timestamps(events)
    protected_windows: list[tuple[int, int]] = []
    attempts = 0
    event_sequence = 0
    while result.achieved_test_anomalous_rows < target_rows and attempts < max_attempts:
        attempts += 1
        start_index = rng.choice(test_indices)
        requested_duration = rng.randint(
            min_duration_seconds,
            max_duration_seconds - MAX_CONTIGUOUS_GAP_SECONDS,
        )
        candidate = build_candidate(
            events=events,
            start_index=start_index,
            requested_duration_seconds=requested_duration,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
            bad_times=bad_times,
            guard_seconds=guard_seconds,
        )
        if candidate is None or window_collides(candidate, protected_windows, guard_seconds):
            continue
        anomaly_type = rng.choice(tuple(anomaly_types))
        original_values = [events[index].energy_kwh for index in range(candidate.start_index, candidate.end_index + 1)]
        transformation = transform_values(anomaly_type, original_values, calibration, controls, rng)
        if transformation is None:
            continue
        if len(transformation.modified_values) != len(original_values):
            raise AssertionError("Transformation length mismatch")
        if any(value < -EPSILON or not math.isfinite(value) for value in transformation.modified_values):
            raise AssertionError("Generated non-finite or negative energy")
        if any(abs(after - before) <= EPSILON for before, after in zip(original_values, transformation.modified_values)):
            continue

        event_sequence += 1
        anomaly_event_id = f"H{household_id:02d}_E{event_sequence:03d}"
        for offset, event_index in enumerate(range(candidate.start_index, candidate.end_index + 1)):
            event = events[event_index]
            if event.split != "test" or event.anomaly_label != 0:
                raise AssertionError("Attempted to contaminate a non-test or already-labelled event")
            event.synthetic_energy_kwh = transformation.modified_values[offset]
            event.anomaly_label = 1
            event.anomaly_type = transformation.anomaly_type
            event.anomaly_event_id = anomaly_event_id

        original_sum = sum(original_values)
        modified_sum = sum(transformation.modified_values)
        absolute_change = modified_sum - original_sum
        result.achieved_test_anomalous_rows += candidate.row_count
        protected_windows.append(candidate.timestamps)
        start_event = events[candidate.start_index]
        end_event = events[candidate.end_index]
        result.episodes.append(
            {
                "household_id": household_id,
                "evaluation_cohort": result.cohort,
                "anomaly_event_id": anomaly_event_id,
                "dataset_split": "test",
                "start_source_row_number": start_event.row.get("source_row_number", ""),
                "end_source_row_number": end_event.row.get("source_row_number", ""),
                "start_source_unix": start_event.timestamp_epoch,
                "end_source_unix": end_event.timestamp_epoch,
                "start_timestamp_utc": start_event.row.get("timestamp_utc", ""),
                "end_timestamp_utc": end_event.row.get("timestamp_utc", ""),
                "anomaly_type": transformation.anomaly_type,
                "duration_seconds": candidate.actual_duration_seconds,
                "event_row_count": candidate.row_count,
                "original_energy_kwh_sum": original_sum,
                "modified_energy_kwh_sum": modified_sum,
                "absolute_energy_change_kwh": absolute_change,
                "relative_energy_change": None if abs(original_sum) <= EPSILON else absolute_change / original_sum,
                "magnitude_parameter_json": json.dumps(transformation.magnitude_parameter, sort_keys=True),
                "label": 1,
                "label_provenance": "controlled_synthetic_perturbation",
                "random_seed": base_seed,
                "household_seed": household_seed,
                "training_quantile_reference_json": json.dumps(
                    calibration_to_dict(calibration), sort_keys=True
                ),
                "exclusion_policy": (
                    "test_only; continuous_replayable_events; source_quality_issue_guard; "
                    "material_gap_guard; nonoverlap_guard"
                ),
                "source_caveat": start_event.row.get("known_source_caveat", ""),
            }
        )

    if result.achieved_test_anomalous_rows < target_rows:
        raise RuntimeError(
            f"Household {household_id}: safely generated {result.achieved_test_anomalous_rows} of "
            f"{target_rows} target test perturbation rows after {attempts} attempts. "
            "No incomplete evidence was written. Reduce the target rate, relax a declared constraint, "
            "or investigate the held-out data-quality windows."
        )
    return result


def calibration_to_dict(calibration: HouseholdCalibration) -> dict[str, Any]:
    return {
        "household_id": calibration.household_id,
        "train_row_count": calibration.train_row_count,
        "p10_kwh": calibration.p10_kwh,
        "p50_kwh": calibration.p50_kwh,
        "p90_kwh": calibration.p90_kwh,
        "p95_kwh": calibration.p95_kwh,
        "p995_kwh": calibration.p995_kwh,
    }


def output_fields(source_fields: Sequence[str]) -> list[str]:
    additions = [
        "dataset_split",
        "evaluation_cohort",
        "original_estimated_interval_energy_kwh",
        "synthetic_replay_energy_kwh",
        "anomaly_label",
        "anomaly_type",
        "anomaly_event_id",
        "label_provenance",
    ]
    duplicates = set(source_fields) & set(additions)
    if duplicates:
        raise ValueError(f"Input already contains Task 4 derived field(s): {', '.join(sorted(duplicates))}")
    return list(source_fields) + additions


def write_household_dataset(writer: csv.DictWriter, events: Sequence[Event]) -> None:
    """Append one processed household to an already-open derived dataset."""
    for event in events:
        output = dict(event.row)
        output.update(
            {
                "dataset_split": event.split,
                "evaluation_cohort": cohort_for(event.household_id),
                "original_estimated_interval_energy_kwh": event.row["estimated_interval_energy_kwh"],
                "synthetic_replay_energy_kwh": float_text(event.synthetic_energy_kwh),
                "anomaly_label": str(event.anomaly_label),
                "anomaly_type": event.anomaly_type,
                "anomaly_event_id": event.anomaly_event_id,
                "label_provenance": (
                    "controlled_synthetic_perturbation" if event.anomaly_label else "unmodified_recorded_baseline"
                ),
            }
        )
        writer.writerow(output)


INJECTION_LOG_FIELDS = [
    "household_id",
    "evaluation_cohort",
    "anomaly_event_id",
    "dataset_split",
    "start_source_row_number",
    "end_source_row_number",
    "start_source_unix",
    "end_source_unix",
    "start_timestamp_utc",
    "end_timestamp_utc",
    "anomaly_type",
    "duration_seconds",
    "event_row_count",
    "original_energy_kwh_sum",
    "modified_energy_kwh_sum",
    "absolute_energy_change_kwh",
    "relative_energy_change",
    "magnitude_parameter_json",
    "label",
    "label_provenance",
    "random_seed",
    "household_seed",
    "training_quantile_reference_json",
    "exclusion_policy",
    "source_caveat",
]


def write_injection_log(path: Path, results: Sequence[HouseholdResult]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INJECTION_LOG_FIELDS, lineterminator="\n")
        writer.writeheader()
        for result in sorted(results, key=lambda item: item.household_id):
            writer.writerows(result.episodes)


def write_quality_report(path: Path, results: Sequence[HouseholdResult]) -> None:
    fields = [
        "household_id",
        "evaluation_cohort",
        "dataset_split",
        "total_rows",
        "normal_rows",
        "synthetic_anomaly_rows",
        "synthetic_anomaly_rate",
        "target_test_anomaly_rows",
        "achieved_test_anomaly_rows",
        "episode_count",
        "sustained_high_episodes",
        "sustained_low_episodes",
        "stuck_signal_episodes",
        "solar_interference_documented",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for result in sorted(results, key=lambda item: item.household_id):
            household_id = result.household_id
            episodes_by_type = Counter(episode["anomaly_type"] for episode in result.episodes)
            for split in ("train", "validation", "test"):
                total_rows = result.split_counts[split]
                anomalies = result.achieved_test_anomalous_rows if split == "test" else 0
                writer.writerow(
                    {
                        "household_id": household_id,
                        "evaluation_cohort": result.cohort,
                        "dataset_split": split,
                        "total_rows": total_rows,
                        "normal_rows": total_rows - anomalies,
                        "synthetic_anomaly_rows": anomalies,
                        "synthetic_anomaly_rate": (anomalies / total_rows) if total_rows else 0.0,
                        "target_test_anomaly_rows": result.target_test_anomalous_rows if split == "test" else 0,
                        "achieved_test_anomaly_rows": result.achieved_test_anomalous_rows if split == "test" else 0,
                        "episode_count": len(result.episodes) if split == "test" else 0,
                        "sustained_high_episodes": episodes_by_type["sustained_high"] if split == "test" else 0,
                        "sustained_low_episodes": episodes_by_type["sustained_low"] if split == "test" else 0,
                        "stuck_signal_episodes": episodes_by_type["stuck_signal"] if split == "test" else 0,
                        "solar_interference_documented": str(household_id in SOLAR_SENSITIVITY_HOUSEHOLDS).lower(),
                    }
                )


def yaml_quote(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_config(
    path: Path,
    *,
    args: argparse.Namespace,
    households: Sequence[int],
    anomaly_types: Sequence[str],
    controls: ScenarioControls,
    input_sha256: str,
    calibrations: Sequence[HouseholdCalibration],
) -> None:
    """Write plain, dependency-free YAML; values are JSON-quoted YAML scalars."""
    lines = [
        "schema_version: \"1.0\"",
        f"generator: {yaml_quote('scripts/refit_task4_generate_anomalies.py')}",
        f"generator_version: {yaml_quote(SCRIPT_VERSION)}",
        "label_semantics:",
        "  positive_label: 1",
        "  negative_label: 0",
        "  positive_label_meaning: \"controlled synthetic perturbation; not an observed REFIT anomaly\"",
        "  negative_label_meaning: \"unmodified recorded baseline event\"",
        "input:",
        f"  path: {yaml_quote(args.input.as_posix())}",
        f"  sha256: {yaml_quote(input_sha256)}",
        "  source_unit: \"estimated interval energy (kWh), Task 2 trapezoidal estimate\"",
        "selection:",
        f"  households: [{', '.join(str(item) for item in households)}]",
        "  primary_households: [1, 2, 4]",
        "  solar_interference_sensitivity_households: [3, 11]",
        "chronological_split:",
        f"  train_fraction: {args.train_fraction}",
        f"  validation_fraction: {args.validation_fraction}",
        f"  test_fraction: {1.0 - args.train_fraction - args.validation_fraction:.12g}",
        "  random_row_split: false",
        "  perturbation_partitions: [test]",
        "injection:",
        f"  seed: {args.seed}",
        f"  target_test_anomaly_rate: {args.test_anomaly_rate}",
        f"  anomaly_types: [{', '.join(yaml_quote(item) for item in anomaly_types)}]",
        f"  sustained_high_multipliers: [{', '.join(str(item) for item in controls.high_multipliers)}]",
        f"  sustained_low_multipliers: [{', '.join(str(item) for item in controls.low_multipliers)}]",
        f"  stuck_min_relative_spread: {controls.stuck_min_relative_spread}",
        f"  min_duration_seconds: {args.min_duration_seconds}",
        f"  max_duration_seconds: {args.max_duration_seconds}",
        f"  guard_seconds: {args.guard_seconds}",
        f"  maximum_contiguous_gap_seconds: {MAX_CONTIGUOUS_GAP_SECONDS}",
        "  excludes_source_quality_markers: true",
        "  excludes_material_gap_neighbourhoods: true",
        "  allows_overlap: false",
        "  raw_or_task2_source_mutation: false",
        "calibration_from_train_partition:",
    ]
    for calibration in sorted(calibrations, key=lambda item: item.household_id):
        lines.extend(
            [
                f"  household_{calibration.household_id}:",
                f"    train_row_count: {calibration.train_row_count}",
                f"    p10_kwh: {calibration.p10_kwh}",
                f"    p50_kwh: {calibration.p50_kwh}",
                f"    p90_kwh: {calibration.p90_kwh}",
                f"    p95_kwh: {calibration.p95_kwh}",
                f"    p995_kwh: {calibration.p995_kwh}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: Path, results: Sequence[HouseholdResult], input_path: Path, input_sha256: str) -> None:
    total_rows = sum(result.total_rows for result in results)
    total_anomalies = sum(result.achieved_test_anomalous_rows for result in results)
    total_episodes = sum(len(result.episodes) for result in results)
    type_counts = Counter(
        episode["anomaly_type"] for result in results for episode in result.episodes
    )
    lines = [
        "# REFIT Task 4 — Controlled Perturbation Dataset Summary",
        "",
        "## Interpretation boundary",
        "",
        "This output labels **controlled synthetic perturbations** over a real, recorded REFIT aggregate-load baseline. It does not label genuine appliance faults, does not convert the REFIT `Issues` field into a target, and must not be reported as real-world anomaly-detection accuracy.",
        "",
        "The selected cohort (H1, H2, H3, H4, H11) does not have auditable five-house official aggregate anomaly labels in this execution environment. The University of Strathclyde's separate appliance-level label resource covers H1, H10, H16, H18, and H20; its direct CSV/README schema and timestamp mapping were unavailable for audit here. See `evidence/17_refit_anomaly_labelling/strategy.md`.",
        "",
        "## Frozen input",
        "",
        f"- Input: `{input_path.as_posix()}`",
        f"- Input SHA-256: `{input_sha256}`",
        f"- Records copied into derived dataset: **{total_rows:,}**",
        "- Original Task 2 `estimated_interval_energy_kwh` values are preserved verbatim; `synthetic_replay_energy_kwh` is the only derived replay feature.",
        "",
        "## Generation result",
        "",
        f"- Synthetic-labelled test records: **{total_anomalies:,}**",
        f"- Perturbation episodes: **{total_episodes:,}**",
        f"- Episode types: sustained high = **{type_counts['sustained_high']}**, sustained low = **{type_counts['sustained_low']}**, stuck signal = **{type_counts['stuck_signal']}**.",
        "- Train and validation records remain unmodified. Each household was chronologically split before any injection; no random row split is used.",
        "- H1/H2/H4 are primary cohort records. H3/H11 carry source-documented solar-generation interference and are a sensitivity cohort only.",
        "",
        "## Files",
        "",
        "- `anomaly_dataset.csv` — original Task 2 source columns plus split, cohort, original and synthetic replay energy, labels, and episode IDs.",
        "- `anomaly_injection_log.csv` — one auditable row per perturbation episode, including household, start/end, type, original/modified energy sums, magnitude, label and seed.",
        "- `anomaly_generation_config.yaml` — deterministic parameters and per-household training quantiles.",
        "- `anomaly_dataset_quality_report.csv` — class/split distribution with primary/sensitivity cohort separation.",
        "- `anomaly_generation_manifest.json` — hashes and generation constraints.",
        "",
        "## Later-model boundary",
        "",
        "A later model may fit only the unmodified chronological training partition and use validation for threshold selection. Any result against the test labels is a controlled-perturbation detection result. It is not a comparison with genuine REFIT appliance annotations.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def assert_household_invariants(result: HouseholdResult, events: Sequence[Event]) -> None:
    """Fail before writing a household if a split/label/source rule was violated."""
    expected = 0
    event_ids: dict[str, int] = Counter()
    for event in events:
        if event.synthetic_energy_kwh < -EPSILON or not math.isfinite(event.synthetic_energy_kwh):
            raise AssertionError("Synthetic energy must remain finite and non-negative")
        if event.split in {"train", "validation"} and event.anomaly_label != 0:
            raise AssertionError("Train/validation contamination detected")
        if event.anomaly_label:
            expected += 1
            if event.split != "test" or not event.anomaly_event_id or event.anomaly_type == "normal":
                raise AssertionError("Invalid synthetic positive-label provenance")
            if not boolish(event.row.get("is_replayable", "")):
                raise AssertionError("Positive label overlays a non-replayable event")
            if boolish(event.row.get("source_quality_issue_flag", "")):
                raise AssertionError("Positive label overlays a source-quality marker")
            if abs(event.synthetic_energy_kwh - event.energy_kwh) <= EPSILON:
                raise AssertionError("Positive label has no numerical change")
            event_ids[event.anomaly_event_id] += 1
        elif abs(event.synthetic_energy_kwh - event.energy_kwh) > EPSILON:
            raise AssertionError("Unlabelled record was altered")
    if expected != result.achieved_test_anomalous_rows:
        raise AssertionError("Injected event count disagrees with household result")
    logged_ids = {episode["anomaly_event_id"] for episode in result.episodes}
    if set(event_ids) != logged_ids:
        raise AssertionError("Dataset episode IDs do not exactly match injection log")


def write_manifest(
    path: Path,
    *,
    input_path: Path,
    input_sha256: str,
    output_dir: Path,
    args: argparse.Namespace,
    results: Sequence[HouseholdResult],
    controls: ScenarioControls,
) -> None:
    hashes = {
        candidate.name: sha256_file(candidate)
        for candidate in sorted(output_dir.iterdir())
        if candidate.is_file() and candidate.name != path.name
    }
    payload = {
        "schema_version": "1.0",
        "generator": "scripts/refit_task4_generate_anomalies.py",
        "generator_version": SCRIPT_VERSION,
        "input": {"path": input_path.as_posix(), "sha256": input_sha256},
        "semantic_boundary": {
            "positive_label": "controlled synthetic perturbation, not observed REFIT anomaly",
            "official_refit_anomaly_labels_used": False,
            "source_quality_markers_used_as_labels": False,
            "task2_source_modified": False,
        },
        "configuration": {
            "seed": args.seed,
            "train_fraction": args.train_fraction,
            "validation_fraction": args.validation_fraction,
            "test_anomaly_rate": args.test_anomaly_rate,
            "min_duration_seconds": args.min_duration_seconds,
            "max_duration_seconds": args.max_duration_seconds,
            "guard_seconds": args.guard_seconds,
            "anomaly_types": list(parse_types(args.anomaly_types)),
            "sustained_high_multipliers": list(controls.high_multipliers),
            "sustained_low_multipliers": list(controls.low_multipliers),
            "stuck_min_relative_spread": controls.stuck_min_relative_spread,
            "households": list(parse_id_list(args.households)),
        },
        "households": [
            {
                "household_id": result.household_id,
                "evaluation_cohort": result.cohort,
                "total_rows": result.total_rows,
                "split_counts": result.split_counts,
                "target_test_anomalous_rows": result.target_test_anomalous_rows,
                "achieved_test_anomalous_rows": result.achieved_test_anomalous_rows,
                "episode_count": len(result.episodes),
                "training_calibration": calibration_to_dict(result.calibration) if result.calibration else None,
            }
            for result in sorted(results, key=lambda item: item.household_id)
        ],
        "output_sha256": hashes,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(args: argparse.Namespace) -> Path:
    requested_households, anomaly_types, controls = validate_args(args)
    input_sha256 = sha256_file(args.input)
    source_fields = read_source_fields(args.input)
    results: list[HouseholdResult] = []
    calibrations: list[HouseholdCalibration] = []
    output_parent = args.output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{args.output_dir.name}.tmp-", dir=output_parent))
    try:
        with (temporary_dir / "anomaly_dataset.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=output_fields(source_fields), lineterminator="\n")
            writer.writeheader()
            for household_id in requested_households:
                events = load_one_household(args.input, household_id)
                assign_chronological_splits(events, args.train_fraction, args.validation_fraction)
                calibration = calibration_from_train(events)
                result = inject_household(
                    events=events,
                    calibration=calibration,
                    target_rate=args.test_anomaly_rate,
                    min_duration_seconds=args.min_duration_seconds,
                    max_duration_seconds=args.max_duration_seconds,
                    guard_seconds=args.guard_seconds,
                    anomaly_types=anomaly_types,
                    controls=controls,
                    base_seed=args.seed,
                    max_attempts=args.max_attempts_per_household,
                )
                assert_household_invariants(result, events)
                write_household_dataset(writer, events)
                results.append(result)
                calibrations.append(calibration)
        write_injection_log(temporary_dir / "anomaly_injection_log.csv", results)
        write_quality_report(temporary_dir / "anomaly_dataset_quality_report.csv", results)
        write_config(
            temporary_dir / "anomaly_generation_config.yaml",
            args=args,
            households=requested_households,
            anomaly_types=anomaly_types,
            controls=controls,
            input_sha256=input_sha256,
            calibrations=calibrations,
        )
        write_summary(temporary_dir / "anomaly_generation_summary.md", results, args.input, input_sha256)
        write_manifest(
            temporary_dir / "anomaly_generation_manifest.json",
            input_path=args.input,
            input_sha256=input_sha256,
            output_dir=temporary_dir,
            args=args,
            results=results,
            controls=controls,
        )
        temporary_dir.replace(args.output_dir)
    except BaseException:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise
    return args.output_dir


def main() -> int:
    args = parse_args()
    try:
        output_dir = generate(args)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Generated controlled-perturbation artifacts in {output_dir}")
    print("Positive labels mean controlled synthetic perturbation, not observed REFIT anomaly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
