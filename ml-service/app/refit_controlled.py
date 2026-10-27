"""Stateful inference adapter for the isolated REFIT controlled benchmark.

This module intentionally does not replace the legacy Wokwi-compatible
classifier in :mod:`app.main`.  The REFIT artifact was trained on an aggregate
meter stream with causal history and five-minute bins, so it needs an explicit
profile and stream identifier.  It has no implicit device-to-household mapping
and it returns anomaly scores rather than false probabilities.

The artifact remains an experimental controlled-perturbation benchmark.  It
must not be described as a production fault detector or silently applied to
Wokwi's differently scaled telemetry.
"""

from __future__ import annotations

import json
import math
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


ARTIFACT_SCHEMA = "refit_controlled_v1"
PROFILE_IDS = frozenset({1, 2, 3, 4, 11})
FEATURE_NAMES = (
    "log1p_power_proxy_w",
    "robust_residual",
    "scaled_change",
    "trailing_variability",
    "time_of_day_sin",
    "time_of_day_cos",
)


class RefitControlledError(ValueError):
    """Raised when an experimental REFIT stream cannot be evaluated safely."""


@dataclass
class _PendingBin:
    start_epoch: int
    energy_kwh: float = 0.0
    coverage_seconds: float = 0.0


@dataclass
class _StreamState:
    profile_id: int
    pending_bins: dict[int, _PendingBin] = field(default_factory=dict)
    history_power_w: deque[float] = field(default_factory=deque)
    candidate_streaks: dict[str, int] = field(
        default_factory=lambda: {"isolation_forest": 0, "robust_residual": 0}
    )
    last_event_epoch: int | None = None
    last_good_bin_start: int | None = None

    def reset_detection_state(self) -> None:
        self.history_power_w.clear()
        self.candidate_streaks = {"isolation_forest": 0, "robust_residual": 0}
        self.last_good_bin_start = None


@dataclass(frozen=True)
class DetectorDecision:
    """One detector's score and fixed-policy decision at a closed bin."""

    anomaly_score: float
    threshold: float
    candidate: bool
    anomaly: bool
    alert_start: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "anomalyScore": round(self.anomaly_score, 12),
            "decisionThreshold": round(self.threshold, 12),
            "candidate": self.candidate,
            "anomaly": self.anomaly,
            "alertStart": self.alert_start,
        }


@dataclass(frozen=True)
class ClosedBinResult:
    """A serialisable result emitted only after a five-minute bin is closed."""

    profile_id: int
    stream_id: str
    bin_start_epoch: int
    bin_end_epoch: int
    coverage_seconds: float
    status: str
    history_bins_available: int
    detectors: dict[str, DetectorDecision] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "refitProfileId": self.profile_id,
            "streamId": self.stream_id,
            "binStart": datetime.fromtimestamp(self.bin_start_epoch, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "binEnd": datetime.fromtimestamp(self.bin_end_epoch, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "coverageSeconds": round(self.coverage_seconds, 6),
            "state": self.status,
            "historyBinsAvailable": self.history_bins_available,
        }
        if self.detectors:
            result["detectors"] = {
                name: decision.as_dict() for name, decision in self.detectors.items()
            }
        return result


@dataclass(frozen=True)
class StreamIngestionResult:
    """Result of one raw meter event; often buffering, sometimes a closed bin."""

    profile_id: int
    stream_id: str
    input_state: str
    closed_bins: tuple[ClosedBinResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "refitProfileId": self.profile_id,
            "streamId": self.stream_id,
            "inputState": self.input_state,
            "closedBins": [item.as_dict() for item in self.closed_bins],
        }


def _utc_epoch(timestamp: datetime) -> int:
    if timestamp.tzinfo is None:
        raise RefitControlledError("REFIT experimental timestamps must include a timezone")
    return int(timestamp.astimezone(timezone.utc).timestamp())


def _bin_start(epoch_seconds: int, bin_seconds: int) -> int:
    return epoch_seconds - (epoch_seconds % bin_seconds)


class RefitControlledEngine:
    """Thread-safe, stateful adapter for an isolated REFIT model artifact."""

    def __init__(self, models_by_household: dict[str, Any], metadata: dict[str, Any]) -> None:
        self._models = models_by_household
        self._metadata = metadata
        self._states: dict[str, _StreamState] = {}
        self._lock = threading.RLock()
        self._validate_artifact()

    @classmethod
    def load(cls, artifact_dir: Path) -> "RefitControlledEngine":
        metadata_path = artifact_dir / "model_metadata.json"
        model_path = artifact_dir / "isolation_forest_by_household.joblib"
        if not metadata_path.is_file() or not model_path.is_file():
            raise FileNotFoundError(
                "REFIT controlled model artifacts are unavailable; expected "
                f"{metadata_path} and {model_path}"
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        artifact = joblib.load(model_path)
        if not isinstance(artifact, dict):
            raise RefitControlledError("REFIT controlled model joblib must contain an object")
        if artifact.get("artifact_schema") != ARTIFACT_SCHEMA:
            raise RefitControlledError("REFIT controlled model joblib has an unsupported schema")
        models = artifact.get("models_by_household")
        if not isinstance(models, dict):
            raise RefitControlledError("REFIT controlled model joblib lacks models_by_household")
        return cls(models, metadata)

    @property
    def model_version(self) -> str:
        return f"{self._metadata.get('artifact_schema', ARTIFACT_SCHEMA)}-{self._metadata.get('script_version', 'unknown')}"

    @property
    def profile_ids(self) -> tuple[int, ...]:
        return tuple(sorted(PROFILE_IDS))

    @property
    def stream_count(self) -> int:
        with self._lock:
            return len(self._states)

    def reset_stream(self, stream_id: str) -> bool:
        """Explicitly clear a caller-owned stream state; never infer ownership."""
        with self._lock:
            return self._states.pop(stream_id, None) is not None

    def ingest(
        self,
        *,
        profile_id: int,
        stream_id: str,
        energy_kwh: float,
        timestamp: datetime,
        interval_seconds: int,
    ) -> StreamIngestionResult:
        """Accept one time-ordered meter interval and emit any closed-bin results."""
        self._validate_event(profile_id, stream_id, energy_kwh, interval_seconds)
        end_epoch = _utc_epoch(timestamp)
        with self._lock:
            state, input_state = self._state_for_event(profile_id, stream_id, end_epoch, interval_seconds)
            self._add_interval(state, end_epoch, float(energy_kwh), interval_seconds)
            state.last_event_epoch = end_epoch
            closed = self._finalize_completed_bins(state, stream_id, end_epoch)
            return StreamIngestionResult(
                profile_id=profile_id,
                stream_id=stream_id,
                input_state=input_state,
                closed_bins=tuple(closed),
            )

    def _validate_artifact(self) -> None:
        if self._metadata.get("artifact_schema") != ARTIFACT_SCHEMA:
            raise RefitControlledError("REFIT metadata has an unsupported artifact schema")
        declared_features = tuple(self._metadata.get("feature_names", []))
        if declared_features != FEATURE_NAMES:
            raise RefitControlledError("REFIT metadata feature contract does not match the causal adapter")
        models = {str(key) for key in self._models}
        expected = {str(profile) for profile in PROFILE_IDS}
        if models != expected:
            raise RefitControlledError("REFIT artifact does not contain exactly the five declared profiles")
        household_models = self._metadata.get("household_models")
        if not isinstance(household_models, dict) or set(household_models) != expected:
            raise RefitControlledError("REFIT metadata household profiles do not reconcile with the artifact")
        binning = self._metadata.get("binning")
        if not isinstance(binning, dict):
            raise RefitControlledError("REFIT metadata lacks a binning contract")
        if int(binning.get("bin_seconds", 0)) != 300:
            raise RefitControlledError("REFIT adapter only supports the registered 300-second bins")
        if int(binning.get("history_bins", 0)) != 6:
            raise RefitControlledError("REFIT adapter only supports the registered six-bin causal history")
        if int(binning.get("persistence_bins", 0)) != 3:
            raise RefitControlledError("REFIT adapter only supports the registered three-bin persistence rule")
        minimum_coverage = float(binning.get("minimum_coverage_seconds", 0))
        if not 0 < minimum_coverage <= 300:
            raise RefitControlledError("REFIT metadata minimum coverage is invalid")
        for profile in expected:
            profile_metadata = household_models[profile]
            if not isinstance(profile_metadata, dict):
                raise RefitControlledError(f"REFIT metadata profile H{profile} is invalid")
            for key in ("threshold_isolation_forest", "threshold_robust_residual", "scale_floor_w"):
                value = profile_metadata.get(key)
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise RefitControlledError(f"REFIT metadata profile H{profile} lacks finite {key}")
            if float(profile_metadata["scale_floor_w"]) <= 0:
                raise RefitControlledError(f"REFIT metadata profile H{profile} has non-positive scale floor")

    def _validate_event(
        self,
        profile_id: int,
        stream_id: str,
        energy_kwh: float,
        interval_seconds: int,
    ) -> None:
        if isinstance(profile_id, bool) or not isinstance(profile_id, int) or profile_id not in PROFILE_IDS:
            raise RefitControlledError(
                f"Unsupported REFIT profile {profile_id}; use one of {sorted(PROFILE_IDS)}"
            )
        if not isinstance(stream_id, str) or not stream_id.strip() or len(stream_id) > 160:
            raise RefitControlledError("stream_id must be a non-empty string of at most 160 characters")
        if not isinstance(energy_kwh, (int, float)) or not math.isfinite(float(energy_kwh)):
            raise RefitControlledError("energy_kwh must be finite")
        if float(energy_kwh) < 0:
            raise RefitControlledError("energy_kwh must be non-negative")
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or not 1 <= interval_seconds <= 16:
            raise RefitControlledError("interval_seconds must be an integer in the replay-compatible range 1..16")

    def _state_for_event(
        self,
        profile_id: int,
        stream_id: str,
        end_epoch: int,
        interval_seconds: int,
    ) -> tuple[_StreamState, str]:
        state = self._states.get(stream_id)
        if state is None:
            state = _StreamState(profile_id=profile_id, history_power_w=deque(maxlen=self._history_bins))
            self._states[stream_id] = state
            return state, "accepted"
        if state.profile_id != profile_id:
            state = _StreamState(profile_id=profile_id, history_power_w=deque(maxlen=self._history_bins))
            self._states[stream_id] = state
            return state, "stream_reset_profile_changed"
        assert state.last_event_epoch is not None
        interval_start = end_epoch - interval_seconds
        if end_epoch <= state.last_event_epoch:
            state = _StreamState(profile_id=profile_id, history_power_w=deque(maxlen=self._history_bins))
            self._states[stream_id] = state
            return state, "stream_reset_non_monotonic_timestamp"
        if interval_start < state.last_event_epoch:
            state = _StreamState(profile_id=profile_id, history_power_w=deque(maxlen=self._history_bins))
            self._states[stream_id] = state
            return state, "stream_reset_overlapping_interval"
        if end_epoch - state.last_event_epoch > self._maximum_interval_seconds:
            state = _StreamState(profile_id=profile_id, history_power_w=deque(maxlen=self._history_bins))
            self._states[stream_id] = state
            return state, "stream_reset_material_gap"
        return state, "accepted"

    @property
    def _bin_seconds(self) -> int:
        return int(self._metadata["binning"]["bin_seconds"])

    @property
    def _minimum_coverage_seconds(self) -> float:
        return float(self._metadata["binning"]["minimum_coverage_seconds"])

    @property
    def _history_bins(self) -> int:
        return int(self._metadata["binning"]["history_bins"])

    @property
    def _persistence_bins(self) -> int:
        return int(self._metadata["binning"]["persistence_bins"])

    @property
    def _maximum_interval_seconds(self) -> int:
        return 16

    def _add_interval(
        self,
        state: _StreamState,
        end_epoch: int,
        energy_kwh: float,
        interval_seconds: int,
    ) -> None:
        interval_start = end_epoch - interval_seconds
        cursor = interval_start
        while cursor < end_epoch:
            start = _bin_start(cursor, self._bin_seconds)
            end = start + self._bin_seconds
            overlap = min(end_epoch, end) - cursor
            pending = state.pending_bins.setdefault(start, _PendingBin(start_epoch=start))
            pending.energy_kwh += energy_kwh * (overlap / interval_seconds)
            pending.coverage_seconds += overlap
            cursor += overlap

    def _finalize_completed_bins(
        self, state: _StreamState, stream_id: str, current_end_epoch: int
    ) -> list[ClosedBinResult]:
        completed_starts = sorted(
            start for start in state.pending_bins if start + self._bin_seconds <= current_end_epoch
        )
        results: list[ClosedBinResult] = []
        for start in completed_starts:
            pending = state.pending_bins.pop(start)
            results.append(self._evaluate_closed_bin(state, stream_id, pending))
        return results

    def _evaluate_closed_bin(
        self, state: _StreamState, stream_id: str, pending: _PendingBin
    ) -> ClosedBinResult:
        end_epoch = pending.start_epoch + self._bin_seconds
        if pending.coverage_seconds < self._minimum_coverage_seconds:
            state.reset_detection_state()
            return ClosedBinResult(
                profile_id=state.profile_id,
                stream_id=stream_id,
                bin_start_epoch=pending.start_epoch,
                bin_end_epoch=end_epoch,
                coverage_seconds=pending.coverage_seconds,
                status="unscorable_insufficient_coverage",
                history_bins_available=0,
            )
        if (
            state.last_good_bin_start is not None
            and pending.start_epoch - state.last_good_bin_start != self._bin_seconds
        ):
            state.reset_detection_state()
        power_w = pending.energy_kwh * 3_600_000.0 / pending.coverage_seconds
        if not math.isfinite(power_w) or power_w < 0:
            state.reset_detection_state()
            return ClosedBinResult(
                profile_id=state.profile_id,
                stream_id=stream_id,
                bin_start_epoch=pending.start_epoch,
                bin_end_epoch=end_epoch,
                coverage_seconds=pending.coverage_seconds,
                status="unscorable_non_finite_power",
                history_bins_available=0,
            )
        history_length = len(state.history_power_w)
        if history_length < self._history_bins:
            state.history_power_w.append(power_w)
            state.last_good_bin_start = pending.start_epoch
            return ClosedBinResult(
                profile_id=state.profile_id,
                stream_id=stream_id,
                bin_start_epoch=pending.start_epoch,
                bin_end_epoch=end_epoch,
                coverage_seconds=pending.coverage_seconds,
                status="warming_up_causal_history",
                history_bins_available=len(state.history_power_w),
            )

        feature_row, residual = self._feature_row(state, power_w, pending.start_epoch)
        profile_metadata = self._metadata["household_models"][str(state.profile_id)]
        isolation_score = -float(
            self._models[str(state.profile_id)].decision_function(pd.DataFrame([feature_row]))[0]
        )
        baseline_score = abs(residual)
        decisions: dict[str, DetectorDecision] = {}
        for detector, score, threshold_key in (
            ("isolation_forest", isolation_score, "threshold_isolation_forest"),
            ("robust_residual", baseline_score, "threshold_robust_residual"),
        ):
            threshold = float(profile_metadata[threshold_key])
            candidate = score > threshold
            streak = state.candidate_streaks[detector] + 1 if candidate else 0
            state.candidate_streaks[detector] = streak
            anomaly = candidate and streak >= self._persistence_bins
            decisions[detector] = DetectorDecision(
                anomaly_score=score,
                threshold=threshold,
                candidate=candidate,
                anomaly=anomaly,
                alert_start=anomaly and streak == self._persistence_bins,
            )
        state.history_power_w.append(power_w)
        state.last_good_bin_start = pending.start_epoch
        return ClosedBinResult(
            profile_id=state.profile_id,
            stream_id=stream_id,
            bin_start_epoch=pending.start_epoch,
            bin_end_epoch=end_epoch,
            coverage_seconds=pending.coverage_seconds,
            status="scored_experimental_controlled_benchmark",
            history_bins_available=self._history_bins,
            detectors=decisions,
        )

    def _feature_row(
        self, state: _StreamState, current_power_w: float, bin_start_epoch: int
    ) -> tuple[dict[str, float], float]:
        history = np.asarray(state.history_power_w, dtype=float)
        median = float(np.median(history))
        mad = float(np.median(np.abs(history - median)))
        scale_floor = float(self._metadata["household_models"][str(state.profile_id)]["scale_floor_w"])
        robust_scale = max(1.4826 * mad, scale_floor)
        residual = (current_power_w - median) / robust_scale
        second_of_day = bin_start_epoch % 86_400
        angle = 2.0 * math.pi * second_of_day / 86_400.0
        return (
            {
                "log1p_power_proxy_w": math.log1p(current_power_w),
                "robust_residual": residual,
                "scaled_change": (current_power_w - float(history[-1])) / robust_scale,
                "trailing_variability": (1.4826 * mad) / scale_floor,
                "time_of_day_sin": math.sin(angle),
                "time_of_day_cos": math.cos(angle),
            },
            residual,
        )
