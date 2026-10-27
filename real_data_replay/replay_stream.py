#!/usr/bin/env python3
"""Replay Task-2-normalized REFIT energy intervals through the existing gateway.

The historical REFIT records remain historical.  This tool sends their
*estimated interval kWh* values through the established `POST /api/v1/ingestion`
contract to emulate a continuous/live-like stream.  It never sends the raw
REFIT Aggregate-W field as `energyConsumed`.

Safety design:
* Dry-run is the default. Network requests require `--execute`.
* A household-to-existing-device mapping is mandatory; no IDs are invented.
* Device-token material is read only from environment/config, never logged.
* Source timestamps and replay timestamps are both preserved in local logs.
* Each selected source record gets at most one final delivery row per run.
* A gateway 2xx response means accepted by the HTTP ingress boundary; it does
  not prove Kafka, InfluxDB, alerts, or dashboard persistence.

Only Python's standard library is used so the launcher can run in the project
environment without introducing a third-party dependency.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, TextIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_INPUT = Path("data/refit/processed/cleaned_dataset.csv")
DEFAULT_ENDPOINT = "http://localhost:8080/api/v1/ingestion"
DEFAULT_OUTPUT_ROOT = Path("real_data_replay/logs")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 1.0
DEFAULT_PROGRESS_EVERY = 1000

REQUIRED_INPUT_COLUMNS = {
    "household_id",
    "source_filename",
    "source_row_number",
    "source_unix",
    "timestamp_utc",
    "interval_seconds",
    "estimated_interval_energy_kwh",
    "is_replayable",
    "solar_interference_documented",
    "known_source_caveat",
}

SPOOL_COLUMNS = [
    "household_id",
    "source_filename",
    "source_row_number",
    "source_unix",
    "source_timestamp_utc",
    "interval_seconds",
    "energy_consumed_kwh",
    "solar_interference_documented",
    "known_source_caveat",
]

SENT_EVENT_COLUMNS = [
    "run_id",
    "loop_index",
    "sequence",
    "event_id",
    "household_id",
    "device_id",
    "source_filename",
    "source_row_number",
    "source_unix",
    "source_timestamp_utc",
    "replay_timestamp_utc",
    "timestamp_mode",
    "timeline_mode",
    "speed",
    "interval_seconds",
    "energy_consumed_kwh",
    "solar_interference_documented",
    "known_source_caveat",
    "timestamp_adjusted_for_order",
    "schedule_delay_seconds",
    "rate_limit_delay_seconds",
    "attempts",
    "final_http_status",
    "outcome",
    "http_accepted",
    "delivery_error",
    "elapsed_wall_seconds",
]

FAILED_REQUEST_COLUMNS = [
    "run_id",
    "loop_index",
    "sequence",
    "event_id",
    "household_id",
    "device_id",
    "attempt",
    "source_timestamp_utc",
    "replay_timestamp_utc",
    "http_status",
    "retryable",
    "failure_kind",
    "error",
    "response_excerpt",
]


@dataclass(frozen=True)
class RawReplayRecord:
    household_id: str
    source_filename: str
    source_row_number: str
    source_unix: int
    source_timestamp_utc: str
    interval_seconds: int
    energy_consumed_kwh: float
    solar_interference_documented: bool
    known_source_caveat: str

    @property
    def event_id(self) -> str:
        return f"{self.source_filename}:{self.source_row_number}:{self.source_unix}"


@dataclass(frozen=True)
class PreparedDataset:
    spool_paths: dict[str, Path]
    household_first_unix: dict[str, int]
    global_first_unix: int
    total_records: int
    selected_households: list[str]
    per_household_records: dict[str, int]
    relative_span_seconds: int
    source_span_seconds: int
    input_sha256: str


@dataclass(frozen=True)
class DeliveryResult:
    accepted: bool
    attempts: int
    final_http_status: int | None
    outcome: str
    error: str


@dataclass(frozen=True)
class DeviceMapResolution:
    mapping: dict[str, int]
    source: str
    sha256: str
    metadata: dict[str, Any]


@dataclass
class RunCounters:
    planned_events: int = 0
    final_rows: int = 0
    dry_run_events: int = 0
    accepted_events: int = 0
    failed_events: int = 0
    failed_attempts: int = 0
    total_energy_kwh: float = 0.0
    status_counts: Counter[str] | None = None
    outcome_counts: Counter[str] | None = None

    def __post_init__(self) -> None:
        if self.status_counts is None:
            self.status_counts = Counter()
        if self.outcome_counts is None:
            self.outcome_counts = Counter()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay Task-2 normalized REFIT interval-kWh records through the existing "
            "Home Energy Tracker ingestion gateway. Dry-run is the default."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Task-2 cleaned_dataset.csv; defaults to the configured value or data/refit/processed/cleaned_dataset.csv.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional KEY=VALUE config file. It is never copied into run logs.",
    )
    parser.add_argument("--endpoint", default=None, help="Gateway ingestion endpoint override.")
    parser.add_argument(
        "--device-map-file",
        type=Path,
        default=None,
        help="JSON household-to-existing-device-ID map. Required unless configured by REPLAY_DEVICE_MAP_FILE/JSON.",
    )
    parser.add_argument(
        "--device-map-json",
        default=None,
        help="Inline JSON map for controlled automation. Avoid passing secrets on the command line.",
    )
    parser.add_argument(
        "--household",
        action="append",
        default=None,
        help="Household ID to include; repeat the option to include multiple homes. Default: all available in input.",
    )
    parser.add_argument(
        "--start",
        "--source-start",
        dest="source_start",
        default=None,
        help="Inclusive ISO-8601 source-time lower bound, e.g. 2014-10-01T00:00:00Z.",
    )
    parser.add_argument(
        "--end",
        "--source-end",
        dest="source_end",
        default=None,
        help="Inclusive ISO-8601 source-time upper bound, e.g. 2014-10-01T01:00:00Z.",
    )
    parser.add_argument(
        "--timestamp-mode",
        choices=("current", "rebased", "source"),
        default=None,
        help=(
            "Payload timestamp: current=actual/preplanned send time; rebased=original timeline anchored to "
            "replay-start; source=preserve original REFIT UTC."
        ),
    )
    parser.add_argument(
        "--timeline-mode",
        choices=("relative", "source"),
        default=None,
        help="relative aligns each household's selected window at t=0; source preserves global source chronology.",
    )
    parser.add_argument(
        "--replay-start-utc",
        default=None,
        help="UTC anchor for timestamp-mode=rebased and dry-run planning. Default: run start UTC. Does not affect source mode.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Historical/timeline seconds per wall-clock second. 1=normal speed; >1=accelerated.",
    )
    parser.add_argument(
        "--max-events-per-second",
        type=float,
        default=None,
        help="Global start-rate ceiling for HTTP POSTs. It may reduce the effective accelerated speed.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Maximum events across all loops; use for a controlled smoke run.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Repeat the selected stream. Requires --max-loops >= 2 and timestamp-mode=current.",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="Finite number of loops when --loop is explicitly selected.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Per-request HTTP timeout.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum HTTP attempts for confirmed retryable HTTP statuses.",
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=None,
        help="Initial exponential-backoff delay; attempt n waits backoff*2^(n-1).",
    )
    parser.add_argument(
        "--retry-uncertain-transport",
        action="store_true",
        help=(
            "Retry transport errors explicitly. This may duplicate an event if the gateway accepted it but "
            "the response was lost; default is to log and stop that event."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Root directory for per-run logs.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional safe directory name for this run; autogenerated if omitted.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=None,
        help="Print progress after this many final event rows.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after a final delivery failure instead of continuing through the planned stream.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform POST requests. Without this flag, the run is local dry-run only.",
    )
    return parser.parse_args()


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid config line {line_number} in {path}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Empty config key on line {line_number} in {path}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def config_value(
    cli_value: Any,
    config: dict[str, str],
    names: tuple[str, ...],
    default: Any = None,
) -> Any:
    if cli_value is not None:
        return cli_value
    for name in names:
        if name in config and config[name] != "":
            return config[name]
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def parse_positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer, got {value!r}") from error
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {parsed}")
    return parsed


def parse_nonnegative_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric, got {value!r}") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"{name} must be a finite value >= 0, got {value!r}")
    return parsed


def parse_positive_float(value: Any, name: str) -> float:
    parsed = parse_nonnegative_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {parsed}")
    return parsed


def parse_iso_to_unix(value: str | None, name: str) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be ISO-8601 with an offset, got {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include UTC Z or an explicit offset, got {value!r}")
    return int(parsed.timestamp())


def iso_utc_from_epoch(epoch_seconds: float) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
        raise ValueError(
            "run-id must contain only letters, digits, '.', '_' or '-' and must not start with punctuation"
        )
    return value


def resolve_path(value: Path | str, config_path: Path | None) -> Path:
    path = Path(value)
    if not path.is_absolute() and config_path is not None:
        return (config_path.parent / path).resolve()
    return path


def load_device_map(
    *,
    map_path: Path | None,
    map_json: str | None,
    config_path: Path | None,
) -> DeviceMapResolution:
    if map_path is not None and map_json is not None:
        raise ValueError("Specify only one of device-map-file or device-map-json")
    if map_path is not None:
        resolved = resolve_path(map_path, config_path)
        if not resolved.is_file():
            raise FileNotFoundError(f"Device map file not found: {resolved}")
        source_description = str(resolved)
        raw_text = resolved.read_text(encoding="utf-8")
        raw_data = json.loads(raw_text)
        raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    elif map_json is not None:
        source_description = "inline JSON"
        raw_data = json.loads(map_json)
        raw_hash = hashlib.sha256(map_json.encode("utf-8")).hexdigest()
    else:
        raise ValueError(
            "A household-to-device mapping is required. Supply --device-map-file, --device-map-json, "
            "REPLAY_DEVICE_MAP_FILE, or REPLAY_DEVICE_MAP_JSON."
        )
    if not isinstance(raw_data, dict):
        raise ValueError(f"Device map from {source_description} must be a JSON object")
    mapping_data = raw_data.get("household_to_device_id", raw_data)
    if not isinstance(mapping_data, dict):
        raise ValueError("household_to_device_id must be a JSON object")
    mapping: dict[str, int] = {}
    for household, device_id in mapping_data.items():
        household_text = str(household).strip()
        if not household_text:
            raise ValueError("Device map contains an empty household ID")
        mapping[household_text] = parse_positive_int(device_id, f"device ID for household {household_text}")
    if not mapping:
        raise ValueError("Device map cannot be empty")
    metadata = {
        str(key): value
        for key, value in raw_data.items()
        if key != "household_to_device_id"
    }
    return DeviceMapResolution(
        mapping=mapping,
        source=source_description,
        sha256=raw_hash,
        metadata=metadata,
    )


def required_fieldnames(reader: csv.DictReader, input_path: Path) -> None:
    available = set(reader.fieldnames or [])
    missing = REQUIRED_INPUT_COLUMNS - available
    if missing:
        raise ValueError(
            f"{input_path} lacks required normalized-data column(s): {', '.join(sorted(missing))}"
        )


def parse_cleaned_row(row: dict[str, str], line_number: int) -> RawReplayRecord:
    try:
        household = (row["household_id"] or "").strip()
        filename = (row["source_filename"] or "").strip()
        source_row_number = (row["source_row_number"] or "").strip()
        source_unix = int((row["source_unix"] or "").strip())
        interval_seconds = int((row["interval_seconds"] or "").strip())
        energy = float((row["estimated_interval_energy_kwh"] or "").strip())
    except (KeyError, ValueError) as error:
        raise ValueError(f"Malformed normalized row at CSV line {line_number}: {error}") from error
    if not household or not filename or not source_row_number:
        raise ValueError(f"Missing source identity field at CSV line {line_number}")
    if source_unix <= 0 or interval_seconds <= 0:
        raise ValueError(f"Invalid source time/interval at CSV line {line_number}")
    if not math.isfinite(energy) or energy < 0:
        raise ValueError(f"Invalid normalized kWh value at CSV line {line_number}")
    if (row.get("is_replayable") or "").strip().lower() != "true":
        raise ValueError(
            f"Normalized input row at CSV line {line_number} is not replayable; refuse to send it."
        )
    source_timestamp = (row.get("timestamp_utc") or "").strip() or iso_utc_from_epoch(source_unix)
    solar_value = (row.get("solar_interference_documented") or "").strip().lower()
    if solar_value not in {"true", "false"}:
        raise ValueError(
            f"Invalid solar_interference_documented flag at CSV line {line_number}: {solar_value!r}"
        )
    return RawReplayRecord(
        household_id=household,
        source_filename=filename,
        source_row_number=source_row_number,
        source_unix=source_unix,
        source_timestamp_utc=source_timestamp,
        interval_seconds=interval_seconds,
        energy_consumed_kwh=energy,
        solar_interference_documented=solar_value == "true",
        known_source_caveat=(row.get("known_source_caveat") or "").strip(),
    )


def record_matches_filters(
    record: RawReplayRecord,
    households: set[str] | None,
    source_start_unix: int | None,
    source_end_unix: int | None,
) -> bool:
    if households is not None and record.household_id not in households:
        return False
    if source_start_unix is not None and record.source_unix < source_start_unix:
        return False
    if source_end_unix is not None and record.source_unix > source_end_unix:
        return False
    return True


def create_spools(
    *,
    input_path: Path,
    spool_directory: Path,
    households: set[str] | None,
    source_start_unix: int | None,
    source_end_unix: int | None,
) -> PreparedDataset:
    """Single-scan, bounded-memory preparation of per-house chronological streams.

    Task-2 output is expected to be ordered within each household. We validate
    that invariant and fail rather than silently reordering a supplied file.
    The temporary per-house spools make a globally ordered multi-house merge
    possible without loading hundreds of megabytes of CSV into RAM.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Normalized input file not found: {input_path}")
    spool_directory.mkdir(parents=True, exist_ok=True)
    handles: dict[str, TextIO] = {}
    writers: dict[str, csv.DictWriter] = {}
    spool_paths: dict[str, Path] = {}
    per_household_records: Counter[str] = Counter()
    first_unix: dict[str, int] = {}
    last_unix: dict[str, int] = {}
    global_first: int | None = None
    global_last: int | None = None
    total_records = 0
    try:
        with input_path.open("r", encoding="utf-8", newline="") as input_handle:
            reader = csv.DictReader(input_handle)
            required_fieldnames(reader, input_path)
            for line_number, row in enumerate(reader, start=2):
                record = parse_cleaned_row(row, line_number)
                if not record_matches_filters(record, households, source_start_unix, source_end_unix):
                    continue
                prior = last_unix.get(record.household_id)
                if prior is not None and record.source_unix <= prior:
                    raise ValueError(
                        "Normalized input is not strictly chronological within household "
                        f"{record.household_id}: {record.source_unix} follows {prior}."
                    )
                last_unix[record.household_id] = record.source_unix
                first_unix.setdefault(record.household_id, record.source_unix)
                global_first = record.source_unix if global_first is None else min(global_first, record.source_unix)
                global_last = record.source_unix if global_last is None else max(global_last, record.source_unix)
                if record.household_id not in writers:
                    spool_path = spool_directory / f"household_{record.household_id}.csv"
                    handle = spool_path.open("w", encoding="utf-8", newline="")
                    writer = csv.DictWriter(handle, fieldnames=SPOOL_COLUMNS)
                    writer.writeheader()
                    handles[record.household_id] = handle
                    writers[record.household_id] = writer
                    spool_paths[record.household_id] = spool_path
                writers[record.household_id].writerow(
                    {
                        "household_id": record.household_id,
                        "source_filename": record.source_filename,
                        "source_row_number": record.source_row_number,
                        "source_unix": str(record.source_unix),
                        "source_timestamp_utc": record.source_timestamp_utc,
                        "interval_seconds": str(record.interval_seconds),
                        "energy_consumed_kwh": repr(record.energy_consumed_kwh),
                        "solar_interference_documented": str(
                            record.solar_interference_documented
                        ).lower(),
                        "known_source_caveat": record.known_source_caveat,
                    }
                )
                per_household_records[record.household_id] += 1
                total_records += 1
    finally:
        for handle in handles.values():
            handle.close()
    if total_records == 0:
        raise ValueError("No replayable events remain after household/time filtering")
    if global_first is None or global_last is None:
        raise AssertionError("Non-empty selected replay stream lacks source bounds")
    relative_span = max(last_unix[household] - first_unix[household] for household in first_unix)
    return PreparedDataset(
        spool_paths=spool_paths,
        household_first_unix=first_unix,
        global_first_unix=global_first,
        total_records=total_records,
        selected_households=sorted(spool_paths, key=lambda value: int(value) if value.isdigit() else value),
        per_household_records=dict(sorted(per_household_records.items())),
        relative_span_seconds=relative_span,
        source_span_seconds=global_last - global_first,
        input_sha256=sha256_file(input_path),
    )


def read_spool_record(row: dict[str, str]) -> RawReplayRecord:
    return RawReplayRecord(
        household_id=row["household_id"],
        source_filename=row["source_filename"],
        source_row_number=row["source_row_number"],
        source_unix=int(row["source_unix"]),
        source_timestamp_utc=row["source_timestamp_utc"],
        interval_seconds=int(row["interval_seconds"]),
        energy_consumed_kwh=float(row["energy_consumed_kwh"]),
        solar_interference_documented=(row["solar_interference_documented"].strip().lower() == "true"),
        known_source_caveat=row["known_source_caveat"],
    )


def iter_spool(path: Path) -> Iterator[RawReplayRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield read_spool_record(row)


def timeline_offset_seconds(
    record: RawReplayRecord,
    prepared: PreparedDataset,
    timeline_mode: str,
) -> int:
    if timeline_mode == "relative":
        return record.source_unix - prepared.household_first_unix[record.household_id]
    return record.source_unix - prepared.global_first_unix


def merged_records(
    prepared: PreparedDataset,
    timeline_mode: str,
) -> Iterator[tuple[int, RawReplayRecord]]:
    """Yield a stable, chronological merge across selected household streams."""
    iterators = [iter_spool(prepared.spool_paths[household]) for household in prepared.selected_households]
    heap: list[tuple[int, int, str, int, int, RawReplayRecord]] = []
    for index, iterator in enumerate(iterators):
        try:
            record = next(iterator)
        except StopIteration:
            continue
        offset = timeline_offset_seconds(record, prepared, timeline_mode)
        row_number_key = int(record.source_row_number) if record.source_row_number.isdigit() else 0
        heapq.heappush(
            heap,
            (offset, record.source_unix, record.household_id, row_number_key, index, record),
        )
    while heap:
        offset, _, _, _, iterator_index, record = heapq.heappop(heap)
        yield offset, record
        iterator = iterators[iterator_index]
        try:
            next_record = next(iterator)
        except StopIteration:
            continue
        next_offset = timeline_offset_seconds(next_record, prepared, timeline_mode)
        row_number_key = int(next_record.source_row_number) if next_record.source_row_number.isdigit() else 0
        heapq.heappush(
            heap,
            (
                next_offset,
                next_record.source_unix,
                next_record.household_id,
                row_number_key,
                iterator_index,
                next_record,
            ),
        )


def payload_timestamp(
    *,
    record: RawReplayRecord,
    timeline_offset: int,
    loop_index: int,
    loop_span_seconds: int,
    timestamp_mode: str,
    replay_start_epoch: float,
    speed: float,
    current_epoch: float,
    device_id: int,
    last_payload_epoch_by_device: dict[int, float],
) -> tuple[str, bool]:
    if timestamp_mode == "source":
        candidate_epoch = float(record.source_unix)
    elif timestamp_mode == "rebased":
        # Preserve logical source timing independently of wall-clock replay
        # speed. Under acceleration this may intentionally create future
        # timestamps, so it is not the default dashboard mode.
        virtual_offset = loop_index * loop_span_seconds + timeline_offset
        candidate_epoch = replay_start_epoch + virtual_offset
    else:
        # `current` is the practical live-like mode. On an actual execution it
        # represents send time; dry-run passes a deterministic planned send
        # time so the emitted plan is inspectable without HTTP traffic.
        candidate_epoch = current_epoch
    prior = last_payload_epoch_by_device.get(device_id)
    adjusted = prior is not None and candidate_epoch <= prior
    if adjusted:
        candidate_epoch = prior + 0.000001
    last_payload_epoch_by_device[device_id] = candidate_epoch
    return iso_utc_from_epoch(candidate_epoch), adjusted


def response_excerpt(response: bytes | str | None, limit: int = 500) -> str:
    if response is None:
        return ""
    if isinstance(response, bytes):
        text = response.decode("utf-8", errors="replace")
    else:
        text = str(response)
    return text.replace("\r", " ").replace("\n", " ")[:limit]


def status_retryable(status: int) -> bool:
    return status == 408 or status == 429 or 500 <= status <= 599


def send_with_retries(
    *,
    endpoint: str,
    device_token: str,
    correlation_id: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    max_attempts: int,
    backoff_seconds: float,
    retry_uncertain_transport: bool,
    failure_writer: csv.DictWriter,
    failure_log_base: dict[str, str],
) -> DeliveryResult:
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "home-energy-refit-replay/1.0",
        "X-Device-Token": device_token,
        "X-Correlation-ID": correlation_id,
    }
    last_status: int | None = None
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        request = Request(endpoint, data=encoded, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - user-controlled local/configured endpoint.
                status = response.getcode()
                body = response.read()
        except HTTPError as error:
            status = error.code
            body = error.read()
            error_text = f"HTTP {status}"
            retryable = status_retryable(status)
            failure_writer.writerow(
                {
                    **failure_log_base,
                    "attempt": str(attempt),
                    "http_status": str(status),
                    "retryable": str(retryable).lower(),
                    "failure_kind": "http_error",
                    "error": error_text,
                    "response_excerpt": response_excerpt(body),
                }
            )
            last_status = status
            last_error = error_text
            if not retryable or attempt >= max_attempts:
                return DeliveryResult(False, attempt, status, "HTTP_FAILURE", error_text)
        except (URLError, TimeoutError, OSError) as error:
            # A connection or read failure can happen after the gateway already
            # accepted the body. Do not blindly retry it unless the operator has
            # explicitly accepted the possibility of duplicate ingestion.
            error_text = f"{type(error).__name__}: {error}"
            retryable = retry_uncertain_transport
            failure_writer.writerow(
                {
                    **failure_log_base,
                    "attempt": str(attempt),
                    "http_status": "",
                    "retryable": str(retryable).lower(),
                    "failure_kind": "transport_uncertain",
                    "error": error_text,
                    "response_excerpt": "",
                }
            )
            last_error = error_text
            if not retryable or attempt >= max_attempts:
                outcome = "TRANSPORT_UNCERTAIN" if not retryable else "TRANSPORT_FAILURE"
                return DeliveryResult(False, attempt, None, outcome, error_text)
        else:
            if 200 <= status < 300:
                return DeliveryResult(True, attempt, status, "HTTP_ACCEPTED", "")
            # urllib normally converts non-2xx statuses into HTTPError, but
            # retain this path for custom handlers and future runtime changes.
            retryable = status_retryable(status)
            error_text = f"Unexpected HTTP status {status}"
            failure_writer.writerow(
                {
                    **failure_log_base,
                    "attempt": str(attempt),
                    "http_status": str(status),
                    "retryable": str(retryable).lower(),
                    "failure_kind": "unexpected_http_status",
                    "error": error_text,
                    "response_excerpt": response_excerpt(body),
                }
            )
            last_status = status
            last_error = error_text
            if not retryable or attempt >= max_attempts:
                return DeliveryResult(False, attempt, status, "HTTP_FAILURE", error_text)
        time.sleep(backoff_seconds * (2 ** (attempt - 1)))
    return DeliveryResult(False, max_attempts, last_status, "HTTP_FAILURE", last_error)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_settings(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve() if args.config is not None else None
    config = parse_env_file(config_path) if config_path is not None else {}
    input_value = config_value(args.input, config, ("REPLAY_INPUT",), DEFAULT_INPUT)
    endpoint = str(config_value(args.endpoint, config, ("REPLAY_ENDPOINT",), DEFAULT_ENDPOINT)).strip()
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("REPLAY_ENDPOINT/--endpoint must begin with http:// or https://")
    map_file_value = config_value(args.device_map_file, config, ("REPLAY_DEVICE_MAP_FILE",), None)
    map_json_value = config_value(args.device_map_json, config, ("REPLAY_DEVICE_MAP_JSON",), None)
    device_map_resolution = load_device_map(
        map_path=None if map_file_value is None else Path(map_file_value),
        map_json=None if map_json_value is None else str(map_json_value),
        # A path explicitly supplied at the CLI is relative to the working
        # directory; a path supplied by the config file is relative to that
        # config file. This avoids surprising double-directory resolution.
        config_path=None if args.device_map_file is not None else config_path,
    )
    timestamp_mode = str(
        config_value(args.timestamp_mode, config, ("REPLAY_TIMESTAMP_MODE",), "current")
    ).strip().lower()
    timeline_mode = str(
        config_value(args.timeline_mode, config, ("REPLAY_TIMELINE_MODE",), "relative")
    ).strip().lower()
    if timestamp_mode not in {"current", "rebased", "source"}:
        raise ValueError("timestamp-mode must be current, rebased, or source")
    if timeline_mode not in {"relative", "source"}:
        raise ValueError("timeline-mode must be relative or source")
    speed = parse_positive_float(config_value(args.speed, config, ("REPLAY_SPEED",), 100.0), "speed")
    max_events_per_second = parse_positive_float(
        config_value(
            args.max_events_per_second,
            config,
            ("REPLAY_MAX_EVENTS_PER_SECOND",),
            5.0,
        ),
        "max-events-per-second",
    )
    timeout_seconds = parse_positive_float(
        config_value(args.timeout_seconds, config, ("REPLAY_TIMEOUT_SECONDS",), DEFAULT_TIMEOUT_SECONDS),
        "timeout-seconds",
    )
    max_attempts = parse_positive_int(
        config_value(args.max_attempts, config, ("REPLAY_MAX_ATTEMPTS",), DEFAULT_MAX_ATTEMPTS),
        "max-attempts",
    )
    backoff_seconds = parse_nonnegative_float(
        config_value(args.backoff_seconds, config, ("REPLAY_BACKOFF_SECONDS",), DEFAULT_BACKOFF_SECONDS),
        "backoff-seconds",
    )
    output_value = config_value(args.output_dir, config, ("REPLAY_OUTPUT_DIR",), DEFAULT_OUTPUT_ROOT)
    output_dir = resolve_path(
        Path(output_value), None if args.output_dir is not None else config_path
    )
    input_path = resolve_path(Path(input_value), None if args.input is not None else config_path)
    source_start = parse_iso_to_unix(args.source_start, "--start")
    source_end = parse_iso_to_unix(args.source_end, "--end")
    if source_start is not None and source_end is not None and source_end < source_start:
        raise ValueError("--end must be at or after --start")
    selected_households = None if not args.household else {str(value).strip() for value in args.household}
    if selected_households is not None and "" in selected_households:
        raise ValueError("--household cannot be empty")
    max_events = None if args.max_events is None else parse_positive_int(args.max_events, "max-events")
    progress_every = parse_positive_int(
        config_value(args.progress_every, config, ("REPLAY_PROGRESS_EVERY",), DEFAULT_PROGRESS_EVERY),
        "progress-every",
    )
    max_loops = 1
    if args.loop:
        max_loops = parse_positive_int(args.max_loops, "max-loops")
        if max_loops < 2:
            raise ValueError("--loop requires --max-loops >= 2")
        if timestamp_mode != "current":
            raise ValueError("--loop requires timestamp-mode=current to prevent repeated source timestamp events")
    elif args.max_loops is not None:
        raise ValueError("--max-loops is valid only with --loop")
    replay_start_value = config_value(args.replay_start_utc, config, ("REPLAY_START_UTC",), None)
    replay_start_epoch = (
        float(parse_iso_to_unix(str(replay_start_value), "replay-start-utc"))
        if replay_start_value is not None
        else time.time()
    )
    device_token = str(
        config_value(None, config, ("REPLAY_DEVICE_TOKEN", "WOKWI_INGESTION_TOKEN"), "")
    )
    # `config_value` also consults the environment, allowing WOKWI_INGESTION_TOKEN
    # supplied by a local Docker/PowerShell session without reading `.env` implicitly.
    if args.execute and not device_token:
        raise ValueError(
            "--execute requires REPLAY_DEVICE_TOKEN or WOKWI_INGESTION_TOKEN in the supplied config/environment."
        )
    run_id = safe_run_id(args.run_id) if args.run_id else (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    return {
        "config_path": config_path,
        "input_path": input_path,
        "endpoint": endpoint,
        "device_map": device_map_resolution.mapping,
        "device_map_provenance": {
            "source": device_map_resolution.source,
            "sha256": device_map_resolution.sha256,
            "metadata": device_map_resolution.metadata,
        },
        "timestamp_mode": timestamp_mode,
        "timeline_mode": timeline_mode,
        "speed": speed,
        "max_events_per_second": max_events_per_second,
        "timeout_seconds": timeout_seconds,
        "max_attempts": max_attempts,
        "backoff_seconds": backoff_seconds,
        "retry_uncertain_transport": args.retry_uncertain_transport,
        "output_dir": output_dir,
        "run_id": run_id,
        "source_start_unix": source_start,
        "source_end_unix": source_end,
        "selected_households": selected_households,
        "max_events": max_events,
        "max_loops": max_loops,
        "replay_start_epoch": replay_start_epoch,
        "progress_every": progress_every,
        "execute": args.execute,
        "stop_on_failure": args.stop_on_failure,
        "device_token": device_token,
    }


def log_manifest_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Return a safe config copy: never persist the device token itself."""
    return {
        "input_path": str(settings["input_path"].as_posix()),
        "endpoint": settings["endpoint"],
        "device_map": settings["device_map"],
        "device_map_provenance": settings["device_map_provenance"],
        "timestamp_mode": settings["timestamp_mode"],
        "timeline_mode": settings["timeline_mode"],
        "speed": settings["speed"],
        "max_events_per_second": settings["max_events_per_second"],
        "timeout_seconds": settings["timeout_seconds"],
        "max_attempts": settings["max_attempts"],
        "backoff_seconds": settings["backoff_seconds"],
        "retry_uncertain_transport": settings["retry_uncertain_transport"],
        "source_start_unix": settings["source_start_unix"],
        "source_end_unix": settings["source_end_unix"],
        "selected_households": sorted(settings["selected_households"] or []),
        "max_events": settings["max_events"],
        "max_loops": settings["max_loops"],
        "replay_start_utc": iso_utc_from_epoch(settings["replay_start_epoch"]),
        "progress_every": settings["progress_every"],
        "execute": settings["execute"],
        "stop_on_failure": settings["stop_on_failure"],
        "device_token_configured": bool(settings["device_token"]),
    }


def print_plan(prepared: PreparedDataset, settings: dict[str, Any], max_offset: int) -> None:
    planned_seconds = max_offset / settings["speed"]
    mode = "HTTP execution" if settings["execute"] else "dry run (no HTTP requests)"
    print(
        "Replay plan: "
        f"{prepared.total_records:,} events across {', '.join(prepared.selected_households)}; "
        f"{settings['timeline_mode']} timeline; {settings['timestamp_mode']} timestamps; "
        f"speed={settings['speed']:g}x; planned span={planned_seconds:.3f} wall seconds; "
        f"max-start-rate={settings['max_events_per_second']:g}/s; {mode}."
    )


def run_replay(settings: dict[str, Any]) -> int:
    output_root: Path = settings["output_dir"]
    run_dir = output_root / settings["run_id"]
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists; choose a new --run-id: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    spool_dir = Path(tempfile.mkdtemp(prefix=".spool_", dir=run_dir))
    started_epoch = time.time()
    started_monotonic = time.monotonic()
    completed_normally = False
    interrupted = False
    counters = RunCounters()
    try:
        prepared = create_spools(
            input_path=settings["input_path"],
            spool_directory=spool_dir,
            households=settings["selected_households"],
            source_start_unix=settings["source_start_unix"],
            source_end_unix=settings["source_end_unix"],
        )
        missing_mappings = [
            household for household in prepared.selected_households if household not in settings["device_map"]
        ]
        if missing_mappings:
            raise ValueError(
                "No device mapping for selected household(s): " + ", ".join(missing_mappings)
            )
        selected_device_ids = [settings["device_map"][household] for household in prepared.selected_households]
        if len(selected_device_ids) != len(set(selected_device_ids)):
            raise ValueError(
                "Selected households must map to distinct device IDs so aggregate household streams are not silently conflated."
            )
        max_offset = (
            prepared.relative_span_seconds
            if settings["timeline_mode"] == "relative"
            else prepared.source_span_seconds
        )
        loop_span_seconds = max_offset + 1
        planned_events = prepared.total_records * settings["max_loops"]
        if settings["max_events"] is not None:
            planned_events = min(planned_events, settings["max_events"])
        counters.planned_events = planned_events
        print_plan(prepared, settings, max_offset)

        manifest_path = run_dir / "run_manifest.json"
        task2_manifest_path = settings["input_path"].parent / "preprocessing_manifest.json"
        task2_manifest_hash = sha256_file(task2_manifest_path) if task2_manifest_path.is_file() else None
        solar_households = [
            household
            for household in prepared.selected_households
            if household in {"3", "11"}
        ]
        initial_manifest = {
            "tool": "real_data_replay/replay_stream.py",
            "tool_sha256": sha256_file(Path(__file__)),
            "run_id": settings["run_id"],
            "started_at_utc": iso_utc_from_epoch(started_epoch),
            "configuration": log_manifest_settings(settings),
            "input": {
                "sha256": prepared.input_sha256,
                "task2_manifest_path": str(task2_manifest_path.as_posix())
                if task2_manifest_path.is_file()
                else None,
                "task2_manifest_sha256": task2_manifest_hash,
                "total_filtered_records": prepared.total_records,
                "selected_households": prepared.selected_households,
                "per_household_records": prepared.per_household_records,
                "relative_timeline_span_seconds": prepared.relative_span_seconds,
                "source_timeline_span_seconds": prepared.source_span_seconds,
            },
            "source_caveats": {
                "solar_interference_households": solar_households,
                "note": (
                    "Houses 3 and 11 retain the Task-2 documented solar-generation interference caveat; "
                    "they are not filtered or relabeled by replay."
                ),
            },
            "semantic_notes": [
                "Input energy_consumed_kwh is Task-2 estimated interval energy in kWh, not raw REFIT Watts.",
                "source timestamp is retained as local provenance in sent_events.csv.",
                "timestamp-mode=current uses the actual send-time clock during execution; it is not the original measurement timestamp.",
                "timestamp-mode=rebased preserves source-relative timing from a declared anchor independently of speed.",
                "HTTP 2xx means ingress acceptance only; it does not prove downstream Kafka, InfluxDB, alert, or dashboard persistence.",
                "No ingestion idempotency key is supported by the current backend; transport-error retries can duplicate data and are opt-in.",
            ],
        }
        write_json(manifest_path, initial_manifest)

        with (run_dir / "sent_events.csv").open("w", encoding="utf-8", newline="") as sent_handle, (
            run_dir / "failed_requests.csv"
        ).open("w", encoding="utf-8", newline="") as failed_handle:
            sent_writer = csv.DictWriter(sent_handle, fieldnames=SENT_EVENT_COLUMNS)
            failed_writer = csv.DictWriter(failed_handle, fieldnames=FAILED_REQUEST_COLUMNS)
            sent_writer.writeheader()
            failed_writer.writeheader()
            sent_handle.flush()
            failed_handle.flush()

            run_schedule_origin = time.monotonic()
            next_allowed_send_start = run_schedule_origin
            last_payload_epoch_by_device: dict[int, float] = {}
            sequence = 0
            for loop_index in range(settings["max_loops"]):
                for timeline_offset, record in merged_records(prepared, settings["timeline_mode"]):
                    if settings["max_events"] is not None and sequence >= settings["max_events"]:
                        completed_normally = True
                        break
                    sequence += 1
                    device_id = settings["device_map"][record.household_id]
                    scheduled_elapsed = (loop_index * loop_span_seconds + timeline_offset) / settings["speed"]
                    schedule_delay_seconds = 0.0
                    rate_limit_delay_seconds = 0.0
                    if settings["execute"]:
                        schedule_target = run_schedule_origin + scheduled_elapsed
                        schedule_delay_seconds = max(0.0, schedule_target - time.monotonic())
                        if schedule_delay_seconds > 0:
                            time.sleep(schedule_delay_seconds)
                        rate_target = max(schedule_target, next_allowed_send_start)
                        rate_limit_delay_seconds = max(0.0, rate_target - time.monotonic())
                        if rate_limit_delay_seconds > 0:
                            time.sleep(rate_limit_delay_seconds)
                        send_start_monotonic = time.monotonic()
                        next_allowed_send_start = send_start_monotonic + (
                            1.0 / settings["max_events_per_second"]
                        )
                        current_payload_epoch = time.time()
                    else:
                        # Dry runs never sleep. This is a planned current-time
                        # coordinate for audit purposes, not an emitted event.
                        current_payload_epoch = settings["replay_start_epoch"] + scheduled_elapsed
                    replay_timestamp, timestamp_adjusted = payload_timestamp(
                        record=record,
                        timeline_offset=timeline_offset,
                        loop_index=loop_index,
                        loop_span_seconds=loop_span_seconds,
                        timestamp_mode=settings["timestamp_mode"],
                        replay_start_epoch=settings["replay_start_epoch"],
                        speed=settings["speed"],
                        current_epoch=current_payload_epoch,
                        device_id=device_id,
                        last_payload_epoch_by_device=last_payload_epoch_by_device,
                    )
                    payload = {
                        "deviceId": device_id,
                        "energyConsumed": record.energy_consumed_kwh,
                        "timestamp": replay_timestamp,
                    }
                    event_log_base = {
                        "run_id": settings["run_id"],
                        "loop_index": str(loop_index),
                        "sequence": str(sequence),
                        "event_id": record.event_id,
                        "household_id": record.household_id,
                        "device_id": str(device_id),
                        "source_filename": record.source_filename,
                        "source_row_number": record.source_row_number,
                        "source_unix": str(record.source_unix),
                        "source_timestamp_utc": record.source_timestamp_utc,
                        "replay_timestamp_utc": replay_timestamp,
                        "timestamp_mode": settings["timestamp_mode"],
                        "timeline_mode": settings["timeline_mode"],
                        "speed": repr(settings["speed"]),
                        "interval_seconds": str(record.interval_seconds),
                        "energy_consumed_kwh": repr(record.energy_consumed_kwh),
                        "solar_interference_documented": str(
                            record.solar_interference_documented
                        ).lower(),
                        "known_source_caveat": record.known_source_caveat,
                        "timestamp_adjusted_for_order": str(timestamp_adjusted).lower(),
                        "schedule_delay_seconds": repr(schedule_delay_seconds),
                        "rate_limit_delay_seconds": repr(rate_limit_delay_seconds),
                    }
                    if settings["execute"]:
                        delivery = send_with_retries(
                            endpoint=settings["endpoint"],
                            device_token=settings["device_token"],
                            correlation_id=f"refit-{settings['run_id']}-{loop_index}-{sequence}",
                            payload=payload,
                            timeout_seconds=settings["timeout_seconds"],
                            max_attempts=settings["max_attempts"],
                            backoff_seconds=settings["backoff_seconds"],
                            retry_uncertain_transport=settings["retry_uncertain_transport"],
                            failure_writer=failed_writer,
                            failure_log_base={
                                "run_id": settings["run_id"],
                                "loop_index": str(loop_index),
                                "sequence": str(sequence),
                                "event_id": record.event_id,
                                "household_id": record.household_id,
                                "device_id": str(device_id),
                                "source_timestamp_utc": record.source_timestamp_utc,
                                "replay_timestamp_utc": replay_timestamp,
                            },
                        )
                    else:
                        delivery = DeliveryResult(
                            accepted=False,
                            attempts=0,
                            final_http_status=None,
                            outcome="DRY_RUN",
                            error="",
                        )
                    sent_writer.writerow(
                        {
                            **event_log_base,
                            "attempts": str(delivery.attempts),
                            "final_http_status": ""
                            if delivery.final_http_status is None
                            else str(delivery.final_http_status),
                            "outcome": delivery.outcome,
                            "http_accepted": str(delivery.accepted).lower(),
                            "delivery_error": delivery.error,
                            "elapsed_wall_seconds": repr(time.monotonic() - started_monotonic),
                        }
                    )
                    sent_handle.flush()
                    failed_handle.flush()
                    counters.final_rows += 1
                    counters.total_energy_kwh += record.energy_consumed_kwh
                    counters.outcome_counts[delivery.outcome] += 1
                    if delivery.final_http_status is not None:
                        counters.status_counts[str(delivery.final_http_status)] += 1
                    if delivery.outcome == "DRY_RUN":
                        counters.dry_run_events += 1
                    elif delivery.accepted:
                        counters.accepted_events += 1
                    else:
                        counters.failed_events += 1
                        # Failed attempts are recorded by send_with_retries. Count
                        # is recovered below from failed_requests.csv for accuracy.
                        if settings["stop_on_failure"]:
                            raise RuntimeError(
                                f"Stopped after final delivery failure for {record.event_id}: {delivery.error}"
                            )
                    if counters.final_rows % settings["progress_every"] == 0 or counters.final_rows == planned_events:
                        print(
                            f"Progress: {counters.final_rows:,}/{planned_events:,} final events; "
                            f"accepted={counters.accepted_events:,}; failed={counters.failed_events:,}; "
                            f"dry-run={counters.dry_run_events:,}"
                        )
                else:
                    continue
                # Inner loop broke because max-events was reached.
                break
            else:
                completed_normally = True
            if sequence >= planned_events:
                completed_normally = True

        failed_requests_path = run_dir / "failed_requests.csv"
        with failed_requests_path.open("r", encoding="utf-8", newline="") as handle:
            counters.failed_attempts = sum(1 for _ in csv.DictReader(handle))
        ended_epoch = time.time()
        summary = {
            "run_id": settings["run_id"],
            "status": "completed" if completed_normally else "stopped_early",
            "started_at_utc": iso_utc_from_epoch(started_epoch),
            "ended_at_utc": iso_utc_from_epoch(ended_epoch),
            "elapsed_wall_seconds": time.monotonic() - started_monotonic,
            "planned_events": counters.planned_events,
            "final_event_rows": counters.final_rows,
            "dry_run_events": counters.dry_run_events,
            "http_accepted_events": counters.accepted_events,
            "failed_final_events": counters.failed_events,
            "failed_request_attempts": counters.failed_attempts,
            "total_energy_kwh_in_final_rows": counters.total_energy_kwh,
            "http_status_counts": dict(sorted(counters.status_counts.items())),
            "outcome_counts": dict(sorted(counters.outcome_counts.items())),
            "downstream_persistence_verified": False,
            "notes": [
                "A 2xx response is ingress acceptance, not a Kafka/InfluxDB/alert/dashboard persistence guarantee.",
                "source mode retains historical timestamps; current dashboard windows will not normally show them.",
                "current mode timestamps represent local send time and do not replace source measurement provenance.",
            ],
        }
        write_json(run_dir / "replay_summary.json", summary)
        final_manifest = {
            **initial_manifest,
            "completed_at_utc": iso_utc_from_epoch(ended_epoch),
            "output_files": {
                "sent_events.csv": sha256_file(run_dir / "sent_events.csv"),
                "failed_requests.csv": sha256_file(run_dir / "failed_requests.csv"),
                "replay_summary.json": sha256_file(run_dir / "replay_summary.json"),
            },
        }
        write_json(manifest_path, final_manifest)
        print(f"Run artifacts written to: {run_dir}")
        print(
            f"Completed: final={counters.final_rows:,}, accepted={counters.accepted_events:,}, "
            f"failed={counters.failed_events:,}, dry-run={counters.dry_run_events:,}."
        )
        return 0 if counters.failed_events == 0 else 2
    except KeyboardInterrupt:
        interrupted = True
        print("Replay interrupted by operator; partial CSV logs remain in the run directory.", file=sys.stderr)
        return 130
    finally:
        # Only delete this run's temporary splice files; final logs remain.
        if spool_dir.exists():
            shutil.rmtree(spool_dir)
        if interrupted:
            # The full manifest is not guaranteed if interruption happened
            # during preparation, but the run directory itself remains as
            # transparent evidence of an incomplete attempt.
            pass


def main() -> int:
    try:
        settings = resolve_settings(parse_args())
        return run_replay(settings)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"Replay configuration error: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"Replay stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
