#!/usr/bin/env python3
"""Independent consistency checks for Task 2 REFIT preprocessing artifacts.

This verifier is read-only. It does not regenerate, modify, replay, or upload
the dataset. It checks the coverage and mathematical contract claimed by the
Task 2 output files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


MAX_INTEGRATABLE_GAP_SECONDS = 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Task 2 REFIT preprocessing artifacts.")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/refit/processed"),
        help="Directory written by scripts/refit_task2_preprocess.py.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise AssertionError(f"Invalid integer {field}={value!r}") from exc


def parse_float(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AssertionError(f"Invalid float {field}={value!r}") from exc
    if not math.isfinite(parsed):
        raise AssertionError(f"Non-finite float {field}={value!r}")
    return parsed


def main() -> None:
    args = parse_args()
    processed = args.processed_dir
    paths = {
        "cleaned_dataset.csv": processed / "cleaned_dataset.csv",
        "preprocessing_actions.csv": processed / "preprocessing_actions.csv",
        "data_quality_report.csv": processed / "data_quality_report.csv",
        "preprocessing_manifest.json": processed / "preprocessing_manifest.json",
        "preprocessing_summary.md": processed / "preprocessing_summary.md",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise AssertionError(f"Missing Task 2 artifact(s): {', '.join(missing)}")

    with paths["data_quality_report.csv"].open("r", encoding="utf-8", newline="") as handle:
        quality_rows = list(csv.DictReader(handle))
    overall = next(
        (row for row in quality_rows if row.get("scope") == "overall_selected_five_households"), None
    )
    if overall is None:
        raise AssertionError("No overall_selected_five_households row in data_quality_report.csv")
    expected_source_rows = parse_int(overall["source_rows_selected"], "source_rows_selected")
    expected_cleaned_rows = parse_int(overall["cleaned_records_written"], "cleaned_records_written")
    expected_energy = parse_float(overall["estimated_replayable_energy_kwh"], "estimated_replayable_energy_kwh")

    action_count = 0
    action_events = 0
    action_keys: set[tuple[str, str]] = set()
    action_types: Counter[str] = Counter()
    with paths["preprocessing_actions.csv"].open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            action_count += 1
            key = (row["source_filename"], row["source_row_number"])
            if key in action_keys:
                raise AssertionError(f"Duplicate action-log entry for source record {key}")
            action_keys.add(key)
            action_types[row["action"]] += 1
            if row["cleaned_event_written"].lower() == "true":
                action_events += 1

    cleaned_count = 0
    cleaned_energy = 0.0
    prior_timestamp_by_house: dict[str, int] = defaultdict(lambda: -1)
    quality_counts: Counter[str] = Counter()
    with paths["cleaned_dataset.csv"].open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cleaned_count += 1
            household = row["household_id"]
            current_timestamp = parse_int(row["source_unix"], "source_unix")
            if current_timestamp <= prior_timestamp_by_house[household]:
                raise AssertionError(f"Non-chronological cleaned timestamp for household {household}")
            prior_timestamp_by_house[household] = current_timestamp
            interval_seconds = parse_int(row["interval_seconds"], "interval_seconds")
            if not 0 < interval_seconds <= MAX_INTEGRATABLE_GAP_SECONDS:
                raise AssertionError(
                    f"Cleaned row violates gap policy: interval_seconds={interval_seconds}"
                )
            energy = parse_float(row["estimated_interval_energy_kwh"], "estimated_interval_energy_kwh")
            if energy < 0:
                raise AssertionError(f"Negative normalized energy: {energy}")
            if row["is_replayable"].lower() != "true":
                raise AssertionError("A row in cleaned_dataset.csv is not marked replayable")
            if row["conversion_method"] != "trapezoidal_active_power_w_actual_unix_delta":
                raise AssertionError(f"Unexpected conversion method: {row['conversion_method']!r}")
            cleaned_energy += energy
            quality_counts[row["interval_quality"]] += 1

    if action_count != expected_source_rows:
        raise AssertionError(f"Action rows {action_count} != reported source rows {expected_source_rows}")
    if cleaned_count != expected_cleaned_rows:
        raise AssertionError(
            f"Cleaned rows {cleaned_count} != reported cleaned rows {expected_cleaned_rows}"
        )
    if action_events != cleaned_count:
        raise AssertionError(f"Action event count {action_events} != cleaned rows {cleaned_count}")
    if not math.isclose(cleaned_energy, expected_energy, rel_tol=1e-12, abs_tol=1e-9):
        raise AssertionError(
            f"Cleaned energy {cleaned_energy!r} != reported energy {expected_energy!r}"
        )

    manifest = json.loads(paths["preprocessing_manifest.json"].read_text(encoding="utf-8"))
    for filename, expected_hash in manifest.get("output_hashes_sha256", {}).items():
        actual_path = processed / filename
        if not actual_path.is_file():
            raise AssertionError(f"Manifest names unavailable output: {filename}")
        actual_hash = sha256_file(actual_path)
        if actual_hash != expected_hash:
            raise AssertionError(f"Checksum mismatch for {filename}")

    result = {
        "verification": "passed",
        "selected_source_rows": action_count,
        "action_log_unique_source_rows": len(action_keys),
        "cleaned_replayable_records": cleaned_count,
        "action_rows_marked_event_written": action_events,
        "estimated_energy_kwh_sum": cleaned_energy,
        "interval_quality_counts": dict(sorted(quality_counts.items())),
        "action_type_counts": dict(sorted(action_types.items())),
        "manifest_hashes_verified": sorted(manifest.get("output_hashes_sha256", {})),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"VERIFICATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
