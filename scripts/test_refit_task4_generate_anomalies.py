#!/usr/bin/env python3
"""Focused regression tests for Task 4 controlled-perturbation generation."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import refit_task4_generate_anomalies as task4  # noqa: E402
import refit_task4_verify_anomalies as task4_verify  # noqa: E402


SOURCE_FIELDS = [
    "household_id",
    "source_filename",
    "source_row_number",
    "source_time_text",
    "source_unix",
    "timestamp_utc",
    "previous_source_row_number",
    "previous_source_unix",
    "previous_timestamp_utc",
    "previous_aggregate_w",
    "aggregate_w",
    "interval_seconds",
    "estimated_interval_energy_kwh",
    "conversion_method",
    "interval_quality",
    "is_replayable",
    "exclusion_reason",
    "previous_iqr_outlier_diagnostic_flag",
    "current_iqr_outlier_diagnostic_flag",
    "source_issues_raw",
    "source_quality_issue_flag",
    "solar_interference_documented",
    "known_source_caveat",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class Task4GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="task4-test-"))
        self.input_path = self.temp_dir / "cleaned_dataset.csv"
        self._write_input()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_input(self) -> None:
        start = 1_700_000_000
        with self.input_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SOURCE_FIELDS, lineterminator="\n")
            writer.writeheader()
            # 1,800 records -> a 270-record final test partition (> 30 minutes).
            # Long high/low blocks make a sustained-low scenario deterministic.
            for index in range(1_800):
                phase = (index // 120) % 2
                energy = 0.0020 + (index % 17) * 0.00001 if phase else 0.00025 + (index % 17) * 0.00001
                timestamp = start + index * 8
                writer.writerow(
                    {
                        "household_id": "1",
                        "source_filename": "CLEAN_House1.csv",
                        "source_row_number": str(index + 2),
                        "source_time_text": "synthetic-test-only",
                        "source_unix": str(timestamp),
                        "timestamp_utc": f"1970-01-01T00:00:{index % 60:02d}Z",
                        "previous_source_row_number": str(index + 1),
                        "previous_source_unix": str(timestamp - 8),
                        "previous_timestamp_utc": "",
                        "previous_aggregate_w": "100",
                        "aggregate_w": "100",
                        "interval_seconds": "8",
                        "estimated_interval_energy_kwh": repr(energy),
                        "conversion_method": "test",
                        "interval_quality": "native_7_to_9_seconds",
                        "is_replayable": "true",
                        "exclusion_reason": "",
                        "previous_iqr_outlier_diagnostic_flag": "false",
                        "current_iqr_outlier_diagnostic_flag": "false",
                        "source_issues_raw": "0",
                        "source_quality_issue_flag": "false",
                        "solar_interference_documented": "false",
                        "known_source_caveat": "test-only",
                    }
                )

    def _args(self, output_dir: Path) -> object:
        parser = task4.argparse.ArgumentParser()
        # Construct the same namespace shape used by generator, without invoking process CLI.
        return task4.argparse.Namespace(
            input=self.input_path,
            output_dir=output_dir,
            seed=12345,
            train_fraction=0.70,
            validation_fraction=0.15,
            test_anomaly_rate=0.10,
            min_duration_seconds=300,
            max_duration_seconds=316,
            guard_seconds=0,
            anomaly_types="sustained_low",
            high_multipliers="1.40,1.60,1.80,2.00",
            low_multipliers="0.25,0.40,0.55,0.70",
            stuck_min_relative_spread=0.35,
            households="1",
            max_attempts_per_household=10000,
        )

    def _verify_args(self, output_dir: Path) -> object:
        return task4_verify.argparse.Namespace(
            source=self.input_path,
            dataset=output_dir / "anomaly_dataset.csv",
            log=output_dir / "anomaly_injection_log.csv",
            manifest=output_dir / "anomaly_generation_manifest.json",
            output=self.temp_dir / "verification.json",
        )

    def test_generation_is_deterministic_and_keeps_non_test_rows_untouched(self) -> None:
        source_hash_before = sha256(self.input_path)
        first = self.temp_dir / "out-one"
        second = self.temp_dir / "out-two"
        task4.generate(self._args(first))
        task4.generate(self._args(second))

        self.assertEqual(source_hash_before, sha256(self.input_path))
        for filename in (
            "anomaly_dataset.csv",
            "anomaly_injection_log.csv",
            "anomaly_generation_config.yaml",
            "anomaly_dataset_quality_report.csv",
            "anomaly_generation_summary.md",
            "anomaly_generation_manifest.json",
        ):
            self.assertEqual(sha256(first / filename), sha256(second / filename), filename)

        verification = task4_verify.verify(self._verify_args(first))
        self.assertEqual("PASS", verification["verification_status"])

        with (first / "anomaly_dataset.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(1_800, len(rows))
        positive_rows = [row for row in rows if row["anomaly_label"] == "1"]
        self.assertGreater(len(positive_rows), 0)
        for row in rows:
            if row["dataset_split"] in {"train", "validation"}:
                self.assertEqual("0", row["anomaly_label"])
                self.assertEqual(
                    row["estimated_interval_energy_kwh"],
                    row["synthetic_replay_energy_kwh"],
                )
            if row["anomaly_label"] == "1":
                self.assertEqual("test", row["dataset_split"])
                self.assertNotEqual(
                    row["estimated_interval_energy_kwh"],
                    row["synthetic_replay_energy_kwh"],
                )
                self.assertEqual("controlled_synthetic_perturbation", row["label_provenance"])

        with (first / "anomaly_injection_log.csv").open("r", encoding="utf-8", newline="") as handle:
            log_rows = list(csv.DictReader(handle))
        self.assertGreater(len(log_rows), 0)
        self.assertTrue(all(row["dataset_split"] == "test" for row in log_rows))
        self.assertTrue(all(row["label"] == "1" for row in log_rows))
        self.assertTrue(all(300 <= int(row["duration_seconds"]) <= 316 for row in log_rows))

        # Demonstrate that the verifier recomputes chronological boundaries,
        # rather than merely trusting a nondecreasing `dataset_split` column.
        dataset_path = first / "anomaly_dataset.csv"
        with dataset_path.open("r", encoding="utf-8", newline="") as handle:
            fieldnames = list(csv.DictReader(handle).fieldnames or [])
        with dataset_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["dataset_split"] = "test"
        with dataset_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        manifest_path = first / "anomaly_generation_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["output_sha256"]["anomaly_dataset.csv"] = sha256(dataset_path)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected chronological split"):
            task4_verify.verify(self._verify_args(first))


if __name__ == "__main__":
    unittest.main(verbosity=2)
