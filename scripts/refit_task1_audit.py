#!/usr/bin/env python3
"""Audit the official REFIT cleaned-source subset used for Task 1.

This script is intentionally read-only with respect to input CSV files.  It
profiles the source archive, verifies published checksums, calculates
household-level quality statistics, and applies a pre-registered selection
gate.  It is not a preprocessing, anomaly-labeling, replay, or ML-training
script.

The official Zenodo record 5063428 currently exposes only Houses 1, 2, 3, 4,
5, and 11.  If a file is unavailable it is reported as unavailable; it is
never replaced by a non-official mirror or silently omitted from the report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import re
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RECORD_URL = "https://zenodo.org/records/5063428"
RECORD_DOI = "https://doi.org/10.5281/zenodo.5063428"
SOURCE_LANDING_PAGE = (
    "https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/"
)
ANNOTATION_LANDING_PAGE = (
    "https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/"
)
WINDOW_SECONDS = 14 * 24 * 60 * 60
EXPECTED_SLOT_SECONDS = 8
WINDOW_EXPECTED_SLOTS = WINDOW_SECONDS // EXPECTED_SLOT_SECONDS + 1

# Values copied from the public Zenodo record's file metadata, not inferred.
EXPECTED_MD5: dict[str, str] = {
    "CLEAN_House1.csv": "f5336d80c700f866af0d997ea8d39146",
    "CLEAN_House2.csv": "13957fd139bf8f6ba8bceea36e85bb3d",
    "CLEAN_House3.csv": "ab6e34ea386eb4563bfcb9762619dc8f",
    "CLEAN_House4.csv": "efbfab2b04a61fbf7595422f15cacfb1",
    "CLEAN_House5.csv": "03938c844fdb09d787eb637bcf65f956",
    "CLEAN_House11.csv": "5b41bae97ab28871fcfe5167b41c0347",
}

SELECTION_GATE = {
    "minimum_window_days": 14,
    "minimum_valid_8_second_grid_coverage": 0.90,
    "maximum_estimated_missing_slot_fraction": 0.10,
    "maximum_gap_seconds": 3600,
    "minimum_native_cadence_share": 0.90,
    "native_cadence_definition": "abs(inter-sample interval - 8 s) <= 1 s",
    "selection_rule": (
        "Select every accessible household that satisfies all gates. If more than five satisfy them, "
        "rank by coverage descending, longest usable segment descending, invalid-record rate ascending, "
        "then numeric household ID ascending. No model score is used."
    ),
}


@dataclass
class IntervalEvent:
    end_ts: int
    delta_seconds: int
    estimated_missing_slots: int
    native: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream and audit official REFIT source CSVs.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/refit/raw/zenodo_5063428"),
        help="Directory containing CLEAN_House*.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/16_refit_dataset_audit"),
        help="Directory for small, versionable Task 1 evidence files.",
    )
    return parser.parse_args()


def utc_iso(timestamp: int | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_epoch(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = float(value.strip())
    except (AttributeError, ValueError):
        return None
    if not math.isfinite(parsed) or not parsed.is_integer():
        return None
    return int(parsed)


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value.strip())
    except (AttributeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def parse_refit_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def numeric_household_id(filename: str) -> int:
    match = re.search(r"House(\d+)", filename)
    return int(match.group(1)) if match else 10**9


def hash_file(path: Path) -> dict[str, str]:
    md5 = hashlib.md5()  # nosec B324 - used only to verify publisher-provided MD5 metadata.
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            md5.update(block)
            sha256.update(block)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def weighted_quantile(histogram: Counter[float], quantile: float) -> float | None:
    total = sum(histogram.values())
    if not total:
        return None
    target = quantile * (total - 1)
    cumulative = 0
    for value in sorted(histogram):
        cumulative += histogram[value]
        if cumulative > target:
            return value
    return max(histogram)


def percent(numerator: int | float, denominator: int | float) -> float | None:
    return None if not denominator else numerator / denominator


def csv_write(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = list(rows)
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8f}"
    return str(value)


def scan_house(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Stream one file.  No source rows are modified or held in memory."""
    file_hashes = hash_file(path)
    total_rows = 0
    valid_timestamp_rows = 0
    valid_aggregate_rows = 0
    usable_rows = 0
    invalid_unix_rows = 0
    invalid_datetime_rows = 0
    invalid_aggregate_rows = 0
    nonfinite_aggregate_rows = 0
    negative_aggregate_rows = 0
    zero_aggregate_rows = 0
    issue_marked_rows = 0
    out_of_order_timestamps = 0
    duplicate_timestamps = 0
    datetime_delta_checks = 0
    datetime_delta_mismatches = 0
    intervals: Counter[int] = Counter()
    aggregate_values: Counter[float] = Counter()
    first_ts: int | None = None
    last_ts: int | None = None
    previous_order_ts: int | None = None
    previous_valid_ts: int | None = None
    previous_time: datetime | None = None
    previous_time_ts: int | None = None
    longest_gap_seconds = 0
    gaps_over_8 = 0
    gaps_over_60 = 0
    gaps_over_600 = 0
    gaps_over_3600 = 0
    estimated_missing_slots = 0
    native_cadence_intervals = 0
    positive_intervals = 0
    segment_start: int | None = None
    segment_end: int | None = None
    segment_spans: list[int] = []
    candidates: list[dict[str, Any]] = []
    rolling_events: deque[IntervalEvent] = deque()
    rolling_max_heap: list[tuple[int, int]] = []
    rolling_missing = 0
    rolling_native = 0
    emission_day: int | None = None

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        required = {"Time", "Unix", "Aggregate"}
        missing_required = sorted(required - set(fieldnames))
        if missing_required:
            raise ValueError(f"{path.name} lacks required columns: {', '.join(missing_required)}")
        appliance_columns = [field for field in fieldnames if field.lower().startswith("appliance")]

        for row in reader:
            total_rows += 1
            unix_ts = parse_epoch(row.get("Unix"))
            local_time = parse_refit_datetime(row.get("Time"))
            aggregate = parse_float(row.get("Aggregate"))

            if unix_ts is None:
                invalid_unix_rows += 1
            else:
                valid_timestamp_rows += 1
                if first_ts is None or unix_ts < first_ts:
                    first_ts = unix_ts
                if last_ts is None or unix_ts > last_ts:
                    last_ts = unix_ts
                if previous_order_ts is not None:
                    if unix_ts == previous_order_ts:
                        duplicate_timestamps += 1
                    elif unix_ts < previous_order_ts:
                        out_of_order_timestamps += 1
                previous_order_ts = unix_ts

            if local_time is None:
                invalid_datetime_rows += 1
            elif unix_ts is not None and previous_time is not None and previous_time_ts is not None:
                datetime_delta_checks += 1
                datetime_delta = int((local_time - previous_time).total_seconds())
                unix_delta = unix_ts - previous_time_ts
                if datetime_delta != unix_delta:
                    datetime_delta_mismatches += 1
                previous_time = local_time
                previous_time_ts = unix_ts
            elif unix_ts is not None:
                previous_time = local_time
                previous_time_ts = unix_ts

            if aggregate is None:
                invalid_aggregate_rows += 1
                raw_value = (row.get("Aggregate") or "").strip().lower()
                if raw_value not in {"", "nan", "na", "n/a", "null"}:
                    nonfinite_aggregate_rows += 1
            elif aggregate < 0:
                negative_aggregate_rows += 1
                invalid_aggregate_rows += 1
            else:
                valid_aggregate_rows += 1
                aggregate_values[aggregate] += 1
                if aggregate == 0:
                    zero_aggregate_rows += 1

            issue_value = (row.get("Issues") or "").strip()
            if issue_value not in {"", "0", "0.0"}:
                issue_marked_rows += 1

            if unix_ts is None or aggregate is None or aggregate < 0:
                continue

            usable_rows += 1
            if previous_valid_ts is None:
                previous_valid_ts = unix_ts
                segment_start = unix_ts
                segment_end = unix_ts
                continue

            if unix_ts <= previous_valid_ts:
                previous_valid_ts = unix_ts if unix_ts > previous_valid_ts else previous_valid_ts
                continue

            delta = unix_ts - previous_valid_ts
            intervals[delta] += 1
            positive_intervals += 1
            if abs(delta - EXPECTED_SLOT_SECONDS) <= 1:
                native_cadence_intervals += 1
            if delta > EXPECTED_SLOT_SECONDS:
                gaps_over_8 += 1
                estimated_missing_slots += max(round(delta / EXPECTED_SLOT_SECONDS) - 1, 0)
            if delta > 60:
                gaps_over_60 += 1
            if delta > 600:
                gaps_over_600 += 1
            if delta > 3600:
                gaps_over_3600 += 1
                if segment_start is not None and segment_end is not None:
                    segment_spans.append(segment_end - segment_start)
                segment_start = unix_ts
            segment_end = unix_ts
            longest_gap_seconds = max(longest_gap_seconds, delta)

            event = IntervalEvent(
                end_ts=unix_ts,
                delta_seconds=delta,
                estimated_missing_slots=max(round(delta / EXPECTED_SLOT_SECONDS) - 1, 0),
                native=abs(delta - EXPECTED_SLOT_SECONDS) <= 1,
            )
            rolling_events.append(event)
            rolling_missing += event.estimated_missing_slots
            rolling_native += int(event.native)
            heapq.heappush(rolling_max_heap, (-event.delta_seconds, event.end_ts))

            window_start = unix_ts - WINDOW_SECONDS
            while rolling_events and rolling_events[0].end_ts <= window_start:
                expired = rolling_events.popleft()
                rolling_missing -= expired.estimated_missing_slots
                rolling_native -= int(expired.native)
            while rolling_max_heap and rolling_max_heap[0][1] <= window_start:
                heapq.heappop(rolling_max_heap)

            current_day = unix_ts // 86400
            if first_ts is not None and unix_ts - first_ts >= WINDOW_SECONDS and current_day != emission_day:
                emission_day = current_day
                interval_count = len(rolling_events)
                observations = interval_count + 1
                max_gap = -rolling_max_heap[0][0] if rolling_max_heap else 0
                coverage = min(1.0, observations / WINDOW_EXPECTED_SLOTS)
                missing_fraction = rolling_missing / max(1, WINDOW_EXPECTED_SLOTS - 1)
                cadence_share = rolling_native / interval_count if interval_count else 0.0
                candidates.append(
                    {
                        "candidate_window_start_utc": utc_iso(window_start),
                        "candidate_window_end_utc": utc_iso(unix_ts),
                        "candidate_observations": observations,
                        "candidate_expected_slots": WINDOW_EXPECTED_SLOTS,
                        "candidate_valid_coverage": coverage,
                        "candidate_estimated_missing_slots": rolling_missing,
                        "candidate_estimated_missing_fraction": missing_fraction,
                        "candidate_max_gap_seconds": max_gap,
                        "candidate_native_cadence_share": cadence_share,
                    }
                )
            previous_valid_ts = unix_ts

    if segment_start is not None and segment_end is not None:
        segment_spans.append(segment_end - segment_start)

    q1 = weighted_quantile(aggregate_values, 0.25)
    median = weighted_quantile(aggregate_values, 0.50)
    q3 = weighted_quantile(aggregate_values, 0.75)
    iqr = (q3 - q1) if q1 is not None and q3 is not None else None
    robust_high_threshold = q3 + 3 * iqr if q3 is not None and iqr is not None else None
    robust_high_flags = (
        sum(count for value, count in aggregate_values.items() if value > robust_high_threshold)
        if robust_high_threshold is not None
        else 0
    )

    def interval_quantile(q: float) -> int | None:
        total = sum(intervals.values())
        if not total:
            return None
        target = q * (total - 1)
        cumulative = 0
        for value in sorted(intervals):
            cumulative += intervals[value]
            if cumulative > target:
                return value
        return max(intervals)

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate["candidate_valid_coverage"] >= SELECTION_GATE["minimum_valid_8_second_grid_coverage"]
        and candidate["candidate_estimated_missing_fraction"]
        <= SELECTION_GATE["maximum_estimated_missing_slot_fraction"]
        and candidate["candidate_max_gap_seconds"] <= SELECTION_GATE["maximum_gap_seconds"]
        and candidate["candidate_native_cadence_share"] >= SELECTION_GATE["minimum_native_cadence_share"]
    ]
    candidate_rank_key = lambda candidate: (
        candidate["candidate_valid_coverage"],
        candidate["candidate_native_cadence_share"],
        -candidate["candidate_max_gap_seconds"],
        -candidate["candidate_estimated_missing_fraction"],
        candidate["candidate_window_start_utc"],
    )
    ranked_candidates = sorted(
        candidates,
        key=candidate_rank_key,
        reverse=True,
    )
    ranked_eligible_candidates = sorted(eligible_candidates, key=candidate_rank_key, reverse=True)
    best_candidate = (ranked_eligible_candidates or ranked_candidates or [None])[0]
    longest_segment = max(segment_spans, default=0)
    household = str(numeric_household_id(path.name))
    audit: dict[str, Any] = {
        "household": household,
        "source_filename": path.name,
        "source_file_size_bytes": path.stat().st_size,
        "source_md5": file_hashes["md5"],
        "published_md5": EXPECTED_MD5.get(path.name, ""),
        "published_md5_matches": file_hashes["md5"].lower() == EXPECTED_MD5.get(path.name, "").lower(),
        "source_sha256": file_hashes["sha256"],
        "schema_columns": "|".join(fieldnames),
        "aggregate_column": "Aggregate",
        "appliance_columns": "|".join(appliance_columns),
        "issues_column_present": "Issues" in fieldnames,
        "rows": total_rows,
        "valid_timestamp_rows": valid_timestamp_rows,
        "valid_aggregate_rows": valid_aggregate_rows,
        "usable_rows": usable_rows,
        "start_utc": utc_iso(first_ts),
        "end_utc": utc_iso(last_ts),
        "calendar_span_days": (last_ts - first_ts) / 86400 if first_ts is not None and last_ts is not None else None,
        "invalid_unix_rows": invalid_unix_rows,
        "invalid_datetime_rows": invalid_datetime_rows,
        "invalid_aggregate_rows": invalid_aggregate_rows,
        "nonfinite_aggregate_rows": nonfinite_aggregate_rows,
        "negative_aggregate_rows": negative_aggregate_rows,
        "zero_aggregate_rows": zero_aggregate_rows,
        "issue_marked_rows": issue_marked_rows,
        "duplicate_timestamps": duplicate_timestamps,
        "out_of_order_timestamps": out_of_order_timestamps,
        "datetime_unix_delta_checks": datetime_delta_checks,
        "datetime_unix_delta_mismatches": datetime_delta_mismatches,
        "median_interval_seconds": interval_quantile(0.50),
        "p95_interval_seconds": interval_quantile(0.95),
        "native_cadence_share": percent(native_cadence_intervals, positive_intervals),
        "gaps_over_8_seconds": gaps_over_8,
        "gaps_over_60_seconds": gaps_over_60,
        "gaps_over_600_seconds": gaps_over_600,
        "gaps_over_3600_seconds": gaps_over_3600,
        "longest_gap_seconds": longest_gap_seconds,
        "estimated_missing_slots": estimated_missing_slots,
        "estimated_missing_slot_fraction": percent(estimated_missing_slots, positive_intervals + estimated_missing_slots),
        "longest_contiguous_segment_days": longest_segment / 86400,
        "segments_at_least_14_days": sum(span >= WINDOW_SECONDS for span in segment_spans),
        "aggregate_q1_w": q1,
        "aggregate_median_w": median,
        "aggregate_q3_w": q3,
        "aggregate_iqr_w": iqr,
        "robust_high_threshold_w": robust_high_threshold,
        "robust_high_value_flags": robust_high_flags,
        "robust_high_value_flag_rate": percent(robust_high_flags, usable_rows),
        "candidate_windows_evaluated": len(candidates),
        "candidate_windows_passing_gate": len(eligible_candidates),
        "best_candidate_eligible": bool(eligible_candidates),
    }
    if best_candidate:
        audit.update(best_candidate)
    return audit, candidates


def selection_reason(audit: dict[str, Any]) -> str:
    if not audit.get("published_md5_matches"):
        return "REJECTED: local checksum does not match the published Zenodo MD5."
    if not audit.get("best_candidate_eligible"):
        return (
            "REJECTED: no inspected 14-day window met all pre-registered coverage, missing-slot, "
            "maximum-gap, and native-cadence gates."
        )
    return "ELIGIBLE: checksum-valid source file with at least one 14-day window satisfying every pre-registered gate."


def write_markdown_report(output_dir: Path, audits: list[dict[str, Any]], selection: list[dict[str, Any]]) -> None:
    valid_files = sum(bool(audit.get("published_md5_matches")) for audit in audits)
    eligible = sum(row["selection_status"] == "SELECTED" for row in selection)
    unavailable = sorted(set(EXPECTED_MD5) - {audit["source_filename"] for audit in audits})
    lines = [
        "# REFIT Task 1 Dataset Audit",
        "",
        "## Scope",
        "",
        "This report audits only checksum-verified files locally available from the official Zenodo REFIT cleaned record 5063428. It does not claim to audit the full 20-house University of Strathclyde archive.",
        "",
        f"- Official record: {RECORD_URL}",
        f"- DOI: {RECORD_DOI}",
        f"- Official University landing page: {SOURCE_LANDING_PAGE}",
        f"- Locally checksum-verified files: {valid_files}/{len(audits)}",
        f"- Official-record files unavailable locally: {', '.join(unavailable) if unavailable else 'none'}",
        f"- Selected replay-quality households: {eligible}",
        "",
        "## Selection rule",
        "",
        "A household is eligible only when at least one exact 14-day window has observed nominal-slot coverage >= 90% (capped at 100% because timestamps may jitter), estimated missing-slot fraction <= 10%, maximum observed gap <= 3600 seconds, and native-cadence share >= 90%, where native cadence means an observed interval within +/-1 second of 8 seconds. These are pre-registered data-quality gates; no model result was used.",
        "",
        "## Interpretation constraints",
        "",
        "- The source files are the cleaned REFIT release. Duplicate merging, short-gap forward filling, and long-gap zeroing are upstream transformations documented by the source publisher. This audit does not present their post-cleaning completeness as raw-data quality.",
        "- The full University archive and the official REFIT anomaly CSV could not be retrieved programmatically because the official file endpoints presented Cloudflare bot verification. No unofficial mirror was substituted.",
        "- The source CSV `Issues` field was counted for traceability, but its semantics have not been inferred and it is not treated as an anomaly label.",
        "- Therefore raw-versus-cleaned change rates, official anomaly-label schema, label-to-aggregate alignment, and true anomaly counts are NOT VERIFIED — DO NOT CLAIM IN PAPER.",
        "- Aggregate measurements are Watts. No energy conversion, imputation, row removal, anomaly injection, replay, model training, or alert testing was performed by this Task 1 script.",
        "",
            "## Table 1A — Household selection",
            "",
            "`Estimated missing-slot percentage` and major gaps describe the full cleaned-source span; they are not a claim about the selected 14-day replay window.",
            "",
            "| Household | Duration (calendar days) | Records | Observed interval | Estimated missing slots (full span) | Duplicate % | Major gap statistics | Selected/Rejected | Reason |",
            "|---:|---:|---:|---|---:|---:|---|---|---|",
    ]
    selected_by_house = {row["household"]: row for row in selection}
    for audit in sorted(audits, key=lambda row: int(row["household"])):
        row = selected_by_house[audit["household"]]
        lines.append(
            "| {house} | {span:.2f} | {rows} | nominal 8 s; median {median} s, p95 {p95} s | {missing:.2%} | {duplicates:.6%} | >1 h: {gap_count}; max: {gap} s | {status} | {reason} |".format(
                house=audit["household"],
                rows=audit["rows"],
                span=float(audit["calendar_span_days"] or 0),
                median=stringify(audit["median_interval_seconds"]),
                p95=stringify(audit["p95_interval_seconds"]),
                missing=float(audit["estimated_missing_slot_fraction"] or 0),
                duplicates=(int(audit["duplicate_timestamps"] or 0) / max(1, int(audit["rows"]))),
                gap_count=stringify(audit["gaps_over_3600_seconds"]),
                gap=stringify(audit["longest_gap_seconds"]),
                status=row["selection_status"],
                reason=("Checksum-valid; at least one 14-day window passed all gates." if row["selection_status"] == "SELECTED" else row["selection_reason"]),
            )
        )
    lines.extend(
        [
            "",
            "## Next required action",
            "",
            "Task 2 must first decide and document the energy-normalisation policy from aggregate active power in Watts using actual inter-sample intervals. It must not assume an eight-second interval across gaps. The official anomaly CSV must be obtained and schema-inspected before any genuine-label ML evaluation is claimed.",
        ]
    )
    (output_dir / "data_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("CLEAN_House*.csv"), key=lambda item: numeric_household_id(item.name))
    if not csv_files:
        raise SystemExit(f"No CLEAN_House*.csv files found in {input_dir}")

    audits: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for source_path in csv_files:
        print(f"[AUDIT] {source_path.name}", flush=True)
        audit, candidates = scan_house(source_path)
        audits.append(audit)
        for candidate in candidates:
            candidate_rows.append({"household": audit["household"], **candidate})

    eligible_audits = [
        audit for audit in audits if audit.get("published_md5_matches") and audit.get("best_candidate_eligible")
    ]
    eligible_ranked = sorted(
        eligible_audits,
        key=lambda audit: (
            -(audit.get("candidate_valid_coverage") or 0),
            -(audit.get("longest_contiguous_segment_days") or 0),
            audit.get("invalid_aggregate_rows") or 0,
            int(audit["household"]),
        ),
    )
    selected_houses = {audit["household"] for audit in eligible_ranked[:5]}
    selection: list[dict[str, Any]] = []
    for audit in sorted(audits, key=lambda row: int(row["household"])):
        selected = audit["household"] in selected_houses
        status = "SELECTED" if selected else "REJECTED"
        reason = selection_reason(audit)
        if audit.get("best_candidate_eligible") and not selected:
            reason = "REJECTED: eligible but outside the maximum five-household replay cohort after pre-registered ranking."
        selection.append(
            {
                "household": audit["household"],
                "source_filename": audit["source_filename"],
                "selection_status": status,
                "selection_reason": reason,
                "best_window_start_utc": audit.get("candidate_window_start_utc", ""),
                "best_window_end_utc": audit.get("candidate_window_end_utc", ""),
                "best_window_coverage": audit.get("candidate_valid_coverage", ""),
                "best_window_missing_fraction": audit.get("candidate_estimated_missing_fraction", ""),
                "best_window_max_gap_seconds": audit.get("candidate_max_gap_seconds", ""),
                "best_window_native_cadence_share": audit.get("candidate_native_cadence_share", ""),
            }
        )

    manifest = {
        "task": "Task 1 — Download + Dataset Selection",
        "source": {
            "university_landing_page": SOURCE_LANDING_PAGE,
            "annotation_landing_page": ANNOTATION_LANDING_PAGE,
            "zenodo_record": RECORD_URL,
            "zenodo_doi": RECORD_DOI,
            "licence": "CC BY 4.0, as displayed by the official Zenodo record",
            "scope": "Only locally available checksum-verified cleaned-house CSVs are profiled.",
        },
        "expected_zenodo_md5": EXPECTED_MD5,
        "local_files": [
            {
                "filename": audit["source_filename"],
                "size_bytes": audit["source_file_size_bytes"],
                "md5": audit["source_md5"],
                "sha256": audit["source_sha256"],
                "published_md5_matches": audit["published_md5_matches"],
            }
            for audit in audits
        ],
        "not_verified": [
            "Full 20-house archive content and per-house metrics outside locally available files.",
            "Raw-versus-cleaned transformation footprint.",
            "Official anomaly CSV schema, timestamps, label counts, and aggregate alignment.",
            "Human-readable DateTime timezone offset; UNIX time is used only for chronological ordering.",
        ],
    }
    (output_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "selection_criteria.md").write_text(
        "# REFIT Task 1 Pre-registered Household Selection Criteria\n\n"
        + "```json\n"
        + json.dumps(SELECTION_GATE, indent=2)
        + "\n```\n\n"
        + "The script selects based on data integrity only. It does not use labels, model output, alert counts, or other downstream results.\n",
        encoding="utf-8",
    )
    csv_write(output_dir / "dataset_inventory.csv", audits)
    csv_write(output_dir / "household_audit.csv", audits)
    csv_write(output_dir / "candidate_14_day_windows.csv", candidate_rows)
    csv_write(output_dir / "household_selection.csv", selection)
    write_markdown_report(output_dir, audits, selection)
    print(f"[DONE] Evidence written to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
