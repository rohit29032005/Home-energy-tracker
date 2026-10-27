"""Focused unit tests for the REFIT controlled-perturbation trainer."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


# ``ml-service`` is not a valid Python identifier, so make this runnable from
# the repository root as well as through unittest discovery in this directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ML_SERVICE_ROOT = REPOSITORY_ROOT / "ml-service"
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from training import train_refit_controlled as trainer


COHORT = "primary_no_documented_solar_interference"


def make_args(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "bin_seconds": 300,
        "history_bins": 2,
        "mad_floor_relative": 0.05,
        "mad_floor_min_w": 1.0,
        "persistence_bins": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_record(
    start: int,
    power_w: float,
    *,
    split: str = "train",
    label: int = 0,
    quality_status: str = "eligible",
) -> trainer.BinRecord:
    return trainer.BinRecord(
        household_id=1,
        bin_start_epoch=start,
        timestamp_utc=f"1970-01-01T00:00:{start:02d}Z",
        dataset_split=split,
        evaluation_cohort=COHORT,
        energy_kwh=power_w / 12_000.0,
        coverage_seconds=300.0,
        power_proxy_w=power_w,
        anomaly_label=label,
        anomaly_types="synthetic" if label else "",
        anomaly_event_ids="event-1" if label else "",
        positive_coverage_seconds=300.0 if label else 0.0,
        quality_status=quality_status,
    )


class NegativeDecisionModel:
    """Small score stub: isolation_scores negates decision_function output."""

    def decision_function(self, frame: pd.DataFrame) -> np.ndarray:
        return -np.ones(len(frame), dtype=float)


class TrainRefitControlledTests(unittest.TestCase):
    def test_model_feature_contract_excludes_labels_split_and_quality(self) -> None:
        forbidden = {
            "anomaly_label",
            "anomaly_types",
            "anomaly_event_ids",
            "dataset_split",
            "evaluation_cohort",
            "quality_status",
            "positive_coverage_seconds",
        }

        self.assertFalse(set(trainer.MODEL_FEATURES) & forbidden)

        frame = trainer.build_feature_frame(
            [make_record(index * 300, 10.0 + index) for index in range(3)],
            scale_floor_w=1.0,
            args=make_args(),
        )
        ready = frame.loc[frame["feature_ready"]]
        matrix = trainer.feature_matrix(ready)
        self.assertEqual(list(matrix.columns), trainer.MODEL_FEATURES)
        self.assertFalse(set(matrix.columns) & forbidden)

    def test_feature_values_do_not_depend_on_later_rows(self) -> None:
        records = [make_record(index * 300, power) for index, power in enumerate((10.0, 20.0, 30.0, 40.0))]
        changed_future = records[:-1] + [make_record(900, 40_000.0)]

        before = trainer.build_feature_frame(records, scale_floor_w=5.0, args=make_args())
        after = trainer.build_feature_frame(changed_future, scale_floor_w=5.0, args=make_args())
        before_row = before.loc[before["bin_start_epoch"].eq(600)].iloc[0]
        after_row = after.loc[after["bin_start_epoch"].eq(600)].iloc[0]

        self.assertTrue(before_row["feature_ready"])
        self.assertTrue(after_row["feature_ready"])
        for feature in trainer.MODEL_FEATURES:
            self.assertTrue(math.isclose(before_row[feature], after_row[feature], rel_tol=0.0, abs_tol=1e-12))

    def test_scale_floor_rejects_positive_training_bin(self) -> None:
        with self.assertRaisesRegex(ValueError, "Normal-only training was violated"):
            trainer.calculate_scale_floor(
                [make_record(0, 100.0, label=1)],
                make_args(),
            )

    def test_persistence_needs_consecutive_candidates_and_resets_by_segment(self) -> None:
        rows: list[dict[str, object]] = []
        for index, segment_id in enumerate((1, 1, 1, 2, 2, 2)):
            row: dict[str, object] = {
                "bin_start_epoch": index * 300,
                "stream_segment_id": segment_id,
                "feature_ready": True,
            }
            row.update({feature: 0.0 for feature in trainer.MODEL_FEATURES})
            row["robust_residual"] = 1.0
            rows.append(row)
        frame = pd.DataFrame(rows)
        result = trainer.HouseholdTrainingResult(
            household_id=1,
            cohort=COHORT,
            threshold_isolation_forest=0.5,
            threshold_robust_residual=0.5,
            model=NegativeDecisionModel(),  # type: ignore[arg-type]
            model_parameters={},
            scale_floor_w=1.0,
            train_rows=2,
            validation_rows=1,
            test_rows=1,
        )

        scored = trainer.add_scores_and_persistence(frame, result, make_args(persistence_bins=3))

        expected_alerts = [False, False, True, False, False, True]
        for detector in ("isolation_forest", "robust_residual"):
            self.assertEqual(scored[f"{detector}_candidate"].tolist(), [True] * 6)
            self.assertEqual(scored[f"{detector}_alert"].tolist(), expected_alerts)
            self.assertEqual(scored[f"{detector}_alert_start"].tolist(), [False, False, True, False, False, True])

    def test_crossing_interval_allocates_energy_and_positive_coverage_exactly(self) -> None:
        event = trainer.LabeledEvent(
            household_id=1,
            timestamp_epoch=305,
            timestamp_utc="1970-01-01T00:05:05Z",
            interval_seconds=10,
            is_replayable=True,
            source_quality_issue=False,
            dataset_split="test",
            evaluation_cohort=COHORT,
            synthetic_energy_kwh=0.01,
            anomaly_label=1,
            anomaly_type="controlled_spike",
            anomaly_event_id="event-crossing-bin",
            label_provenance="controlled_synthetic_perturbation",
        )
        bins: dict[int, trainer.BinAccumulator] = {}

        keys = trainer.add_event_to_bins(bins, event, bin_seconds=300)

        self.assertEqual(keys, [0, 300])
        self.assertAlmostEqual(bins[0].energy_kwh, 0.005)
        self.assertAlmostEqual(bins[300].energy_kwh, 0.005)
        self.assertAlmostEqual(sum(bin_.energy_kwh for bin_ in bins.values()), event.synthetic_energy_kwh)
        self.assertEqual(bins[0].coverage_seconds, 5.0)
        self.assertEqual(bins[300].coverage_seconds, 5.0)
        self.assertEqual(bins[0].positive_coverage_seconds, 5.0)
        self.assertEqual(bins[300].positive_coverage_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
