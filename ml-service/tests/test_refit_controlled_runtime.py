"""Unit tests for the explicit, stateful REFIT controlled-model adapter."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np


ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.refit_controlled import (  # noqa: E402
    FEATURE_NAMES,
    PROFILE_IDS,
    RefitControlledEngine,
    RefitControlledError,
    _PendingBin,
    _StreamState,
)


class FixedDecisionModel:
    """Returns a fixed negative decision function, so score is positive one."""

    def decision_function(self, _frame: object) -> np.ndarray:
        return np.asarray([-1.0])


def metadata() -> dict[str, object]:
    profiles = {
        str(profile): {
            "threshold_isolation_forest": 0.5,
            "threshold_robust_residual": 999.0,
            "scale_floor_w": 1.0,
        }
        for profile in PROFILE_IDS
    }
    return {
        "artifact_schema": "refit_controlled_v1",
        "script_version": "test",
        "feature_names": list(FEATURE_NAMES),
        "binning": {
            "bin_seconds": 300,
            "minimum_coverage_seconds": 285.0,
            "history_bins": 6,
            "persistence_bins": 3,
        },
        "household_models": profiles,
    }


def engine() -> RefitControlledEngine:
    return RefitControlledEngine(
        {str(profile): FixedDecisionModel() for profile in PROFILE_IDS}, metadata()
    )


def send_constant_power(
    runtime: RefitControlledEngine,
    *,
    profile_id: int,
    stream_id: str,
    completed_bins: int,
    power_w: float = 100.0,
    start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
) -> list[object]:
    """Produce 10-second intervals and return every closed-bin result."""
    energy_per_event = power_w * 10.0 / 3_600_000.0
    results: list[object] = []
    for offset in range(10, completed_bins * 300 + 1, 10):
        response = runtime.ingest(
            profile_id=profile_id,
            stream_id=stream_id,
            energy_kwh=energy_per_event,
            timestamp=start + timedelta(seconds=offset),
            interval_seconds=10,
        )
        results.extend(response.closed_bins)
    return results


class RefitControlledRuntimeTests(unittest.TestCase):
    def test_profile_is_explicit_and_not_derived_from_stream_or_device_identifier(self) -> None:
        runtime = engine()
        response = runtime.ingest(
            profile_id=4,
            stream_id="device-999",
            energy_kwh=0.001,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            interval_seconds=8,
        )
        self.assertEqual(response.profile_id, 4)
        self.assertEqual(response.stream_id, "device-999")
        with self.assertRaisesRegex(RefitControlledError, "Unsupported REFIT profile"):
            runtime.ingest(
                profile_id=999,
                stream_id="device-999",
                energy_kwh=0.001,
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                interval_seconds=8,
            )

    def test_cross_bin_interval_preserves_energy_and_coverage(self) -> None:
        runtime = engine()
        state = _StreamState(profile_id=1)
        runtime._add_interval(state, end_epoch=305, energy_kwh=0.01, interval_seconds=10)
        self.assertEqual(set(state.pending_bins), {0, 300})
        self.assertAlmostEqual(state.pending_bins[0].energy_kwh, 0.005)
        self.assertAlmostEqual(state.pending_bins[300].energy_kwh, 0.005)
        self.assertAlmostEqual(state.pending_bins[0].coverage_seconds, 5.0)
        self.assertAlmostEqual(state.pending_bins[300].coverage_seconds, 5.0)
        self.assertAlmostEqual(
            sum(item.energy_kwh for item in state.pending_bins.values()), 0.01
        )

    def test_six_completed_bins_are_warmup_and_seventh_is_scored(self) -> None:
        results = send_constant_power(
            engine(), profile_id=1, stream_id="explicit-stream-one", completed_bins=7
        )
        self.assertEqual(len(results), 7)
        self.assertTrue(all(item.status == "warming_up_causal_history" for item in results[:6]))
        self.assertEqual(results[-1].status, "scored_experimental_controlled_benchmark")
        self.assertEqual(results[-1].history_bins_available, 6)
        self.assertIn("isolation_forest", results[-1].detectors)

    def test_three_consecutive_candidates_trigger_only_the_third_scored_bin(self) -> None:
        results = send_constant_power(
            engine(), profile_id=2, stream_id="explicit-stream-two", completed_bins=9
        )
        decisions = [item.detectors["isolation_forest"] for item in results[6:]]
        self.assertEqual(len(decisions), 3)
        self.assertTrue(all(item.candidate for item in decisions))
        self.assertEqual([item.anomaly for item in decisions], [False, False, True])
        self.assertEqual([item.alert_start for item in decisions], [False, False, True])

    def test_material_gap_resets_stream_without_reusing_history(self) -> None:
        runtime = engine()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        runtime.ingest(
            profile_id=1,
            stream_id="gap-test",
            energy_kwh=0.0002,
            timestamp=start + timedelta(seconds=8),
            interval_seconds=8,
        )
        result = runtime.ingest(
            profile_id=1,
            stream_id="gap-test",
            energy_kwh=0.0002,
            timestamp=start + timedelta(seconds=40),
            interval_seconds=8,
        )
        self.assertEqual(result.input_state, "stream_reset_material_gap")
        self.assertEqual(runtime.stream_count, 1)


if __name__ == "__main__":
    unittest.main()
