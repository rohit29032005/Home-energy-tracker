#!/usr/bin/env python3
"""Task 2: auditable REFIT aggregate-power cleaning and energy normalization.

This script reads only the checksum-verified REFIT CSV files selected in Task 1.
It never writes raw data, calls an API, replays measurements, trains a model,
generates anomalies, changes Docker, or changes the research paper.

The REFIT Aggregate field is documented whole-house active power in W, not
interval energy. The source does not establish whether each reading is a point
sample or interval average. For a transparent, source-aligned estimate, this
script uses a left-rectangle/sample-hold estimate anchored at the interval-start
reading: E = P_start * actual_delta_seconds / 3,600,000 kWh. This is estimated
interval energy, not a utility-metered kWh measurement.
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
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


@dataclass(frozen=True)
class SelectedWindow:
    household_id: int
    filename: str
    start_unix: int
    end_unix: int
    start_utc: str
    end_utc: str
    selection_reason: str


@dataclass
class RawRecord:
    household_id: int
    filename: str
    row_number: int
    time_text: str
    unix_text: str
    unix: int
    aggregate_text: str
    aggregate_w: float | None
    aggregate_status: str
    issues_text: str
    time_matches_unix_utc: bool | None


@dataclass
class IntervalStatistics:
    nominal_seconds: int
    max_integratable_seconds: int
    previous_unix: int | None = None
    positive_interval_count: int = 0
    interval_seconds_sum: int = 0
    interval_counts: Counter[int] = field(default_factory=Counter)
    min_interval_seconds: int | None = None
    max_interval_seconds: int | None = None
    duplicate_timestamp_count: int = 0
    out_of_order_timestamp_count: int = 0
    intervals_over_nominal_count: int = 0
    estimated_missing_nominal_slots: int = 0
    intervals_over_integratable_limit_count: int = 0
    intervals_over_60_seconds_count: int = 0
    intervals_over_3600_seconds_count: int = 0

    def observe(self, timestamp: int) -> None:
        if self.previous_unix is None:
            self.previous_unix = timestamp
            return
        delta = timestamp - self.previous_unix
        if delta == 0:
            self.duplicate_timestamp_count += 1
            return
        if delta < 0:
            self.out_of_order_timestamp_count += 1
            return
        self.previous_unix = timestamp
        self.positive_interval_count += 1
        self.interval_seconds_sum += delta
        self.interval_counts[delta] += 1
        self.min_interval_seconds = delta if self.min_interval_seconds is None else min(self.min_interval_seconds, delta)
        self.max_interval_seconds = delta if self.max_interval_seconds is None else max(self.max_interval_seconds, delta)
        if delta > self.nominal_seconds:
            self.intervals_over_nominal_count += 1
            # An estimate only: time jitter means this is not a count of proven lost samples.
            self.estimated_missing_nominal_slots += max(0, round(delta / self.nominal_seconds) - 1)
        if delta > self.max_integratable_seconds:
            self.intervals_over_integratable_limit_count += 1
        if delta > 60:
            self.intervals_over_60_seconds_count += 1
        if delta > 3600:
            self.intervals_over_3600_seconds_count += 1

    def median_seconds(self) -> float | None:
        if not self.positive_interval_count:
            return None
        left_rank = (self.positive_interval_count - 1) // 2
        right_rank = self.positive_interval_count // 2
        total = 0
        left_value: int | None = None
        right_value: int | None = None
        for seconds in sorted(self.interval_counts):
            total += self.interval_counts[seconds]
            if left_value is None and total > left_rank:
                left_value = seconds
            if total > right_rank:
                right_value = seconds
                break
        assert left_value is not None and right_value is not None
        return (left_value + right_value) / 2.0

    def mean_seconds(self) -> float | None:
        if not self.positive_interval_count:
            return None
        return self.interval_seconds_sum / self.positive_interval_count

    def native_share(self, native_min: int, native_max: int) -> float | None:
        if not self.positive_interval_count:
            return None
        native = sum(
            count for seconds, count in self.interval_counts.items() if native_min <= seconds <= native_max
        )
        return native / self.positive_interval_count

    def positive_duration_seconds(self) -> int:
        return self.interval_seconds_sum


@dataclass
class MeasurementAudit:
    nominal_seconds: int
    max_integratable_seconds: int
    row_count: int = 0
    valid_unix_count: int = 0
    invalid_unix_count: int = 0
    human_time_pattern_valid_count: int = 0
    human_time_pattern_invalid_count: int = 0
    time_unix_utc_crosschecks: int = 0
    time_unix_utc_match_count: int = 0
    time_unix_utc_mismatch_count: int = 0
    valid_aggregate_count: int = 0
    missing_aggregate_count: int = 0
    invalid_aggregate_count: int = 0
    nonfinite_aggregate_count: int = 0
    negative_aggregate_count: int = 0
    zero_aggregate_count: int = 0
    source_issues_marked_count: int = 0
    intervals: IntervalStatistics = field(init=False)

    def __post_init__(self) -> None:
        self.intervals = IntervalStatistics(
            nominal_seconds=self.nominal_seconds,
            max_integratable_seconds=self.max_integratable_seconds,
        )

    def observe(
        self,
        time_text: str,
        unix: int | None,
        aggregate_status: str,
        aggregate_w: float | None,
        issues_text: str,
        crosscheck_time_against_unix: bool,
    ) -> bool | None:
        self.row_count += 1
        if TIME_PATTERN.match(time_text):
            self.human_time_pattern_valid_count += 1
        else:
            self.human_time_pattern_invalid_count += 1
        time_matches: bool | None = None
        if unix is None:
            self.invalid_unix_count += 1
        else:
            self.valid_unix_count += 1
            self.intervals.observe(unix)
            if crosscheck_time_against_unix:
                self.time_unix_utc_crosschecks += 1
                time_matches = unix_to_utc_text(unix) == time_text
                if time_matches:
                    self.time_unix_utc_match_count += 1
                else:
                    self.time_unix_utc_mismatch_count += 1
        if aggregate_status == "VALID":
            self.valid_aggregate_count += 1
            if aggregate_w == 0:
                self.zero_aggregate_count += 1
        elif aggregate_status == "MISSING_AGGREGATE":
            self.missing_aggregate_count += 1
        elif aggregate_status == "NONFINITE_AGGREGATE":
            self.nonfinite_aggregate_count += 1
        elif aggregate_status == "NEGATIVE_AGGREGATE":
            self.negative_aggregate_count += 1
        else:
            self.invalid_aggregate_count += 1
        if source_issue_marked(issues_text):
            self.source_issues_marked_count += 1
        return time_matches


@dataclass
class FileInspection:
    household_id: int
    window: SelectedWindow
    file_path: Path
    file_size_bytes: int
    file_md5: str
    file_sha256: str
    header: list[str]
    full: MeasurementAudit
    selected: MeasurementAudit
    selected_records: list[RawRecord]


@dataclass
class ProcessingResult:
    household_id: int
    cohort: str
    source_filename: str
    selected_rows: int
    cleaned_records: int = 0
    excluded_records: int = 0
    exclusion_counts: Counter[str] = field(default_factory=Counter)
    total_interval_seconds: int = 0
    estimated_energy_kwh: float = 0.0
    iqr_q1_w: float | None = None
    iqr_q3_w: float | None = None
    iqr_lower_fence_w: float | None = None
    iqr_upper_fence_w: float | None = None
    iqr_diagnostic_count: int = 0
    manual_example: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 2 REFIT preprocessing, without replay or ML.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("preprocessing_config.yaml"),
        help="JSON-compatible YAML configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory, resolved from repository root when relative.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace only this script's named artifacts in the chosen output directory.",
    )
    return parser.parse_args()


def read_config(path: Path) -> dict[str, Any]:
    try:
        # The committed .yaml file is deliberately JSON-compatible YAML 1.2, avoiding a third-party dependency.
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read JSON-compatible YAML config {path}: {exc}") from exc


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_hashes(path: Path) -> tuple[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return md5.hexdigest(), sha256.hexdigest()


def text(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def unix_to_utc_text(value: int) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def unix_to_utc_iso(value: int | None) -> str:
    if value is None:
        return ""
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_epoch(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        number = float(value.strip())
    except ValueError:
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def parse_aggregate(value: str | None) -> tuple[float | None, str]:
    if value is None or not value.strip():
        return None, "MISSING_AGGREGATE"
    try:
        number = float(value.strip())
    except ValueError:
        return None, "INVALID_AGGREGATE"
    if not math.isfinite(number):
        return None, "NONFINITE_AGGREGATE"
    if number < 0:
        return number, "NEGATIVE_AGGREGATE"
    return number, "VALID"


def source_issue_marked(value: str) -> bool:
    return value.strip() not in {"", "0", "0.0"}


def parse_iso_epoch(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Task 1 selection time is not timezone-aware: {value!r}")
    return int(parsed.timestamp())


def load_selected_windows(path: Path) -> list[SelectedWindow]:
    selected: list[SelectedWindow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        needed = {
            "household",
            "source_filename",
            "selection_status",
            "selection_reason",
            "best_window_start_utc",
            "best_window_end_utc",
        }
        absent = needed - set(reader.fieldnames or [])
        if absent:
            raise ValueError(f"Task 1 selection file misses columns: {', '.join(sorted(absent))}")
        for row in reader:
            if row["selection_status"].strip() != "SELECTED":
                continue
            household_id = int(row["household"])
            selected.append(
                SelectedWindow(
                    household_id=household_id,
                    filename=row["source_filename"].strip(),
                    start_unix=parse_iso_epoch(row["best_window_start_utc"].strip()),
                    end_unix=parse_iso_epoch(row["best_window_end_utc"].strip()),
                    start_utc=row["best_window_start_utc"].strip(),
                    end_utc=row["best_window_end_utc"].strip(),
                    selection_reason=row["selection_reason"].strip(),
                )
            )
    if not selected:
        raise ValueError("Task 1 selection file contains no selected household.")
    return sorted(selected, key=lambda item: item.household_id)


def inspect_source(
    window: SelectedWindow,
    input_directory: Path,
    config: dict[str, Any],
) -> FileInspection:
    sampling = config["sampling"]
    full = MeasurementAudit(
        nominal_seconds=int(sampling["nominal_interval_seconds"]),
        max_integratable_seconds=int(sampling["maximum_integratable_interval_seconds"]),
    )
    selected = MeasurementAudit(
        nominal_seconds=int(sampling["nominal_interval_seconds"]),
        max_integratable_seconds=int(sampling["maximum_integratable_interval_seconds"]),
    )
    file_path = input_directory / window.filename
    if not file_path.is_file():
        raise FileNotFoundError(f"Selected REFIT source is absent: {file_path}")
    file_md5, file_sha256 = file_hashes(file_path)
    expected_md5 = config["expected_source_md5"].get(window.filename)
    if expected_md5 is None:
        raise ValueError(f"No expected source MD5 configured for {window.filename}")
    if file_md5.lower() != str(expected_md5).lower():
        raise ValueError(
            f"MD5 mismatch for {window.filename}: expected {expected_md5}, got {file_md5}. Raw file was not used."
        )

    mapping = config["column_mapping"]
    required = set(config["required_columns"])
    selected_records: list[RawRecord] = []
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        absent = required - set(header)
        if absent:
            raise ValueError(f"{window.filename} lacks required columns: {', '.join(sorted(absent))}")
        for row_number, row in enumerate(reader, start=2):
            time_text = (row.get(mapping["human_time"]) or "").strip()
            unix_text = (row.get(mapping["unix_time"]) or "").strip()
            aggregate_text = (row.get(mapping["aggregate_power"]) or "").strip()
            issues_text = (row.get(mapping["source_issues"]) or "").strip()
            unix = parse_epoch(unix_text)
            aggregate_w, aggregate_status = parse_aggregate(aggregate_text)
            full.observe(
                time_text,
                unix,
                aggregate_status,
                aggregate_w,
                issues_text,
                crosscheck_time_against_unix=False,
            )
            if unix is None or unix < window.start_unix or unix > window.end_unix:
                continue
            time_matches = selected.observe(
                time_text,
                unix,
                aggregate_status,
                aggregate_w,
                issues_text,
                crosscheck_time_against_unix=True,
            )
            selected_records.append(
                RawRecord(
                    household_id=window.household_id,
                    filename=window.filename,
                    row_number=row_number,
                    time_text=time_text,
                    unix_text=unix_text,
                    unix=unix,
                    aggregate_text=aggregate_text,
                    aggregate_w=aggregate_w,
                    aggregate_status=aggregate_status,
                    issues_text=issues_text,
                    time_matches_unix_utc=time_matches,
                )
            )
    return FileInspection(
        household_id=window.household_id,
        window=window,
        file_path=file_path,
        file_size_bytes=file_path.stat().st_size,
        file_md5=file_md5,
        file_sha256=file_sha256,
        header=header,
        full=full,
        selected=selected,
        selected_records=selected_records,
    )


def quantile(values: Iterable[float], probability: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    location = (len(ordered) - 1) * probability
    lower = math.floor(location)
    upper = math.ceil(location)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - location) + ordered[upper] * (location - lower)


def iqr_fences(values: Iterable[float]) -> tuple[float | None, float | None, float | None, float | None]:
    # Materialise once: a generator passed by the caller must be available for
    # both quantiles. This is diagnostic only and never removes a measurement.
    materialized = list(values)
    q1 = quantile(materialized, 0.25)
    q3 = quantile(materialized, 0.75)
    if q1 is None or q3 is None:
        return q1, q3, None, None
    iqr = q3 - q1
    return q1, q3, q1 - 1.5 * iqr, q3 + 1.5 * iqr


def is_iqr_diagnostic(value: float | None, lower: float | None, upper: float | None) -> bool:
    return value is not None and lower is not None and upper is not None and (value < lower or value > upper)


def cohort_for(household_id: int, config: dict[str, Any]) -> str:
    cohorts = config["cohorts"]
    if household_id in cohorts["primary"]:
        return "primary"
    if household_id in cohorts["solar_sensitivity"]:
        return "solar_sensitivity"
    raise ValueError(f"House {household_id} is selected by Task 1 but absent from the configured cohorts.")


def solar_caveat(household_id: int) -> str:
    if household_id in {3, 11}:
        return (
            "Documented REFIT solar-generation interference; aggregate is retained without a solar/net-export correction."
        )
    if household_id == 1:
        return "REFIT descriptor reports House 1 was rewired to eliminate solar contribution."
    return "No documented solar-interference caveat applied to this primary cohort record."


def flags_for(
    record: RawRecord,
    delta_seconds: int | None,
    iqr_flag: bool,
    household_id: int,
    sampling: dict[str, Any],
) -> str:
    flags: list[str] = []
    if delta_seconds is not None:
        native_min = int(sampling["native_interval_min_seconds"])
        native_max = int(sampling["native_interval_max_seconds"])
        if native_min <= delta_seconds <= native_max:
            flags.append("NATIVE_CADENCE")
        elif 1 <= delta_seconds < native_min:
            flags.append("SUB_NOMINAL_CADENCE")
        else:
            flags.append("SHORT_IRREGULAR_CADENCE")
    if record.aggregate_w == 0:
        flags.append("ZERO_POWER_RETAINED")
    if source_issue_marked(record.issues_text):
        flags.append("SOURCE_ISSUES_MARKED")
    if iqr_flag:
        flags.append("IQR_OUTLIER_DIAGNOSTIC_ONLY")
    if household_id in {3, 11}:
        flags.append("SOLAR_INTERFERENCE_DOCUMENTED")
    return "|".join(flags) if flags else "NONE"


def excluded_row(
    record: RawRecord,
    cohort: str,
    reason_code: str,
    reason: str,
    predecessor: RawRecord | None,
    interval_seconds: int | None,
    iqr_flag: bool,
) -> dict[str, str]:
    return {
        "household_id": str(record.household_id),
        "cohort": cohort,
        "source_filename": record.filename,
        "source_row_number": str(record.row_number),
        "original_time_text": record.time_text,
        "original_unix": record.unix_text,
        "timestamp_utc_from_unix": unix_to_utc_iso(record.unix),
        "original_aggregate_power_w": record.aggregate_text,
        "aggregate_parse_status": record.aggregate_status,
        "source_issues_raw": record.issues_text,
        "source_issue_marked": str(source_issue_marked(record.issues_text)).lower(),
        "solar_interference_documented": str(record.household_id in {3, 11}).lower(),
        "related_predecessor_row_number": "" if predecessor is None else str(predecessor.row_number),
        "related_predecessor_unix": "" if predecessor is None else predecessor.unix_text,
        "interval_seconds": text(interval_seconds),
        "iqr_outlier_diagnostic_flag": str(iqr_flag).lower(),
        "exclusion_rule": reason_code,
        "reason": reason,
    }


def cleaned_row(
    anchor: RawRecord,
    successor: RawRecord,
    cohort: str,
    interval_seconds: int,
    energy_kwh: float,
    iqr_flag: bool,
    config: dict[str, Any],
) -> dict[str, str]:
    sampling = config["sampling"]
    return {
        "household_id": str(anchor.household_id),
        "cohort": cohort,
        "source_filename": anchor.filename,
        "source_row_number": str(anchor.row_number),
        "original_time_text": anchor.time_text,
        "original_unix": anchor.unix_text,
        "timestamp_utc_from_unix": unix_to_utc_iso(anchor.unix),
        "original_aggregate_power_w": text(anchor.aggregate_w),
        "interval_end_source_row_number": str(successor.row_number),
        "interval_end_unix": successor.unix_text,
        "interval_end_timestamp_utc_from_unix": unix_to_utc_iso(successor.unix),
        "interval_end_aggregate_power_w": text(successor.aggregate_w),
        "interval_seconds": str(interval_seconds),
        "derived_interval_energy_kwh": text(energy_kwh),
        "energy_integration_method": config["normalization"]["energy_method"],
        "interval_classification": (
            "native_7_to_9_seconds"
            if int(sampling["native_interval_min_seconds"]) <= interval_seconds <= int(sampling["native_interval_max_seconds"])
            else (
                "sub_nominal_1_to_6_seconds"
                if 1 <= interval_seconds < int(sampling["native_interval_min_seconds"])
                else "short_irregular_10_to_16_seconds"
            )
        ),
        "data_quality_flags": flags_for(anchor, interval_seconds, iqr_flag, anchor.household_id, sampling),
        "source_issues_raw": anchor.issues_text,
        "source_issue_marked": str(source_issue_marked(anchor.issues_text)).lower(),
        "solar_interference_documented": str(anchor.household_id in {3, 11}).lower(),
        "known_source_caveat": solar_caveat(anchor.household_id),
    }


def process_records(
    inspection: FileInspection,
    config: dict[str, Any],
    primary_writer: csv.DictWriter,
    solar_writer: csv.DictWriter,
    excluded_writer: csv.DictWriter,
) -> ProcessingResult:
    cohort = cohort_for(inspection.household_id, config)
    result = ProcessingResult(
        household_id=inspection.household_id,
        cohort=cohort,
        source_filename=inspection.window.filename,
        selected_rows=len(inspection.selected_records),
    )
    valid_values = [record.aggregate_w for record in inspection.selected_records if record.aggregate_status == "VALID"]
    q1, q3, lower, upper = iqr_fences(value for value in valid_values if value is not None)
    result.iqr_q1_w, result.iqr_q3_w = q1, q3
    result.iqr_lower_fence_w, result.iqr_upper_fence_w = lower, upper
    writer = primary_writer if cohort == "primary" else solar_writer
    max_delta = int(config["sampling"]["maximum_integratable_interval_seconds"])
    anchor: RawRecord | None = None
    last_timestamp: int | None = None

    def log_exclusion(
        record: RawRecord,
        reason_code: str,
        reason: str,
        predecessor: RawRecord | None = None,
        delta_seconds: int | None = None,
    ) -> None:
        flag = is_iqr_diagnostic(record.aggregate_w, lower, upper)
        if flag:
            result.iqr_diagnostic_count += 1
        excluded_writer.writerow(
            excluded_row(record, cohort, reason_code, reason, predecessor, delta_seconds, flag)
        )
        result.excluded_records += 1
        result.exclusion_counts[reason_code] += 1

    for record in inspection.selected_records:
        # All records in this list have a valid Unix timestamp because it was needed for the selected-window test.
        assert record.unix is not None
        if last_timestamp is not None and record.unix == last_timestamp:
            log_exclusion(
                record,
                "DUPLICATE_TIMESTAMP",
                "A duplicate Unix timestamp is not merged or overwritten.",
                anchor,
                0,
            )
            continue
        if last_timestamp is not None and record.unix < last_timestamp:
            log_exclusion(
                record,
                "OUT_OF_ORDER_TIMESTAMP",
                "An out-of-order Unix timestamp is excluded instead of silently sorting source observations.",
                anchor,
                record.unix - last_timestamp,
            )
            continue
        last_timestamp = record.unix

        if record.aggregate_status != "VALID":
            if anchor is not None:
                log_exclusion(
                    anchor,
                    "INVALID_SUCCESSOR_PREVENTS_INTERVAL",
                    "The interval-start reading has no valid next aggregate reading for an additive energy estimate.",
                    record,
                    record.unix - anchor.unix,
                )
                anchor = None
            log_exclusion(
                record,
                record.aggregate_status,
                "The aggregate reading is retained in this audit but not converted to additive interval energy.",
                None,
                None,
            )
            continue

        if anchor is None:
            anchor = record
            continue

        delta_seconds = record.unix - anchor.unix
        if delta_seconds <= 0:
            # Defensive branch: timestamp state above should already handle this.
            log_exclusion(
                record,
                "NONPOSITIVE_INTERVAL",
                "Non-positive elapsed time cannot support an interval-energy estimate.",
                anchor,
                delta_seconds,
            )
            continue
        if delta_seconds > max_delta:
            log_exclusion(
                anchor,
                "GAP_OVER_16_SECONDS",
                "Cross-gap energy is excluded; no interpolation, forward fill, zero fill, or duration cap is applied.",
                record,
                delta_seconds,
            )
            anchor = record
            continue

        assert anchor.aggregate_w is not None
        energy_kwh = anchor.aggregate_w * delta_seconds / 3_600_000.0
        anchor_iqr_flag = is_iqr_diagnostic(anchor.aggregate_w, lower, upper)
        if anchor_iqr_flag:
            result.iqr_diagnostic_count += 1
        writer.writerow(cleaned_row(anchor, record, cohort, delta_seconds, energy_kwh, anchor_iqr_flag, config))
        result.cleaned_records += 1
        result.total_interval_seconds += delta_seconds
        result.estimated_energy_kwh += energy_kwh
        manual_is_native = (
            int(config["sampling"]["native_interval_min_seconds"])
            <= delta_seconds
            <= int(config["sampling"]["native_interval_max_seconds"])
        )
        current_example_is_native = (
            result.manual_example is not None
            and int(config["sampling"]["native_interval_min_seconds"])
            <= int(result.manual_example["interval_seconds"])
            <= int(config["sampling"]["native_interval_max_seconds"])
        )
        if result.manual_example is None or (manual_is_native and not current_example_is_native):
            result.manual_example = {
                "household_id": anchor.household_id,
                "source_row_number": anchor.row_number,
                "interval_start_power_w": anchor.aggregate_w,
                "interval_seconds": delta_seconds,
                "expected_energy_kwh": energy_kwh,
            }
        anchor = record

    if anchor is not None:
        log_exclusion(
            anchor,
            "NO_SUCCESSOR_AT_WINDOW_END",
            "The final selected reading has no successor within the selected window for a sample-hold interval estimate.",
            None,
            None,
        )
    if result.cleaned_records + result.excluded_records != result.selected_rows:
        raise AssertionError(
            f"House {inspection.household_id} reconciliation failed: {result.cleaned_records} cleaned + "
            f"{result.excluded_records} excluded != {result.selected_rows} selected."
        )
    return result


def interval_report_row(
    inspection: FileInspection,
    scope: str,
    audit: MeasurementAudit,
    config: dict[str, Any],
) -> dict[str, str]:
    sampling = config["sampling"]
    native_share = audit.intervals.native_share(
        int(sampling["native_interval_min_seconds"]), int(sampling["native_interval_max_seconds"])
    )
    return {
        "household_id": str(inspection.household_id),
        "cohort": cohort_for(inspection.household_id, config),
        "source_filename": inspection.window.filename,
        "scope": scope,
        "record_count": str(audit.row_count),
        "valid_unix_timestamp_count": str(audit.valid_unix_count),
        "invalid_unix_timestamp_count": str(audit.invalid_unix_count),
        "human_time_pattern_valid_count": str(audit.human_time_pattern_valid_count),
        "human_time_pattern_invalid_count": str(audit.human_time_pattern_invalid_count),
        "time_unix_utc_crosschecks": str(audit.time_unix_utc_crosschecks),
        "time_unix_utc_match_count": str(audit.time_unix_utc_match_count),
        "time_unix_utc_mismatch_count": str(audit.time_unix_utc_mismatch_count),
        "positive_interval_count": str(audit.intervals.positive_interval_count),
        "mean_interval_seconds": text(audit.intervals.mean_seconds()),
        "median_interval_seconds": text(audit.intervals.median_seconds()),
        "minimum_interval_seconds": text(audit.intervals.min_interval_seconds),
        "maximum_interval_seconds": text(audit.intervals.max_interval_seconds),
        "positive_elapsed_duration_seconds": str(audit.intervals.positive_duration_seconds()),
        "duplicate_timestamp_count": str(audit.intervals.duplicate_timestamp_count),
        "out_of_order_timestamp_count": str(audit.intervals.out_of_order_timestamp_count),
        "intervals_over_nominal_8_seconds_count": str(audit.intervals.intervals_over_nominal_count),
        "estimated_missing_nominal_slots": str(audit.intervals.estimated_missing_nominal_slots),
        "intervals_over_16_seconds_count": str(audit.intervals.intervals_over_integratable_limit_count),
        "intervals_over_60_seconds_count": str(audit.intervals.intervals_over_60_seconds_count),
        "intervals_over_3600_seconds_count": str(audit.intervals.intervals_over_3600_seconds_count),
        "native_7_to_9_second_share": text(native_share),
        "nominal_interval_seconds": str(sampling["nominal_interval_seconds"]),
        "maximum_integratable_interval_seconds": str(sampling["maximum_integratable_interval_seconds"]),
    }


def quality_report_row(
    inspection: FileInspection,
    result: ProcessingResult,
    config: dict[str, Any],
) -> dict[str, str]:
    return {
        "household_id": str(inspection.household_id),
        "cohort": result.cohort,
        "source_filename": inspection.window.filename,
        "source_file_size_bytes": str(inspection.file_size_bytes),
        "source_md5": inspection.file_md5,
        "source_sha256": inspection.file_sha256,
        "aggregate_column_selected": config["column_mapping"]["aggregate_power"],
        "aggregate_measurement_semantics": config["normalization"]["source_measurement"],
        "selected_window_start_utc": inspection.window.start_utc,
        "selected_window_end_utc": inspection.window.end_utc,
        "raw_file_record_count": str(inspection.full.row_count),
        "raw_valid_unix_timestamp_count": str(inspection.full.valid_unix_count),
        "raw_invalid_unix_timestamp_count": str(inspection.full.invalid_unix_count),
        "raw_valid_aggregate_count": str(inspection.full.valid_aggregate_count),
        "raw_missing_aggregate_count": str(inspection.full.missing_aggregate_count),
        "raw_invalid_aggregate_count": str(inspection.full.invalid_aggregate_count),
        "raw_nonfinite_aggregate_count": str(inspection.full.nonfinite_aggregate_count),
        "raw_negative_aggregate_count": str(inspection.full.negative_aggregate_count),
        "raw_zero_aggregate_count": str(inspection.full.zero_aggregate_count),
        "raw_source_issues_marked_count": str(inspection.full.source_issues_marked_count),
        "selected_window_record_count": str(result.selected_rows),
        "selected_valid_aggregate_count": str(inspection.selected.valid_aggregate_count),
        "selected_missing_aggregate_count": str(inspection.selected.missing_aggregate_count),
        "selected_invalid_aggregate_count": str(inspection.selected.invalid_aggregate_count),
        "selected_nonfinite_aggregate_count": str(inspection.selected.nonfinite_aggregate_count),
        "selected_negative_aggregate_count": str(inspection.selected.negative_aggregate_count),
        "selected_zero_aggregate_count": str(inspection.selected.zero_aggregate_count),
        "selected_source_issues_marked_count": str(inspection.selected.source_issues_marked_count),
        "cleaned_interval_record_count": str(result.cleaned_records),
        "excluded_source_record_count": str(result.excluded_records),
        "reconciliation_status": (
            "PASS" if result.cleaned_records + result.excluded_records == result.selected_rows else "FAIL"
        ),
        "estimated_integrated_duration_seconds": str(result.total_interval_seconds),
        "estimated_interval_energy_kwh_sum": text(result.estimated_energy_kwh),
        "iqr_q1_w": text(result.iqr_q1_w),
        "iqr_q3_w": text(result.iqr_q3_w),
        "iqr_lower_fence_w": text(result.iqr_lower_fence_w),
        "iqr_upper_fence_w": text(result.iqr_upper_fence_w),
        "iqr_diagnostic_flag_count": str(result.iqr_diagnostic_count),
        "solar_interference_documented": str(inspection.household_id in {3, 11}).lower(),
        "solar_caveat": solar_caveat(inspection.household_id),
        "source_time_timezone_statement": "Time retained verbatim; UTC output is derived from Unix and does not assign a timezone to Time text.",
        "selection_reason": inspection.window.selection_reason,
        "exclusion_counts_json": json.dumps(dict(sorted(result.exclusion_counts.items())), sort_keys=True),
    }


def write_summary(
    path: Path,
    inspections: list[FileInspection],
    results: list[ProcessingResult],
    output_hashes: dict[str, str],
    config: dict[str, Any],
) -> None:
    result_by_house = {result.household_id: result for result in results}
    primary_energy = sum(result.estimated_energy_kwh for result in results if result.cohort == "primary")
    solar_energy = sum(result.estimated_energy_kwh for result in results if result.cohort == "solar_sensitivity")
    primary_events = sum(result.cleaned_records for result in results if result.cohort == "primary")
    solar_events = sum(result.cleaned_records for result in results if result.cohort == "solar_sensitivity")
    lines = [
        "# Task 2 — REFIT Data Cleaning and Energy Normalization",
        "",
        "## Scope and provenance",
        "",
        "This artifact processes only the five checksum-verified, Task-1-selected REFIT cleaned CSV files. "
        "It does not modify raw source data, upload data, invoke the project API, replay data, train ML, generate anomalies, send alerts, alter Docker/backend/device-token configuration, or update the research paper.",
        "",
        "- Aggregate selected: `Aggregate` (whole-house active power, W).",
        "- Chronology selected: `Unix`; `Time` is retained verbatim. UTC strings in outputs are derived from `Unix`, not a claim that the source `Time` text is timezone-tagged.",
        "- Appliance channels were not summed: they are selected IAM channels and do not form a complete, synchronous household aggregate.",
        "- Houses 1, 2, and 4 are the primary cohort. Houses 3 and 11 remain a distinct solar-affected sensitivity cohort.",
        "",
        "## Normalization method",
        "",
        "`Aggregate` is active power, not kWh. The output `derived_interval_energy_kwh` is an **estimated** interval value using the left-rectangle/sample-hold rule:",
        "",
        "```text",
        "estimated_interval_energy_kwh = interval_start_aggregate_power_w × actual_interval_seconds / 3,600,000",
        "```",
        "",
        "Only `0 < actual_interval_seconds <= 16` is integrated. A 7–9 second interval is marked native; 10–16 seconds is short irregular. For a longer gap, no value is interpolated, filled, capped, or synthesized; the cross-gap interval is logged as excluded and the next valid reading becomes a new anchor.",
        "",
        "The REFIT source does not establish whether `Aggregate` is an instantaneous reading or an interval average. This is therefore a documented numerical estimate, not a claim of directly metered interval kWh. Valid high values are retained with an IQR diagnostic flag only. Source `Issues` values are preserved and are not anomaly labels.",
        "",
        "## Quality and output results",
        "",
        "| House | Cohort | Selected source rows | Cleaned interval records | Excluded source rows | Estimated retained energy (kWh) | Solar caveat |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for inspection in inspections:
        result = result_by_house[inspection.household_id]
        lines.append(
            "| {house} | {cohort} | {source_rows:,} | {cleaned:,} | {excluded:,} | {energy:.12g} | {solar} |".format(
                house=inspection.household_id,
                cohort=result.cohort,
                source_rows=result.selected_rows,
                cleaned=result.cleaned_records,
                excluded=result.excluded_records,
                energy=result.estimated_energy_kwh,
                solar="documented interference" if inspection.household_id in {3, 11} else "none documented",
            )
        )
    lines += [
        "",
        "Primary-cohort total: **{:.12g} kWh** across **{:,}** retained interval records.".format(
            primary_energy, primary_events
        ),
        "",
        "Solar-sensitivity-cohort total: **{:.12g} kWh** across **{:,}** retained interval records. "
        "This total must not be interpreted as a corrected net-import or consumption value.".format(solar_energy, solar_events),
        "",
        "## Manual unit-conversion validation",
        "",
    ]
    example = next((result.manual_example for result in results if result.manual_example is not None), None)
    if example is None:
        lines.append("No integrable interval was available; no manual conversion example can be reported.")
    else:
        lines += [
            "A retained record from House {house}, source row {row}, provides the manual check:".format(
                house=example["household_id"], row=example["source_row_number"]
            ),
            "",
            "```text",
            "P_start = {power} W".format(power=text(example["interval_start_power_w"])),
            "Δt = {seconds} s".format(seconds=text(example["interval_seconds"])),
            "E = {power} × {seconds} / 3,600,000 = {energy} kWh".format(
                power=text(example["interval_start_power_w"]),
                seconds=text(example["interval_seconds"]),
                energy=text(example["expected_energy_kwh"]),
            ),
            "```",
        ]
    lines += [
        "",
        "## Generated files",
        "",
        "- `cleaned_primary_cohort.csv`: Houses 1, 2, and 4 only.",
        "- `cleaned_solar_sensitivity_cohort.csv`: Houses 3 and 11 only, retaining solar caveats.",
        "- `per_household_quality_report.csv`: schema, source integrity, missing/invalid/negative/zero counts, cohort and output reconciliation.",
        "- `timestamp_interval_report.csv`: full-source and selected-window interval distributions and Time/Unix crosschecks.",
        "- `excluded_records_log.csv`: one explicit reason for every selected source record not represented by a cleaned interval record.",
        "- `data_manifest.json`: input/output hashes and exact processing configuration.",
        "",
        "## Reproduction command",
        "",
        "```powershell",
        "python experiments/refit_task2_energy_normalization/preprocess_refit.py",
        "python experiments/refit_task2_energy_normalization/verify_artifacts.py",
        "```",
        "",
        "## Output SHA-256",
        "",
    ]
    for name, digest in sorted(output_hashes.items()):
        lines.append(f"- `{name}`: `{digest}`")
    lines += [
        "",
        "## Limitations and non-claims",
        "",
        "1. The dataset is a publisher-cleaned release; observed zero values can reflect upstream cleaning and are retained rather than reinterpreted as guaranteed physical zero demand.",
        "2. Houses 3 and 11 have documented solar-generation interference. No solar or export correction is applied.",
        "3. The source reading semantic (point sample versus interval average) is not resolved by this task. The kWh field remains an explicit sample-hold estimate.",
        "4. Official appliance-level anomaly annotation schema and aggregate alignment remain unresolved and are not used.",
        "5. This task produces local data artifacts only; it is not an end-to-end, alert, or model experiment.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_output_dir_is_safe(output_dir: Path, input_dir: Path) -> None:
    resolved_output = output_dir.resolve()
    resolved_input = input_dir.resolve()
    try:
        resolved_output.relative_to(resolved_input)
    except ValueError:
        return
    raise ValueError("Output directory must not be inside the raw REFIT input directory.")


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    config = read_config(config_path)
    input_dir = repo_path(config["input_directory"]).resolve()
    selection_file = repo_path(config["task1_selection_file"]).resolve()
    output_dir = (repo_path(args.output_dir) if args.output_dir else repo_path(config["output_directory"])).resolve()
    check_output_dir_is_safe(output_dir, input_dir)
    selected_windows = load_selected_windows(selection_file)
    configured_houses = sorted(config["cohorts"]["primary"] + config["cohorts"]["solar_sensitivity"])
    selected_houses = [window.household_id for window in selected_windows]
    if selected_houses != configured_houses:
        raise ValueError(
            f"Task 1 selected households {selected_houses} do not match the explicit cohort configuration {configured_houses}."
        )
    if len(set(config["cohorts"]["primary"]) & set(config["cohorts"]["solar_sensitivity"])):
        raise ValueError("Primary and solar-sensitivity cohorts overlap.")

    filenames = config["output_files"]
    output_paths = {key: output_dir / filename for key, filename in filenames.items()}
    already_present = [str(path) for path in output_paths.values() if path.exists()]
    if already_present and not args.overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing Task 2 artifacts. Use a new --output-dir or explicit --overwrite: "
            + ", ".join(already_present)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=".task2_refit_staging_", dir=output_dir.parent))
    try:
        staged = {key: staging_dir / filename for key, filename in filenames.items()}
        cleaned_fields = [
            "household_id", "cohort", "source_filename", "source_row_number", "original_time_text",
            "original_unix", "timestamp_utc_from_unix", "original_aggregate_power_w",
            "interval_end_source_row_number", "interval_end_unix", "interval_end_timestamp_utc_from_unix",
            "interval_end_aggregate_power_w", "interval_seconds", "derived_interval_energy_kwh",
            "energy_integration_method", "interval_classification", "data_quality_flags", "source_issues_raw",
            "source_issue_marked", "solar_interference_documented", "known_source_caveat",
        ]
        excluded_fields = [
            "household_id", "cohort", "source_filename", "source_row_number", "original_time_text",
            "original_unix", "timestamp_utc_from_unix", "original_aggregate_power_w", "aggregate_parse_status",
            "source_issues_raw", "source_issue_marked", "solar_interference_documented",
            "related_predecessor_row_number", "related_predecessor_unix", "interval_seconds",
            "iqr_outlier_diagnostic_flag", "exclusion_rule", "reason",
        ]
        interval_rows: list[dict[str, str]] = []
        quality_rows: list[dict[str, str]] = []
        inspections: list[FileInspection] = []
        results: list[ProcessingResult] = []
        with (
            staged["primary_cleaned"].open("w", encoding="utf-8", newline="") as primary_handle,
            staged["solar_cleaned"].open("w", encoding="utf-8", newline="") as solar_handle,
            staged["excluded_log"].open("w", encoding="utf-8", newline="") as excluded_handle,
        ):
            primary_writer = csv.DictWriter(primary_handle, fieldnames=cleaned_fields)
            solar_writer = csv.DictWriter(solar_handle, fieldnames=cleaned_fields)
            excluded_writer = csv.DictWriter(excluded_handle, fieldnames=excluded_fields)
            primary_writer.writeheader()
            solar_writer.writeheader()
            excluded_writer.writeheader()
            for window in selected_windows:
                inspection = inspect_source(window, input_dir, config)
                result = process_records(inspection, config, primary_writer, solar_writer, excluded_writer)
                inspections.append(inspection)
                results.append(result)
                interval_rows.extend(
                    [
                        interval_report_row(inspection, "full_source", inspection.full, config),
                        interval_report_row(inspection, "selected_window", inspection.selected, config),
                    ]
                )
                quality_rows.append(quality_report_row(inspection, result, config))

        interval_fields = list(interval_rows[0])
        with staged["interval_report"].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=interval_fields)
            writer.writeheader()
            writer.writerows(interval_rows)
        quality_fields = list(quality_rows[0])
        with staged["quality_report"].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=quality_fields)
            writer.writeheader()
            writer.writerows(quality_rows)

        substantive_keys = ["primary_cleaned", "solar_cleaned", "quality_report", "interval_report", "excluded_log"]
        output_hashes = {filenames[key]: sha256_file(staged[key]) for key in substantive_keys}
        write_summary(staged["summary"], inspections, results, output_hashes, config)
        output_hashes[filenames["summary"]] = sha256_file(staged["summary"])
        manifest = {
            "task": config["task"],
            "scope": "Local cleaning and energy normalization only; no replay, ML, anomalies, alerting, backend, Docker, device-token, or paper change.",
            "config_path": str(config_path.relative_to(REPOSITORY_ROOT).as_posix()),
            "config_sha256": sha256_file(config_path),
            "script_path": str(Path(__file__).resolve().relative_to(REPOSITORY_ROOT).as_posix()),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "task1_selection_file": str(selection_file.relative_to(REPOSITORY_ROOT).as_posix()),
            "task1_selection_file_sha256": sha256_file(selection_file),
            "measurement_semantics": {
                "aggregate_field": config["column_mapping"]["aggregate_power"],
                "unit": "active power W",
                "is_interval_energy": False,
                "canonical_chronology": config["column_mapping"]["unix_time"],
                "human_time_policy": "Retain Time verbatim; derive UTC only from Unix.",
            },
            "normalization": config["normalization"],
            "sampling": config["sampling"],
            "cohorts": config["cohorts"],
            "input_files": [
                {
                    "household_id": item.household_id,
                    "cohort": cohort_for(item.household_id, config),
                    "filename": item.window.filename,
                    "size_bytes": item.file_size_bytes,
                    "md5": item.file_md5,
                    "sha256": item.file_sha256,
                    "selected_window_start_utc": item.window.start_utc,
                    "selected_window_end_utc": item.window.end_utc,
                    "header": item.header,
                }
                for item in inspections
            ],
            "output_hashes_sha256": output_hashes,
            "manifest_self_hash_included": False,
            "determinism": "No generated-at timestamp is embedded, so identical inputs/configuration should yield byte-identical named outputs.",
        }
        staged["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        for key, target in output_paths.items():
            staged[key].replace(target)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


if __name__ == "__main__":
    main()
