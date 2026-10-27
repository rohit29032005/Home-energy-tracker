#!/usr/bin/env python3
"""Create auditable, replay-ready interval-energy records from selected REFIT data.

This Task 2 script deliberately does *not* replay data, call project APIs,
train ML models, inject anomalies, or alter REFIT source files.  It converts
the five Task-1-selected historical REFIT windows from active-power samples
into estimated interval-energy events that are compatible with the project's
``energyConsumed`` (kWh increment) contract.

The REFIT ``Aggregate`` channel is documented active power in Watts.  The
source is sampled nominally every eight seconds, but actual Unix timestamp
intervals vary.  For a valid adjacent pair, the script therefore uses a
trapezoidal numerical integration with the *actual* Unix interval:

    E_kWh = ((P_previous + P_current) / 2) * delta_seconds / 3_600_000

This is an explicit numerical estimate, not a claim that the source provides
metered interval energy.  No interpolation, forward fill, zero fill, capping,
or statistical outlier removal is performed.  Intervals longer than 16
seconds (two nominal sampling periods) are not integrated because doing so
would infer unobserved consumption across a material gap.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK1_SELECTION_FILENAME = "household_selection.csv"
EXPECTED_SOURCE_COLUMNS = {"Time", "Unix", "Aggregate", "Issues"}
NOMINAL_SAMPLE_SECONDS = 8
NATIVE_MIN_SECONDS = 7
NATIVE_MAX_SECONDS = 9
MAX_INTEGRATABLE_GAP_SECONDS = 16
CONVERSION_METHOD = "trapezoidal_active_power_w_actual_unix_delta"

# The REFIT descriptor reports solar-generation interference for Houses 3 and
# 11.  This flag preserves that provenance without changing any observation.
SOLAR_INTERFERENCE_DOCUMENTED = {3, 11}


@dataclass(frozen=True)
class SelectedWindow:
    household_id: int
    source_filename: str
    start_unix: int
    end_unix: int
    start_utc: str
    end_utc: str
    selection_reason: str


@dataclass
class SourceRow:
    household_id: int
    source_filename: str
    source_row_number: int
    source_time_text: str
    source_unix_text: str
    aggregate_text: str
    source_issues: str
    source_unix: int | None
    aggregate_w: float | None


@dataclass
class HouseholdQuality:
    window: SelectedWindow
    source_rows_selected: int = 0
    valid_timestamp_rows: int = 0
    valid_aggregate_rows: int = 0
    invalid_timestamp_rows: int = 0
    invalid_aggregate_rows: int = 0
    negative_aggregate_rows: int = 0
    zero_aggregate_rows_retained: int = 0
    source_issues_marked_rows_retained: int = 0
    duplicate_timestamp_rows_excluded: int = 0
    out_of_order_timestamp_rows_excluded: int = 0
    boundary_rows_no_predecessor: int = 0
    predecessor_invalid_rows: int = 0
    intervals_observed: int = 0
    replayable_intervals: int = 0
    native_intervals_7_to_9_seconds: int = 0
    sub_nominal_intervals_1_to_6_seconds: int = 0
    short_irregular_intervals_10_to_16_seconds: int = 0
    non_integrable_gap_intervals_over_16_seconds: int = 0
    gaps_17_to_60_seconds: int = 0
    gaps_over_60_seconds: int = 0
    max_observed_positive_delta_seconds: int = 0
    total_replayable_interval_seconds: int = 0
    estimated_replayable_energy_kwh: float = 0.0
    iqr_outlier_source_rows_retained: int = 0
    source_rows_without_replay_event: int = 0
    output_rows_written: int = 0
    aggregate_q1_w: float | None = None
    aggregate_q3_w: float | None = None
    aggregate_iqr_lower_fence_w: float | None = None
    aggregate_iqr_upper_fence_w: float | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess Task-1-selected official REFIT windows into auditable interval kWh events."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/refit/raw/zenodo_5063428"),
        help="Directory containing the checksum-verified CLEAN_House*.csv source files.",
    )
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=Path("evidence/16_refit_dataset_audit") / TASK1_SELECTION_FILENAME,
        help="Task 1 selected-household CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/refit/processed"),
        help="Directory for Task 2 generated artifacts (source files are never changed).",
    )
    return parser.parse_args()


def utc_iso(epoch_seconds: int | None) -> str:
    if epoch_seconds is None:
        return ""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_epoch(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        number = float(value.strip())
    except (AttributeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def parse_nonnegative_finite_float(value: str | None) -> tuple[float | None, str | None]:
    """Return (value, error-code); zero is retained as a valid power sample."""
    if value is None:
        return None, "MISSING_AGGREGATE"
    try:
        number = float(value.strip())
    except (AttributeError, ValueError):
        return None, "INVALID_AGGREGATE"
    if not math.isfinite(number):
        return None, "NONFINITE_AGGREGATE"
    if number < 0:
        return None, "NEGATIVE_AGGREGATE"
    return number, None


def numeric_household_id(value: str) -> int:
    match = re.search(r"House(\d+)", value)
    if not match:
        raise ValueError(f"Could not determine a household ID from {value!r}")
    return int(match.group(1))


def parse_iso_utc(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Task 1 selection timestamp is not timezone-aware: {value!r}")
    return int(parsed.timestamp())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def float_text(value: float | None) -> str:
    """Write the shortest round-trip float representation; do not round kWh to display precision."""
    return "" if value is None else repr(value)


def percent(numerator: int | float, denominator: int | float) -> float | None:
    return None if not denominator else numerator / denominator


def quantile_linear(sorted_values: list[float], probability: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def iqr_fences(values: Iterable[float]) -> tuple[float | None, float | None, float | None, float | None]:
    ordered = sorted(values)
    q1 = quantile_linear(ordered, 0.25)
    q3 = quantile_linear(ordered, 0.75)
    if q1 is None or q3 is None:
        return q1, q3, None, None
    iqr = q3 - q1
    return q1, q3, q1 - 1.5 * iqr, q3 + 1.5 * iqr


def is_source_issue_marked(value: str) -> bool:
    """Keep source status verbatim; only identify non-empty, non-zero markers for reporting."""
    normalized = (value or "").strip()
    return normalized not in {"", "0", "0.0"}


def solar_caveat(household_id: int) -> str:
    if household_id in SOLAR_INTERFERENCE_DOCUMENTED:
        return (
            "Documented solar-generation interference in REFIT descriptor; retained unmodified. "
            "Use only with a declared sensitivity cohort for consumption claims."
        )
    if household_id == 1:
        return "REFIT descriptor reports House 1 was rewired to eliminate solar contribution."
    return "No solar-interference caveat applied from the Task 2 source review."


def load_selected_windows(selection_path: Path) -> list[SelectedWindow]:
    if not selection_path.is_file():
        raise FileNotFoundError(f"Task 1 selection file not found: {selection_path}")
    selected: list[SelectedWindow] = []
    with selection_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "household",
            "source_filename",
            "selection_status",
            "selection_reason",
            "best_window_start_utc",
            "best_window_end_utc",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Selection file lacks required fields: {', '.join(sorted(missing))}")
        for row in reader:
            if row["selection_status"].strip() != "SELECTED":
                continue
            household_id = int(row["household"])
            source_filename = row["source_filename"].strip()
            if numeric_household_id(source_filename) != household_id:
                raise ValueError(
                    f"Household ID mismatch in selection: {household_id} versus {source_filename}"
                )
            start_utc = row["best_window_start_utc"].strip()
            end_utc = row["best_window_end_utc"].strip()
            selected.append(
                SelectedWindow(
                    household_id=household_id,
                    source_filename=source_filename,
                    start_unix=parse_iso_utc(start_utc),
                    end_unix=parse_iso_utc(end_utc),
                    start_utc=start_utc,
                    end_utc=end_utc,
                    selection_reason=row["selection_reason"].strip(),
                )
            )
    if not selected:
        raise ValueError("Task 1 selection file contains no rows with selection_status=SELECTED")
    return sorted(selected, key=lambda item: item.household_id)


def read_selected_source_rows(input_path: Path, window: SelectedWindow) -> list[SourceRow]:
    """Read only the Task-1-selected inclusive Unix window from a source file.

    A malformed Unix timestamp cannot be placed in a bounded time window and
    is therefore outside this selected-window extraction.  Task 1 already
    audited all source rows and recorded zero invalid Unix values for these
    checksum-verified files.
    """
    rows: list[SourceRow] = []
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = EXPECTED_SOURCE_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"{input_path.name} lacks expected columns: {', '.join(sorted(missing))}")
        for source_row_number, row in enumerate(reader, start=2):
            unix_text = row.get("Unix", "")
            unix_value = parse_epoch(unix_text)
            if unix_value is None or unix_value < window.start_unix or unix_value > window.end_unix:
                continue
            aggregate_value, _ = parse_nonnegative_finite_float(row.get("Aggregate"))
            rows.append(
                SourceRow(
                    household_id=window.household_id,
                    source_filename=window.source_filename,
                    source_row_number=source_row_number,
                    source_time_text=(row.get("Time") or "").strip(),
                    source_unix_text=(unix_text or "").strip(),
                    aggregate_text=(row.get("Aggregate") or "").strip(),
                    source_issues=(row.get("Issues") or "").strip(),
                    source_unix=unix_value,
                    aggregate_w=aggregate_value,
                )
            )
    return rows


def action_row(
    source: SourceRow,
    *,
    action: str,
    reason: str,
    event_written: bool,
    previous: SourceRow | None = None,
    delta_seconds: int | None = None,
    iqr_outlier_flag: bool = False,
) -> dict[str, str]:
    return {
        "household_id": str(source.household_id),
        "source_filename": source.source_filename,
        "source_row_number": str(source.source_row_number),
        "source_time_text": source.source_time_text,
        "source_unix": source.source_unix_text,
        "source_timestamp_utc": utc_iso(source.source_unix),
        "aggregate_w_raw": source.aggregate_text,
        "source_issues_raw": source.source_issues,
        "source_quality_issue_flag": str(is_source_issue_marked(source.source_issues)).lower(),
        "solar_interference_documented": str(
            source.household_id in SOLAR_INTERFERENCE_DOCUMENTED
        ).lower(),
        "previous_source_row_number": "" if previous is None else str(previous.source_row_number),
        "previous_source_unix": "" if previous is None else previous.source_unix_text,
        "previous_timestamp_utc": "" if previous is None else utc_iso(previous.source_unix),
        "interval_seconds": "" if delta_seconds is None else str(delta_seconds),
        "iqr_outlier_diagnostic_flag": str(iqr_outlier_flag).lower(),
        "action": action,
        "reason": reason,
        "cleaned_event_written": str(event_written).lower(),
    }


def cleaned_row(
    source: SourceRow,
    previous: SourceRow,
    delta_seconds: int,
    energy_kwh: float,
    previous_iqr_outlier: bool,
    current_iqr_outlier: bool,
) -> dict[str, str]:
    if NATIVE_MIN_SECONDS <= delta_seconds <= NATIVE_MAX_SECONDS:
        interval_quality = "native_7_to_9_seconds"
    elif 1 <= delta_seconds <= NATIVE_MIN_SECONDS - 1:
        interval_quality = "sub_nominal_1_to_6_seconds"
    else:
        interval_quality = "short_irregular_10_to_16_seconds"
    return {
        "household_id": str(source.household_id),
        "source_filename": source.source_filename,
        "source_row_number": str(source.source_row_number),
        "source_time_text": source.source_time_text,
        "source_unix": source.source_unix_text,
        "timestamp_utc": utc_iso(source.source_unix),
        "previous_source_row_number": str(previous.source_row_number),
        "previous_source_unix": previous.source_unix_text,
        "previous_timestamp_utc": utc_iso(previous.source_unix),
        "previous_aggregate_w": float_text(previous.aggregate_w),
        "aggregate_w": float_text(source.aggregate_w),
        "interval_seconds": str(delta_seconds),
        "estimated_interval_energy_kwh": float_text(energy_kwh),
        "conversion_method": CONVERSION_METHOD,
        "interval_quality": interval_quality,
        "is_replayable": "true",
        "exclusion_reason": "",
        "previous_iqr_outlier_diagnostic_flag": str(previous_iqr_outlier).lower(),
        "current_iqr_outlier_diagnostic_flag": str(current_iqr_outlier).lower(),
        "source_issues_raw": source.source_issues,
        "source_quality_issue_flag": str(is_source_issue_marked(source.source_issues)).lower(),
        "solar_interference_documented": str(
            source.household_id in SOLAR_INTERFERENCE_DOCUMENTED
        ).lower(),
        "known_source_caveat": solar_caveat(source.household_id),
    }


def write_household_records(
    rows: list[SourceRow],
    quality: HouseholdQuality,
    cleaned_writer: csv.DictWriter,
    action_writer: csv.DictWriter,
) -> None:
    """Write one action record per selected source row and replayable events only."""
    finite_nonnegative_values = [row.aggregate_w for row in rows if row.aggregate_w is not None]
    q1, q3, lower, upper = iqr_fences(finite_nonnegative_values)
    quality.aggregate_q1_w = q1
    quality.aggregate_q3_w = q3
    quality.aggregate_iqr_lower_fence_w = lower
    quality.aggregate_iqr_upper_fence_w = upper

    def is_iqr_outlier(value: float | None) -> bool:
        if value is None or lower is None or upper is None:
            return False
        return value < lower or value > upper

    previous: SourceRow | None = None
    last_seen_unix: int | None = None
    for source in rows:
        quality.source_rows_selected += 1
        if source.source_unix is None:
            quality.invalid_timestamp_rows += 1
            quality.source_rows_without_replay_event += 1
            action_writer.writerow(
                action_row(
                    source,
                    action="INVALID_TIMESTAMP_EXCLUDED",
                    reason="Unix timestamp was not a finite integer epoch value.",
                    event_written=False,
                )
            )
            previous = None
            continue

        quality.valid_timestamp_rows += 1
        aggregate_value, aggregate_error = parse_nonnegative_finite_float(source.aggregate_text)
        if aggregate_error is not None:
            quality.source_rows_without_replay_event += 1
            if aggregate_error == "NEGATIVE_AGGREGATE":
                quality.negative_aggregate_rows += 1
            else:
                quality.invalid_aggregate_rows += 1
            action_writer.writerow(
                action_row(
                    source,
                    action=f"{aggregate_error}_EXCLUDED",
                    reason="Aggregate power is not a finite, non-negative active-power observation.",
                    event_written=False,
                )
            )
            previous = None
            continue

        # Retain the parsed value exactly as read (within IEEE float representation).
        source.aggregate_w = aggregate_value
        quality.valid_aggregate_rows += 1
        if aggregate_value == 0:
            quality.zero_aggregate_rows_retained += 1
        if is_source_issue_marked(source.source_issues):
            quality.source_issues_marked_rows_retained += 1

        current_iqr_outlier = is_iqr_outlier(aggregate_value)
        if current_iqr_outlier:
            quality.iqr_outlier_source_rows_retained += 1

        if last_seen_unix is not None:
            if source.source_unix == last_seen_unix:
                quality.duplicate_timestamp_rows_excluded += 1
                quality.source_rows_without_replay_event += 1
                action_writer.writerow(
                    action_row(
                        source,
                        action="DUPLICATE_TIMESTAMP_EXCLUDED",
                        reason="Duplicate Unix timestamp is excluded; no source value is merged or overwritten.",
                        event_written=False,
                        previous=previous,
                        delta_seconds=0,
                        iqr_outlier_flag=current_iqr_outlier,
                    )
                )
                continue
            if source.source_unix < last_seen_unix:
                quality.out_of_order_timestamp_rows_excluded += 1
                quality.source_rows_without_replay_event += 1
                action_writer.writerow(
                    action_row(
                        source,
                        action="OUT_OF_ORDER_TIMESTAMP_EXCLUDED",
                        reason="Out-of-order Unix timestamp is excluded instead of being silently reordered.",
                        event_written=False,
                        previous=previous,
                        delta_seconds=source.source_unix - last_seen_unix,
                        iqr_outlier_flag=current_iqr_outlier,
                    )
                )
                continue

        last_seen_unix = source.source_unix
        if previous is None:
            quality.boundary_rows_no_predecessor += 1
            quality.source_rows_without_replay_event += 1
            action_writer.writerow(
                action_row(
                    source,
                    action="BOUNDARY_NO_PREDECESSOR",
                    reason="First valid source record of a selected segment has no preceding in-window observation.",
                    event_written=False,
                    iqr_outlier_flag=current_iqr_outlier,
                )
            )
            previous = source
            continue

        if previous.source_unix is None or previous.aggregate_w is None:
            quality.predecessor_invalid_rows += 1
            quality.source_rows_without_replay_event += 1
            action_writer.writerow(
                action_row(
                    source,
                    action="PREDECESSOR_INVALID_NO_EVENT",
                    reason="No interval is estimated across an invalid predecessor observation.",
                    event_written=False,
                    previous=previous,
                    iqr_outlier_flag=current_iqr_outlier,
                )
            )
            previous = source
            continue

        delta_seconds = source.source_unix - previous.source_unix
        quality.intervals_observed += 1
        if delta_seconds > 0:
            quality.max_observed_positive_delta_seconds = max(
                quality.max_observed_positive_delta_seconds, delta_seconds
            )
        if delta_seconds <= 0:
            quality.source_rows_without_replay_event += 1
            action_writer.writerow(
                action_row(
                    source,
                    action="NONPOSITIVE_INTERVAL_EXCLUDED",
                    reason="A non-positive Unix-time interval cannot represent forward elapsed energy.",
                    event_written=False,
                    previous=previous,
                    delta_seconds=delta_seconds,
                    iqr_outlier_flag=current_iqr_outlier,
                )
            )
            previous = source
            continue

        if delta_seconds > MAX_INTEGRATABLE_GAP_SECONDS:
            quality.non_integrable_gap_intervals_over_16_seconds += 1
            quality.source_rows_without_replay_event += 1
            if delta_seconds <= 60:
                quality.gaps_17_to_60_seconds += 1
            else:
                quality.gaps_over_60_seconds += 1
            action_writer.writerow(
                action_row(
                    source,
                    action="GAP_GT_16S_EXCLUDED",
                    reason=(
                        "Cross-gap energy was not estimated: interval exceeds the pre-registered "
                        f"{MAX_INTEGRATABLE_GAP_SECONDS}-second maximum integratable gap."
                    ),
                    event_written=False,
                    previous=previous,
                    delta_seconds=delta_seconds,
                    iqr_outlier_flag=current_iqr_outlier,
                )
            )
            # The valid post-gap reading becomes an anchor for the next adjacent interval.
            previous = source
            continue

        previous_iqr_outlier = is_iqr_outlier(previous.aggregate_w)
        energy_kwh = ((previous.aggregate_w + aggregate_value) / 2.0) * delta_seconds / 3_600_000.0
        cleaned_writer.writerow(
            cleaned_row(
                source,
                previous,
                delta_seconds,
                energy_kwh,
                previous_iqr_outlier,
                current_iqr_outlier,
            )
        )
        quality.replayable_intervals += 1
        quality.output_rows_written += 1
        quality.total_replayable_interval_seconds += delta_seconds
        quality.estimated_replayable_energy_kwh += energy_kwh
        if NATIVE_MIN_SECONDS <= delta_seconds <= NATIVE_MAX_SECONDS:
            quality.native_intervals_7_to_9_seconds += 1
        elif 1 <= delta_seconds <= NATIVE_MIN_SECONDS - 1:
            quality.sub_nominal_intervals_1_to_6_seconds += 1
        else:
            quality.short_irregular_intervals_10_to_16_seconds += 1
        action_writer.writerow(
            action_row(
                source,
                action="REPLAYABLE_INTERVAL_WRITTEN",
                reason=(
                    "Estimated interval energy with trapezoidal integration of two active-power "
                    "samples using the observed Unix-time delta."
                ),
                event_written=True,
                previous=previous,
                delta_seconds=delta_seconds,
                iqr_outlier_flag=current_iqr_outlier or previous_iqr_outlier,
            )
        )
        previous = source


def quality_row(quality: HouseholdQuality) -> dict[str, str]:
    return {
        "scope": "household",
        "household_id": str(quality.window.household_id),
        "source_filename": quality.window.source_filename,
        "selected_window_start_utc": quality.window.start_utc,
        "selected_window_end_utc": quality.window.end_utc,
        "solar_interference_documented": str(
            quality.window.household_id in SOLAR_INTERFERENCE_DOCUMENTED
        ).lower(),
        "known_source_caveat": solar_caveat(quality.window.household_id),
        "source_rows_selected": str(quality.source_rows_selected),
        "valid_timestamp_rows": str(quality.valid_timestamp_rows),
        "valid_aggregate_rows": str(quality.valid_aggregate_rows),
        "invalid_timestamp_rows": str(quality.invalid_timestamp_rows),
        "invalid_aggregate_rows": str(quality.invalid_aggregate_rows),
        "negative_aggregate_rows": str(quality.negative_aggregate_rows),
        "zero_aggregate_rows_retained": str(quality.zero_aggregate_rows_retained),
        "source_issues_marked_rows_retained": str(quality.source_issues_marked_rows_retained),
        "duplicate_timestamp_rows_excluded": str(quality.duplicate_timestamp_rows_excluded),
        "out_of_order_timestamp_rows_excluded": str(quality.out_of_order_timestamp_rows_excluded),
        "boundary_rows_no_predecessor": str(quality.boundary_rows_no_predecessor),
        "predecessor_invalid_rows": str(quality.predecessor_invalid_rows),
        "intervals_observed": str(quality.intervals_observed),
        "replayable_intervals": str(quality.replayable_intervals),
        "replayable_interval_share": float_text(
            percent(quality.replayable_intervals, quality.intervals_observed)
        ),
        "native_intervals_7_to_9_seconds": str(quality.native_intervals_7_to_9_seconds),
        "sub_nominal_intervals_1_to_6_seconds": str(quality.sub_nominal_intervals_1_to_6_seconds),
        "short_irregular_intervals_10_to_16_seconds": str(
            quality.short_irregular_intervals_10_to_16_seconds
        ),
        "non_integrable_gap_intervals_over_16_seconds": str(
            quality.non_integrable_gap_intervals_over_16_seconds
        ),
        "gaps_17_to_60_seconds": str(quality.gaps_17_to_60_seconds),
        "gaps_over_60_seconds": str(quality.gaps_over_60_seconds),
        "max_observed_positive_delta_seconds": str(quality.max_observed_positive_delta_seconds),
        "total_replayable_interval_seconds": str(quality.total_replayable_interval_seconds),
        "estimated_replayable_energy_kwh": float_text(quality.estimated_replayable_energy_kwh),
        "iqr_outlier_source_rows_retained": str(quality.iqr_outlier_source_rows_retained),
        "aggregate_q1_w": float_text(quality.aggregate_q1_w),
        "aggregate_q3_w": float_text(quality.aggregate_q3_w),
        "aggregate_iqr_lower_fence_w": float_text(quality.aggregate_iqr_lower_fence_w),
        "aggregate_iqr_upper_fence_w": float_text(quality.aggregate_iqr_upper_fence_w),
        "source_rows_without_replay_event": str(quality.source_rows_without_replay_event),
        "cleaned_records_written": str(quality.output_rows_written),
        "conversion_method": CONVERSION_METHOD,
        "final_energy_unit": "kWh per estimated interval",
        "interpolation_policy": "none",
        "outlier_treatment": "IQR diagnostic flags only; no aggregate values removed or capped",
    }


def overall_quality_row(qualities: list[HouseholdQuality]) -> dict[str, str]:
    numeric_names = [
        "source_rows_selected",
        "valid_timestamp_rows",
        "valid_aggregate_rows",
        "invalid_timestamp_rows",
        "invalid_aggregate_rows",
        "negative_aggregate_rows",
        "zero_aggregate_rows_retained",
        "source_issues_marked_rows_retained",
        "duplicate_timestamp_rows_excluded",
        "out_of_order_timestamp_rows_excluded",
        "boundary_rows_no_predecessor",
        "predecessor_invalid_rows",
        "intervals_observed",
        "replayable_intervals",
        "native_intervals_7_to_9_seconds",
        "sub_nominal_intervals_1_to_6_seconds",
        "short_irregular_intervals_10_to_16_seconds",
        "non_integrable_gap_intervals_over_16_seconds",
        "gaps_17_to_60_seconds",
        "gaps_over_60_seconds",
        "total_replayable_interval_seconds",
        "iqr_outlier_source_rows_retained",
        "source_rows_without_replay_event",
        "output_rows_written",
    ]
    totals = {name: sum(getattr(item, name) for item in qualities) for name in numeric_names}
    total_energy = sum(item.estimated_replayable_energy_kwh for item in qualities)
    return {
        "scope": "overall_selected_five_households",
        "household_id": "ALL",
        "source_filename": ";".join(item.window.source_filename for item in qualities),
        "selected_window_start_utc": "multiple; see household rows",
        "selected_window_end_utc": "multiple; see household rows",
        "solar_interference_documented": "true for Houses 3 and 11",
        "known_source_caveat": (
            "Houses 3 and 11 have documented solar-generation interference and are retained unmodified."
        ),
        "source_rows_selected": str(totals["source_rows_selected"]),
        "valid_timestamp_rows": str(totals["valid_timestamp_rows"]),
        "valid_aggregate_rows": str(totals["valid_aggregate_rows"]),
        "invalid_timestamp_rows": str(totals["invalid_timestamp_rows"]),
        "invalid_aggregate_rows": str(totals["invalid_aggregate_rows"]),
        "negative_aggregate_rows": str(totals["negative_aggregate_rows"]),
        "zero_aggregate_rows_retained": str(totals["zero_aggregate_rows_retained"]),
        "source_issues_marked_rows_retained": str(totals["source_issues_marked_rows_retained"]),
        "duplicate_timestamp_rows_excluded": str(totals["duplicate_timestamp_rows_excluded"]),
        "out_of_order_timestamp_rows_excluded": str(totals["out_of_order_timestamp_rows_excluded"]),
        "boundary_rows_no_predecessor": str(totals["boundary_rows_no_predecessor"]),
        "predecessor_invalid_rows": str(totals["predecessor_invalid_rows"]),
        "intervals_observed": str(totals["intervals_observed"]),
        "replayable_intervals": str(totals["replayable_intervals"]),
        "replayable_interval_share": float_text(
            percent(totals["replayable_intervals"], totals["intervals_observed"])
        ),
        "native_intervals_7_to_9_seconds": str(totals["native_intervals_7_to_9_seconds"]),
        "sub_nominal_intervals_1_to_6_seconds": str(totals["sub_nominal_intervals_1_to_6_seconds"]),
        "short_irregular_intervals_10_to_16_seconds": str(
            totals["short_irregular_intervals_10_to_16_seconds"]
        ),
        "non_integrable_gap_intervals_over_16_seconds": str(
            totals["non_integrable_gap_intervals_over_16_seconds"]
        ),
        "gaps_17_to_60_seconds": str(totals["gaps_17_to_60_seconds"]),
        "gaps_over_60_seconds": str(totals["gaps_over_60_seconds"]),
        "max_observed_positive_delta_seconds": str(
            max(item.max_observed_positive_delta_seconds for item in qualities)
        ),
        "total_replayable_interval_seconds": str(totals["total_replayable_interval_seconds"]),
        "estimated_replayable_energy_kwh": float_text(total_energy),
        "iqr_outlier_source_rows_retained": str(totals["iqr_outlier_source_rows_retained"]),
        "aggregate_q1_w": "not_aggregated",
        "aggregate_q3_w": "not_aggregated",
        "aggregate_iqr_lower_fence_w": "not_aggregated",
        "aggregate_iqr_upper_fence_w": "not_aggregated",
        "source_rows_without_replay_event": str(totals["source_rows_without_replay_event"]),
        "cleaned_records_written": str(totals["output_rows_written"]),
        "conversion_method": CONVERSION_METHOD,
        "final_energy_unit": "kWh per estimated interval",
        "interpolation_policy": "none",
        "outlier_treatment": "IQR diagnostic flags only; no aggregate values removed or capped",
    }


def write_summary(
    output_path: Path,
    *,
    qualities: list[HouseholdQuality],
    output_hashes: dict[str, str],
    selection_path: Path,
    source_hashes: dict[str, str],
) -> None:
    total_rows = sum(item.source_rows_selected for item in qualities)
    total_events = sum(item.output_rows_written for item in qualities)
    total_excluded_gaps = sum(item.non_integrable_gap_intervals_over_16_seconds for item in qualities)
    total_energy = sum(item.estimated_replayable_energy_kwh for item in qualities)
    lines = [
        "# REFIT Task 2 — Data Cleaning and Energy Normalization Summary",
        "",
        "## Scope and source decision",
        "",
        "This artifact covers only the five checksum-verified official REFIT source files and the inclusive 14-day windows selected reproducibly in Task 1. The source `Aggregate` field is documented active power in Watts (W), not interval energy or cumulative kWh. The project ingestion contract treats `energyConsumed` as an additive kWh value, so raw Watts are not replay-ready.",
        "",
        "The canonical ordering key is the source `Unix` field. It is converted to ISO-8601 UTC for output. The human-readable REFIT `Time` field is retained as source traceability metadata; no timezone assumption is made about that text field.",
        "",
        "## Conversion and cleaning policy",
        "",
        "For two adjacent valid observations `(t[i-1], P[i-1])` and `(t[i], P[i])`, the generated event is the declared numerical estimate:",
        "",
        "```text",
        "E[i] (kWh) = ((P[i-1] + P[i]) / 2) × (t[i] - t[i-1]) / 3,600,000",
        "```",
        "",
        "The calculation uses the actual positive Unix-time delta, not a fixed 8-second multiplier. It is trapezoidal integration of discrete active-power samples and must not be described as a directly metered interval-energy field.",
        "",
        f"A pair is replayable only when `0 < delta_seconds <= {MAX_INTEGRATABLE_GAP_SECONDS}`. The {MAX_INTEGRATABLE_GAP_SECONDS}-second limit equals two nominal REFIT sampling periods and was chosen conservatively to avoid estimating consumption across material gaps. For a longer interval, no interpolation, forward fill, zero fill, duration cap, or synthetic energy value is used. The cross-gap event is excluded from `cleaned_dataset.csv`, logged in `preprocessing_actions.csv`, and the valid post-gap reading becomes the next anchor.",
        "",
        "Zero-W observations are retained. Negative, non-finite, duplicate, out-of-order, and invalid-timestamp observations are handled explicitly if encountered. Aggregate-W IQR flags are diagnostic only; no aggregate value is capped or removed. In particular, the REFIT source's documented 4,000-W handling concerns appliance IAM channels, not the aggregate channel, and is not applied here. The source `Issues` field is preserved verbatim and is not interpreted as an anomaly label or an exclusion criterion.",
        "",
        "## Important upstream-data caveat",
        "",
        "The files are REFIT publisher-cleaned source files. This task does not reconstruct raw data or claim to undo upstream cleaning. Houses 3 and 11 have source-documented solar-generation interference; they are retained unmodified for robustness/replay coverage but must be reported as a declared sensitivity cohort for household-consumption claims. House 1 is reported by the descriptor as rewired to eliminate solar contribution.",
        "",
        "## Observed Task 2 output",
        "",
        f"- Selected source rows processed: **{total_rows:,}**",
        f"- Replayable normalized interval-energy records written: **{total_events:,}**",
        f"- Cross-gap intervals excluded because `delta_seconds > {MAX_INTEGRATABLE_GAP_SECONDS}`: **{total_excluded_gaps:,}**",
        f"- Sum of generated interval-energy estimates over retained intervals: **{total_energy:.12g} kWh**",
        "",
        "| Household | Source rows | Replayable records | Gap exclusions (>16 s) | Estimated retained energy (kWh) | Solar caveat |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for item in qualities:
        caveat = "Documented interference" if item.window.household_id in SOLAR_INTERFERENCE_DOCUMENTED else "No active caveat"
        lines.append(
            "| {household} | {rows:,} | {events:,} | {gaps:,} | {energy:.12g} | {caveat} |".format(
                household=item.window.household_id,
                rows=item.source_rows_selected,
                events=item.output_rows_written,
                gaps=item.non_integrable_gap_intervals_over_16_seconds,
                energy=item.estimated_replayable_energy_kwh,
                caveat=caveat,
            )
        )
    lines += [
        "",
        "## Files and reproducibility",
        "",
        "- `cleaned_dataset.csv`: replayable estimated interval-energy events only; final unit is kWh per interval.",
        "- `data_quality_report.csv`: household and combined quality counts, gap statistics, and diagnostic IQR statistics.",
        "- `preprocessing_actions.csv`: one audit action for every selected source row, including every exclusion reason.",
        "- `preprocessing_manifest.json`: script configuration, selected source provenance, and output hashes.",
        "",
        "Re-run from the repository root:",
        "",
        "```powershell",
        "python scripts/refit_task2_preprocess.py",
        "```",
        "",
        "This task did not send data to the API Gateway, start replay, train a model, inject anomalies, generate alerts, or update the research paper. Those are later tasks.",
        "",
        "### Input provenance",
        "",
        f"- Task 1 selection file: `{selection_path.as_posix()}` (SHA-256: `{sha256_file(selection_path)}`)",
    ]
    for filename, digest in sorted(source_hashes.items()):
        lines.append(f"- Source `{filename}` SHA-256: `{digest}`")
    lines += ["", "### Generated output SHA-256", ""]
    for filename, digest in sorted(output_hashes.items()):
        lines.append(f"- `{filename}`: `{digest}`")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fieldnames_for(rows: Iterable[dict[str, str]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields


def main() -> None:
    args = parse_args()
    selected_windows = load_selected_windows(args.selection_file)
    if len(selected_windows) != 5:
        raise ValueError(
            f"Task 2 is configured for the selected five-household subset; found {len(selected_windows)} selections."
        )
    for window in selected_windows:
        if window.end_unix <= window.start_unix:
            raise ValueError(f"Invalid selected time window for House {window.household_id}")
        input_path = args.input_dir / window.source_filename
        if not input_path.is_file():
            raise FileNotFoundError(f"Selected source file not found: {input_path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".task2_staging_", dir=args.output_dir))
    try:
        cleaned_path = staging / "cleaned_dataset.csv"
        actions_path = staging / "preprocessing_actions.csv"
        quality_path = staging / "data_quality_report.csv"
        manifest_path = staging / "preprocessing_manifest.json"
        summary_path = staging / "preprocessing_summary.md"

        cleaned_fields = [
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
        action_fields = [
            "household_id",
            "source_filename",
            "source_row_number",
            "source_time_text",
            "source_unix",
            "source_timestamp_utc",
            "aggregate_w_raw",
            "source_issues_raw",
            "source_quality_issue_flag",
            "solar_interference_documented",
            "previous_source_row_number",
            "previous_source_unix",
            "previous_timestamp_utc",
            "interval_seconds",
            "iqr_outlier_diagnostic_flag",
            "action",
            "reason",
            "cleaned_event_written",
        ]

        qualities: list[HouseholdQuality] = []
        source_hashes: dict[str, str] = {}
        with cleaned_path.open("w", encoding="utf-8", newline="") as cleaned_handle, actions_path.open(
            "w", encoding="utf-8", newline=""
        ) as actions_handle:
            cleaned_writer = csv.DictWriter(cleaned_handle, fieldnames=cleaned_fields)
            action_writer = csv.DictWriter(actions_handle, fieldnames=action_fields)
            cleaned_writer.writeheader()
            action_writer.writeheader()
            for window in selected_windows:
                input_path = args.input_dir / window.source_filename
                source_hashes[window.source_filename] = sha256_file(input_path)
                selected_rows = read_selected_source_rows(input_path, window)
                quality = HouseholdQuality(window=window)
                write_household_records(selected_rows, quality, cleaned_writer, action_writer)
                qualities.append(quality)

        quality_rows = [quality_row(item) for item in qualities]
        quality_rows.append(overall_quality_row(qualities))
        quality_fields = fieldnames_for(quality_rows)
        with quality_path.open("w", encoding="utf-8", newline="") as quality_handle:
            quality_writer = csv.DictWriter(quality_handle, fieldnames=quality_fields)
            quality_writer.writeheader()
            quality_writer.writerows(quality_rows)

        preliminary_hashes = {
            cleaned_path.name: sha256_file(cleaned_path),
            actions_path.name: sha256_file(actions_path),
            quality_path.name: sha256_file(quality_path),
        }
        manifest = {
            "task": "Task 2 — data cleaning and energy normalization",
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "measurement_semantics": {
                "source_field": "Aggregate",
                "source_unit": "active power W",
                "source_is_interval_energy": False,
                "chronology_field": "Unix",
                "timezone_output": "UTC derived from Unix; Time retained without inferred timezone",
            },
            "normalization": {
                "output_field": "estimated_interval_energy_kwh",
                "output_unit": "kWh per estimated interval",
                "formula": "((previous_aggregate_w + aggregate_w) / 2) * interval_seconds / 3600000",
                "conversion_method": CONVERSION_METHOD,
                "nominal_sample_seconds": NOMINAL_SAMPLE_SECONDS,
                "native_interval_range_seconds": [NATIVE_MIN_SECONDS, NATIVE_MAX_SECONDS],
                "max_integratable_gap_seconds": MAX_INTEGRATABLE_GAP_SECONDS,
                "gap_policy": "exclude cross-gap event; no interpolation, fill, duration cap, or synthetic energy",
                "outlier_policy": "IQR diagnostic only; no aggregate clipping/removal",
                "source_issues_policy": "preserve verbatim; not used as an anomaly label or exclusion criterion",
            },
            "selected_windows": [
                {
                    "household_id": item.household_id,
                    "source_filename": item.source_filename,
                    "start_utc": item.start_utc,
                    "end_utc": item.end_utc,
                    "selection_reason": item.selection_reason,
                    "solar_interference_documented": item.household_id in SOLAR_INTERFERENCE_DOCUMENTED,
                }
                for item in selected_windows
            ],
            "input_hashes_sha256": source_hashes,
            "selection_file": str(args.selection_file.as_posix()),
            "selection_file_sha256": sha256_file(args.selection_file),
            "script_path": "scripts/refit_task2_preprocess.py",
            "script_sha256": sha256_file(Path(__file__)),
            "output_hashes_sha256": preliminary_hashes,
            "outputs": {
                "cleaned_dataset.csv": "Replayable normalized interval-energy records only.",
                "data_quality_report.csv": "Per-household and total data-quality counts.",
                "preprocessing_actions.csv": "One logged action for each selected source row.",
                "preprocessing_summary.md": "Human-readable method and results summary.",
            },
            "not_performed": [
                "API replay",
                "ML training or evaluation",
                "synthetic anomaly injection",
                "alert generation",
                "research-paper update",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        # A file cannot truthfully contain its own final checksum without a
        # recursive fixed-point construction.  The summary and manifest list
        # checksums for the substantive generated data artifacts; the manifest
        # itself is independently hashable after the run.
        output_hashes = {
            cleaned_path.name: sha256_file(cleaned_path),
            actions_path.name: sha256_file(actions_path),
            quality_path.name: sha256_file(quality_path),
        }
        write_summary(
            summary_path,
            qualities=qualities,
            output_hashes=output_hashes,
            selection_path=args.selection_file,
            source_hashes=source_hashes,
        )
        # Include the summary's hash in the final manifest without making the
        # manifest self-referential. The manifest's own final checksum is
        # intentionally not embedded in either file.
        output_hashes[summary_path.name] = sha256_file(summary_path)
        manifest["output_hashes_sha256"] = output_hashes
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        for staged_path in (cleaned_path, actions_path, quality_path, manifest_path, summary_path):
            staged_path.replace(args.output_dir / staged_path.name)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == "__main__":
    main()
