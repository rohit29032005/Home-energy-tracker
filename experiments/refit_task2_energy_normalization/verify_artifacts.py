#!/usr/bin/env python3
"""Read-only consistency verification for Task 2 REFIT artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Task 2 preprocessing outputs without changing them.")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=ROOT / "experiments/refit_task2_energy_normalization/artifacts",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    artifact_dir = args.artifact_dir.resolve()
    manifest_path = artifact_dir / "data_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["output_hashes_sha256"].items():
        actual = sha256_file(artifact_dir / name)
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {name}: {actual} != {expected}")

    primary = read_csv(artifact_dir / "cleaned_primary_cohort.csv")
    solar = read_csv(artifact_dir / "cleaned_solar_sensitivity_cohort.csv")
    excluded = read_csv(artifact_dir / "excluded_records_log.csv")
    quality = read_csv(artifact_dir / "per_household_quality_report.csv")
    expected_cohorts = {"primary": {"1", "2", "4"}, "solar_sensitivity": {"3", "11"}}
    seen_keys: set[tuple[str, str]] = set()
    prior_unix: dict[str, int] = defaultdict(lambda: -1)
    event_counts: Counter[str] = Counter()
    energy_sums: Counter[str] = Counter()
    for cohort_name, rows in (("primary", primary), ("solar_sensitivity", solar)):
        for row in rows:
            house = row["household_id"]
            assert row["cohort"] == cohort_name
            assert house in expected_cohorts[cohort_name]
            key = (house, row["original_unix"])
            if key in seen_keys:
                raise AssertionError(f"Duplicate cleaned household/timestamp key: {key}")
            seen_keys.add(key)
            timestamp = int(row["original_unix"])
            if timestamp <= prior_unix[house]:
                raise AssertionError(f"Non-increasing cleaned timestamps for household {house}")
            prior_unix[house] = timestamp
            delta = int(row["interval_seconds"])
            if not 0 < delta <= 16:
                raise AssertionError(f"Invalid integrated delta: {delta}")
            power = float(row["original_aggregate_power_w"])
            reported = float(row["derived_interval_energy_kwh"])
            expected = power * delta / 3_600_000.0
            if not math.isclose(reported, expected, rel_tol=1e-12, abs_tol=1e-15):
                raise AssertionError(f"Energy formula mismatch for {key}: {reported} != {expected}")
            event_counts[house] += 1
            energy_sums[house] += reported

    excluded_counts: Counter[str] = Counter(row["household_id"] for row in excluded)
    for row in quality:
        house = row["household_id"]
        selected = int(row["selected_window_record_count"])
        cleaned = int(row["cleaned_interval_record_count"])
        excluded_count = int(row["excluded_source_record_count"])
        if selected != cleaned + excluded_count:
            raise AssertionError(f"Selected-row reconciliation failed for House {house}")
        if cleaned != event_counts[house]:
            raise AssertionError(f"Cleaned count mismatch for House {house}")
        if excluded_count != excluded_counts[house]:
            raise AssertionError(f"Excluded count mismatch for House {house}")
        reported_energy = float(row["estimated_interval_energy_kwh_sum"])
        if not math.isclose(reported_energy, energy_sums[house], rel_tol=1e-12, abs_tol=1e-12):
            raise AssertionError(f"Energy sum mismatch for House {house}")
        if row["reconciliation_status"] != "PASS":
            raise AssertionError(f"Quality report says non-PASS reconciliation for House {house}")

    result = {
        "verification": "passed",
        "artifact_dir": str(artifact_dir),
        "primary_cleaned_records": len(primary),
        "solar_sensitivity_cleaned_records": len(solar),
        "excluded_records": len(excluded),
        "per_household_reconciliations": len(quality),
        "output_hashes_verified": sorted(manifest["output_hashes_sha256"]),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, ValueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"VERIFICATION FAILED: {error}")
