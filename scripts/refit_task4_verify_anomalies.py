#!/usr/bin/env python3
"""Independently verify the Task 4 controlled-perturbation artifact.

This verifier streams the frozen Task 2 file and its Task 4 derived copy in
lockstep.  It checks source preservation, chronological partitions, synthetic
label semantics, episode-log reconciliation, and generation-manifest hashes.
It deliberately makes no claim that the positive labels are observed REFIT
anomalies; they are controlled synthetic perturbations only.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EPSILON = 1e-12
SPLIT_ORDER = {"train": 0, "validation": 1, "test": 2}
SUPPORTED_TYPES = {"sustained_high", "sustained_low", "stuck_signal"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Task 4 controlled-perturbation artifacts.")
    parser.add_argument("--source", type=Path, default=Path("data/refit/processed/cleaned_dataset.csv"))
    parser.add_argument("--dataset", type=Path, default=Path("data/refit/labeled-verified/anomaly_dataset.csv"))
    parser.add_argument("--log", type=Path, default=Path("data/refit/labeled-verified/anomaly_injection_log.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/refit/labeled-verified/anomaly_generation_manifest.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/17_refit_anomaly_labelling/anomaly_dataset_verification.json"),
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def float_value(value: str, context: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid float for {context}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite float for {context}: {value!r}")
    return parsed


def int_value(value: str, context: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {context}: {value!r}") from exc


def compare_close(actual: float, expected: float, name: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=EPSILON):
        raise ValueError(f"{name} mismatch: expected {expected!r}, got {actual!r}")


def split_for_row(index: int, total: int, train_fraction: float, validation_fraction: float) -> str:
    """Recompute the generator's chronological per-household split assignment."""
    train_end = int(math.floor(total * train_fraction))
    validation_end = int(math.floor(total * (train_fraction + validation_fraction)))
    if index < train_end:
        return "train"
    if index < validation_end:
        return "validation"
    return "test"


def timestamp_near_any(values: list[int], left: int, right: int) -> bool:
    position = bisect.bisect_left(values, left)
    return position < len(values) and values[position] <= right


def source_counts_and_bad_times(path: Path) -> tuple[Counter[str], dict[str, list[int]]]:
    """Count source rows and recreate the generator's non-label quality/gap markers."""
    counts: Counter[str] = Counter()
    bad_times: dict[str, list[int]] = defaultdict(list)
    last_timestamp: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            household = row.get("household_id", "")
            timestamp = int_value(row.get("source_unix", ""), f"source Unix row {row_number}")
            previous = last_timestamp.get(household)
            if previous is not None:
                if timestamp <= previous:
                    raise ValueError(f"Source chronology is not strictly increasing for household {household}")
                if timestamp - previous > 16:
                    bad_times[household].extend((previous, timestamp))
            if boolish(row.get("source_quality_issue_flag", "")):
                bad_times[household].append(timestamp)
            last_timestamp[household] = timestamp
            counts[household] += 1
    return counts, {household: sorted(set(values)) for household, values in bad_times.items()}


def verify(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.source, args.dataset, args.log, args.manifest):
        if not path.is_file():
            raise FileNotFoundError(f"Required file not found: {path}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    configuration = manifest.get("configuration", {})
    try:
        train_fraction = float(configuration["train_fraction"])
        validation_fraction = float(configuration["validation_fraction"])
        min_duration_seconds = int(configuration["min_duration_seconds"])
        max_duration_seconds = int(configuration["max_duration_seconds"])
        guard_seconds = int(configuration["guard_seconds"])
        expected_seed = str(configuration["seed"])
        expected_households = {str(item) for item in configuration["households"]}
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Manifest has no valid chronological-split/injection configuration") from exc
    if not (0.0 < train_fraction < 1.0 and 0.0 <= validation_fraction < 1.0 and train_fraction + validation_fraction < 1.0):
        raise ValueError("Manifest has invalid chronological fractions")
    if min_duration_seconds < 300 or max_duration_seconds < min_duration_seconds or guard_seconds < 0:
        raise ValueError("Manifest has invalid duration or guard settings")
    expected_source_hash = manifest.get("input", {}).get("sha256")
    actual_source_hash = sha256_file(args.source)
    if expected_source_hash != actual_source_hash:
        raise ValueError(
            f"Frozen Task 2 input SHA-256 mismatch: manifest={expected_source_hash}, actual={actual_source_hash}"
        )

    output_hashes = manifest.get("output_sha256", {})
    for filename, expected_hash in output_hashes.items():
        path = args.dataset.parent / filename
        if not path.is_file():
            raise ValueError(f"Manifest-listed generated artifact is missing: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Manifest SHA-256 mismatch for {filename}: {actual_hash} != {expected_hash}")

    source_counts, source_bad_times = source_counts_and_bad_times(args.source)
    if set(source_counts) != expected_households:
        raise ValueError(
            f"Manifest household selection {sorted(expected_households)} does not match source rows {sorted(source_counts)}"
        )

    with args.log.open("r", encoding="utf-8", newline="") as log_handle:
        log_rows = list(csv.DictReader(log_handle))
    required_log = {
        "household_id",
        "anomaly_event_id",
        "dataset_split",
        "start_source_unix",
        "end_source_unix",
        "anomaly_type",
        "duration_seconds",
        "event_row_count",
        "original_energy_kwh_sum",
        "modified_energy_kwh_sum",
        "random_seed",
        "label",
        "label_provenance",
    }
    missing_log = required_log - set(log_rows[0].keys() if log_rows else [])
    if missing_log:
        raise ValueError(f"Injection log missing required field(s): {', '.join(sorted(missing_log))}")
    log_by_id: dict[str, dict[str, str]] = {}
    for row in log_rows:
        identifier = row["anomaly_event_id"]
        if not identifier or identifier in log_by_id:
            raise ValueError(f"Injection log has missing or duplicate event ID: {identifier!r}")
        if row["dataset_split"] != "test" or row["label"] != "1":
            raise ValueError(f"Injection log event {identifier} is not a positive held-out test event")
        if row["label_provenance"] != "controlled_synthetic_perturbation":
            raise ValueError(f"Injection log event {identifier} has incorrect provenance")
        if row["anomaly_type"] not in SUPPORTED_TYPES:
            raise ValueError(f"Injection log event {identifier} has unsupported type")
        duration = int_value(row["duration_seconds"], f"log duration {identifier}")
        if duration < min_duration_seconds or duration > max_duration_seconds:
            raise ValueError(f"Injection log event {identifier} has invalid episode duration {duration}")
        if row["random_seed"] != expected_seed:
            raise ValueError(f"Injection log event {identifier} has a seed inconsistent with the manifest")
        log_by_id[identifier] = row

    total_rows = 0
    per_house_split: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    per_house_type: dict[str, Counter[str]] = defaultdict(Counter)
    event_observed: dict[str, dict[str, Any]] = {}
    last_split_by_household: dict[str, int] = {}
    source_index_by_household: Counter[str] = Counter()
    previous_row_event_id: dict[str, str] = defaultdict(str)
    seen_event_ids: dict[str, set[str]] = defaultdict(set)
    closed_event_ids: dict[str, set[str]] = defaultdict(set)

    with args.source.open("r", encoding="utf-8", newline="") as source_handle, args.dataset.open(
        "r", encoding="utf-8", newline=""
    ) as dataset_handle:
        source_reader = csv.DictReader(source_handle)
        dataset_reader = csv.DictReader(dataset_handle)
        source_fields = list(source_reader.fieldnames or [])
        required_dataset = {
            "dataset_split",
            "evaluation_cohort",
            "original_estimated_interval_energy_kwh",
            "synthetic_replay_energy_kwh",
            "anomaly_label",
            "anomaly_type",
            "anomaly_event_id",
            "label_provenance",
        }
        missing_dataset = required_dataset - set(dataset_reader.fieldnames or [])
        if missing_dataset:
            raise ValueError(f"Derived dataset missing field(s): {', '.join(sorted(missing_dataset))}")

        for row_number, (source_row, derived_row) in enumerate(zip(source_reader, dataset_reader), start=2):
            total_rows += 1
            for field in source_fields:
                if derived_row.get(field) != source_row.get(field):
                    raise ValueError(f"Source preservation mismatch at derived row {row_number}, field {field}")
            household = derived_row["household_id"]
            split = derived_row["dataset_split"]
            if split not in SPLIT_ORDER:
                raise ValueError(f"Invalid split at derived row {row_number}: {split!r}")
            if household not in source_counts:
                raise ValueError(f"Unexpected household in derived dataset at row {row_number}: {household}")
            source_index = source_index_by_household[household]
            expected_split = split_for_row(
                source_index,
                source_counts[household],
                train_fraction,
                validation_fraction,
            )
            if split != expected_split:
                raise ValueError(
                    f"Derived row {row_number} has split {split!r}; expected chronological "
                    f"split {expected_split!r} for household {household} source index {source_index}"
                )
            source_index_by_household[household] += 1
            if SPLIT_ORDER[split] < last_split_by_household.get(household, -1):
                raise ValueError(f"Non-chronological split order for household {household} at row {row_number}")
            last_split_by_household[household] = SPLIT_ORDER[split]

            original = float_value(derived_row["original_estimated_interval_energy_kwh"], f"original row {row_number}")
            source_energy = float_value(source_row["estimated_interval_energy_kwh"], f"source row {row_number}")
            synthetic = float_value(derived_row["synthetic_replay_energy_kwh"], f"synthetic row {row_number}")
            compare_close(original, source_energy, f"original-energy preservation row {row_number}")
            if synthetic < -EPSILON:
                raise ValueError(f"Negative synthetic energy at row {row_number}")
            label = derived_row["anomaly_label"]
            if label not in {"0", "1"}:
                raise ValueError(f"Invalid binary label at row {row_number}: {label!r}")
            per_house_split[(household, split)]["total"] += 1

            if label == "0":
                compare_close(synthetic, original, f"unchanged negative row {row_number}")
                if derived_row["anomaly_type"] != "normal" or derived_row["anomaly_event_id"]:
                    raise ValueError(f"Negative label carries anomaly metadata at row {row_number}")
                if derived_row["label_provenance"] != "unmodified_recorded_baseline":
                    raise ValueError(f"Negative label has incorrect provenance at row {row_number}")
                if previous_row_event_id[household]:
                    closed_event_ids[household].add(previous_row_event_id[household])
                    previous_row_event_id[household] = ""
                per_house_split[(household, split)]["normal"] += 1
                continue

            if split != "test":
                raise ValueError(f"Positive label outside test partition at row {row_number}")
            if derived_row["label_provenance"] != "controlled_synthetic_perturbation":
                raise ValueError(f"Positive label has wrong provenance at row {row_number}")
            anomaly_type = derived_row["anomaly_type"]
            identifier = derived_row["anomaly_event_id"]
            if anomaly_type not in SUPPORTED_TYPES or not identifier:
                raise ValueError(f"Positive label missing valid anomaly metadata at row {row_number}")
            if abs(synthetic - original) <= EPSILON:
                raise ValueError(f"Positive label does not modify energy at row {row_number}")
            if boolish(derived_row.get("source_quality_issue_flag", "")):
                raise ValueError(f"Positive label overlays source-quality marker at row {row_number}")
            if not boolish(derived_row.get("is_replayable", "")):
                raise ValueError(f"Positive label overlays a non-replayable event at row {row_number}")
            if identifier not in log_by_id:
                raise ValueError(f"Positive dataset event ID absent from injection log: {identifier}")
            prior_identifier = previous_row_event_id[household]
            if identifier in closed_event_ids[household]:
                raise ValueError(f"Episode {identifier} is not contiguous in household {household}")
            if identifier in seen_event_ids[household] and prior_identifier != identifier:
                raise ValueError(f"Episode {identifier} resumes after another event or a normal row")
            if prior_identifier and prior_identifier != identifier:
                closed_event_ids[household].add(prior_identifier)
            seen_event_ids[household].add(identifier)
            previous_row_event_id[household] = identifier
            timestamp = int_value(derived_row["source_unix"], f"source Unix row {row_number}")
            observed = event_observed.setdefault(
                identifier,
                {
                    "count": 0,
                    "original_sum": 0.0,
                    "synthetic_sum": 0.0,
                    "first_unix": timestamp,
                    "last_unix": timestamp,
                    "household": household,
                    "type": anomaly_type,
                },
            )
            if observed["household"] != household or observed["type"] != anomaly_type:
                raise ValueError(f"Episode {identifier} changes household or type across its rows")
            if observed["count"] and (timestamp <= observed["last_unix"] or timestamp - observed["last_unix"] > 16):
                raise ValueError(f"Episode {identifier} contains a non-continuous source-time transition")
            observed["count"] += 1
            observed["original_sum"] += original
            observed["synthetic_sum"] += synthetic
            observed["last_unix"] = timestamp
            per_house_split[(household, split)]["synthetic_anomaly"] += 1
            per_house_type[household][anomaly_type] += 1

        trailing_source = next(source_reader, None)
        trailing_derived = next(dataset_reader, None)
        if trailing_source is not None or trailing_derived is not None:
            raise ValueError("Source and derived dataset row counts differ")

    if dict(source_index_by_household) != dict(source_counts):
        raise ValueError("Derived dataset does not preserve the complete per-household source row counts")

    if set(event_observed) != set(log_by_id):
        missing_from_dataset = sorted(set(log_by_id) - set(event_observed))
        missing_from_log = sorted(set(event_observed) - set(log_by_id))
        raise ValueError(
            f"Episode ID reconciliation failed; missing dataset={missing_from_dataset}, missing log={missing_from_log}"
        )
    for identifier, observed in event_observed.items():
        log_row = log_by_id[identifier]
        if log_row["household_id"] != observed["household"]:
            raise ValueError(f"Episode {identifier}: household does not match injection log")
        if log_row["anomaly_type"] != observed["type"]:
            raise ValueError(f"Episode {identifier}: anomaly type does not match injection log")
        if str(observed["count"]) != log_row["event_row_count"]:
            raise ValueError(f"Episode {identifier}: row count does not match log")
        compare_close(observed["original_sum"], float_value(log_row["original_energy_kwh_sum"], identifier), f"{identifier} original sum")
        compare_close(observed["synthetic_sum"], float_value(log_row["modified_energy_kwh_sum"], identifier), f"{identifier} synthetic sum")
        if str(observed["first_unix"]) != log_row["start_source_unix"]:
            raise ValueError(f"Episode {identifier}: start timestamp does not match log")
        if str(observed["last_unix"]) != log_row["end_source_unix"]:
            raise ValueError(f"Episode {identifier}: end timestamp does not match log")
        actual_duration = observed["last_unix"] - observed["first_unix"]
        if actual_duration != int_value(log_row["duration_seconds"], f"episode duration {identifier}"):
            raise ValueError(f"Episode {identifier}: duration does not match start/end timestamps")
        if timestamp_near_any(
            source_bad_times.get(observed["household"], []),
            observed["first_unix"] - guard_seconds,
            observed["last_unix"] + guard_seconds,
        ):
            raise ValueError(f"Episode {identifier}: overlaps a quality-marker or material-gap guard window")

    intervals_by_household: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for identifier, observed in event_observed.items():
        intervals_by_household[observed["household"]].append(
            (observed["first_unix"], observed["last_unix"], identifier)
        )
    for household, intervals in intervals_by_household.items():
        intervals.sort()
        for (_, previous_end, previous_id), (current_start, _, current_id) in zip(intervals, intervals[1:]):
            if current_start <= previous_end + guard_seconds:
                raise ValueError(
                    f"Episodes {previous_id} and {current_id} violate the configured {guard_seconds}s non-overlap guard "
                    f"for household {household}"
                )

    result = {
        "verification_status": "PASS",
        "semantic_boundary": "Labels verified as controlled synthetic perturbations only; no genuine REFIT anomaly-label claim is made.",
        "source_sha256": actual_source_hash,
        "rows_verified": total_rows,
        "injection_episode_count": len(log_by_id),
        "synthetic_positive_rows": sum(item["count"] for item in event_observed.values()),
        "household_split_counts": {
            f"H{household}_{split}": dict(sorted(counts.items()))
            for (household, split), counts in sorted(per_house_split.items(), key=lambda item: (int(item[0][0]), SPLIT_ORDER[item[0][1]]))
        },
        "household_positive_type_rows": {household: dict(counts) for household, counts in sorted(per_house_type.items(), key=lambda item: int(item[0]))},
        "checks": [
            "manifest input and generated artifact hashes",
            "all frozen Task 2 source columns preserved",
            "source and derived row counts aligned",
            "per-household chronological 70/15/15 split boundaries recomputed from manifest fractions",
            "positive labels only in held-out test records",
            "negative labels numerically unchanged",
            "positive labels numerically changed, non-negative, and replayable",
            "source-quality / material-gap guard windows not injected",
            "episode duration, contiguity, type, household, non-overlap guard, IDs, sums and timestamps reconcile",
        ],
    }
    return result


def boolish(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    args = parse_args()
    try:
        result = verify(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"PASS: verified {result['rows_verified']:,} derived events and {result['injection_episode_count']} episodes")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
