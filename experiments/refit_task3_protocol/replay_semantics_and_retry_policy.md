# Task 3 — Replay Semantics and Retry Policy

## 1. Existing ingestion contract: verified boundaries

The existing public route is:

```http
POST /api/v1/ingestion
Content-Type: application/json
X-Device-Token: <device-bound token>
```

The accepted body has only `deviceId`, non-negative `energyConsumed`, and non-null `timestamp` parsed as Java `Instant`. It contains no source row identity, replay-run identity, original source time, ingestion time, or idempotency key. The ingestion service copies the supplied timestamp into its Kafka event and invokes `kafkaTemplate.send("energy-usage", event)` without waiting for broker acknowledgement.

Consequences:

- A HTTP `201 Created` is ingress acceptance only. It is not evidence of durable Kafka publication, consumption, InfluxDB persistence, ML processing, alert creation, or email delivery.
- Static code inspection found no age, historical-time, monotonicity, per-device ordering, or duplicate validation at ingestion. A historical REFIT timestamp is not rejected merely for being historical.
- Because the current contract carries one timestamp, source time and replay time cannot both be persisted through the existing contract. They must be preserved separately in the external run ledger.

Relevant evidence: `EnergyUsageDto.java:11-18`, `IngestionController.java:23-27`, `IngestionService.java:24-35`, and `EnergyUsageEvent.java:8-13`.

## 2. Task 2 to replay-helper compatibility gate

The current Task 2 files have these authoritative field names:

```text
original_unix
timestamp_utc_from_unix
derived_interval_energy_kwh
```

The existing `real_data_replay/replay_stream.py` instead requires, among others:

```text
source_unix
timestamp_utc
estimated_interval_energy_kwh
is_replayable
```

The latter `is_replayable` field is not present in Task 2. Therefore the existing helper must not be described as ready to replay the Task 2 output. A future, separately reviewed compatibility adapter would have to:

| Task 2 source field | Future replay-helper field | Constraint |
|---|---|---|
| `original_unix` | `source_unix` | Preserve integer chronology exactly. |
| `timestamp_utc_from_unix` | `timestamp_utc` | Preserve derived UTC representation. |
| `derived_interval_energy_kwh` | `estimated_interval_energy_kwh` | Preserve numeric value and declare left-rectangle estimated-energy semantics. |
| retained valid Task 2 record | `is_replayable=true` | Only after an adapter validates all Task 2 inclusion rules; do not infer this flag from source quality alone. |
| Task 2 provenance fields | source identity/caveat fields | Retain household, source filename/row, solar flag, and caveat in the external ledger. |

Task 3 creates no adapter, does not merge the two cohort CSVs, and does not send a request.

## 3. Three distinct clocks

| Clock | Definition | Storage/recording rule |
|---|---|---|
| Original recorded measurement time | `original_unix` and `timestamp_utc_from_unix` from Task 2. | Immutable in the source/provenance ledger. |
| Replay payload time | The timestamp included in the future POST body. | Store in every client receipt. |
| Ingestion/processing wall-clock time | Time at which services receive/process a request. | Not present in the event contract; collect only from run logs, broker records, metrics, or service logs when available. |

The main live-like experiment will use `timestamp-mode=current`: the payload timestamp is the controlled replay wall-clock timestamp, while the original REFIT timestamp remains in the ledger. This aligns with current system components, which query wall-clock windows (`now - 1 hour` for scheduled usage aggregation and `now - days` for usage views).

`timestamp-mode=source` is permitted only for a forensic/historical persistence check. Source-mode events use 2014/2015 timestamps and will not normally appear in current usage windows or current-hour alert aggregation. `timestamp-mode=rebased` is a separately declared logical-timeline mode, not the default dashboard mode.

## 4. Ordering, timeline, and household sequencing

1. Within a household, sort strictly by `(original_unix, source_row_number)`.
2. The first executed stage is H1 only.
3. The primary multi-house run uses H1, H2, and H4 concurrently under a **relative** timeline: each selected window begins at relative time zero, while ordering inside each house is preserved.
4. If two planned events share a relative offset, the deterministic planner order is relative offset, original Unix, numeric household ID, then source row number.
5. A relative timeline must be labelled artificial; H1/H2 observations are from 2014 while H4 is from 2015. It is appropriate for controlled live-like pipeline exercise, not for claims that the homes were measured simultaneously.
6. H3/H11 are never interleaved into the primary result. They may be replayed later as a separately labelled solar-sensitivity run.

## 5. Intended staged speed and duration

The following are frozen operational starting settings, not capacity claims. They are intentionally small until actual accounting evidence exists.

| Stage | Scope | Timeline/payload mode | Speed and rate ceiling | Intended duration/purpose |
|---|---|---|---|---|
| Dry-run preflight | H1, 25 events | Relative / current-planned | `speed=10`; no network request | Validate schema, ordering, and ledger formation. |
| G2 smoke | H1, 5 events | Relative / current | `speed=1`; global start ceiling 1 event/s; no loop | Approximately the native short cadence; prove only ingress receipt handling. |
| G3 multi-house dry run | H1/H2/H4, 25 each | Relative / current-planned | `speed=10`; no network request | 75-event schedule/mapping validation. |
| G4 short end-to-end | H1/H2/H4, 25 each | Relative / current | `speed=1`; global start ceiling 3 events/s; no loop | 75-event controlled observation window. |
| G5 provisional extended run | One pre-registered continuous six-source-hour segment per primary house | Relative / current | `speed=10`; global ceiling 5 events/s | About 36 wall-clock minutes before rate limiting at 10×; permitted only after G4 proves no collision/accounting issue. |

The rate ceilings are safeguards, not demonstrated service capacities. The G5 setting must be reapproved if G4 shows HTTP failures, timestamp/persistence collisions, consumer lag, or any unreconciled evidence. No full 14-day replay rate is asserted or authorized by this protocol.

## 6. Conservative retry policy

The future replay launcher must use this conservative policy, consistent with the existing helper's documented behavior:

| Outcome | Action |
|---|---|
| HTTP 2xx | Record final acceptance; do not resend. |
| HTTP 408, 429, or 5xx | Retry at most three total attempts with a 1-second initial exponential backoff. Log every attempt. |
| Other 4xx, including authentication/schema failures | Do not retry automatically. Stop the affected stage and correct the configuration. |
| Network timeout or transport error with no response | Mark `TRANSPORT_UNCERTAIN`; do not retry automatically. Investigate before intentionally resending the same source identity. |

`--retry-uncertain-transport` must remain absent in protocol runs. This is essential because the API has no idempotency key and a lost response can follow successful ingestion.

## 7. Duplicate and collision accounting

The future client ledger will assign each planned event a deterministic local identity:

```text
REFIT:<source_filename>:<source_row_number>:<original_unix>
```

This is a ledger identity, not an API field. It enables exact client-side detection of multiple attempts or receipts for the same source observation.

Downstream exact deduplication is not guaranteed: Kafka events and InfluxDB points do not contain this identity. Usage service persists `energy_usage` with only the `deviceId` tag, `energyConsumed` field, and payload timestamp at millisecond precision. A future short run must therefore use isolated device mappings and record pre/post query evidence. Any apparent duplicate or count mismatch is an investigation finding, not something to be overwritten, re-sent, or silently deduplicated.

## 8. Device mapping gate

The Compose default config declares only one explicit token mapping (`deviceId=1`). Existing ingestion authorization binds a machine token to the supplied device ID. A five-house or even three-house primary replay cannot assume a valid mapping from REFIT households to distinct backend devices.

Before any execute stage, an operator must verify an existing, authorized, one-to-one H1/H2/H4-to-device mapping and record only its non-secret hash/metadata in the run manifest. Task 3 does not create devices, change device tokens, expose tokens, or modify Compose.

## 9. Required evidence for a future run

Every later execution must preserve: Task 2 input hash; adapter hash; device-map hash; non-secret configuration; service/image version; original/replay timestamps; source identity; correlation ID; every HTTP attempt; final client outcome; pre/post Kafka and DLT offsets; Influx query result; ML metrics; and alert metric snapshots. Absence of any downstream record must be reported as unavailable or unresolved, never as a zero count.
