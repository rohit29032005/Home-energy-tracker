# Task 3 — Protocol Open Questions and Decision Register

## Blocking questions before any replay execution

| ID | Open question | Evidence at Task 3 freeze | Required resolution | Blocks |
|---|---|---|---|---|
| OQ-1 | How will the authoritative Task 2 schema be made compatible with the existing replay helper? | Task 2 uses `original_unix`/`derived_interval_energy_kwh`; helper requires `source_unix`/`estimated_interval_energy_kwh`/`is_replayable`. | Review a non-mutating adapter design, preserve provenance/caveats, and hash the derived replay input. | G2 onward |
| OQ-2 | Which existing authorized devices correspond to H1, H2, and H4? | Compose default visibly defines a mapping only for device 1; Task 2 has no device IDs. | Operator verifies a one-to-one existing device map and appropriate token authorization without exposing credentials. | G2 for H1; G3 onward for all primary houses |
| OQ-3 | Can downstream counts be made run-specific? | Ingestion/Kafka/Influx do not carry source-row/run identity. | Define an approved correlation/observation procedure, or restrict claims to client/HTTP evidence. | Exact Kafka/Influx/ML/alert reconciliation |
| OQ-4 | What is the effective partition count and retention state of the pre-existing `energy-usage` topic? | Compose default uses topic configuration, but existing persistent Kafka data may differ. | Record broker/topic/consumer-group metadata before an execution stage. | Ordering and offset interpretation |
| OQ-5 | Can InfluxDB distinguish every rapid replayed record at configured payload timestamp precision? | Usage service writes at millisecond precision; no source event ID is persisted. | Smoke-test query identity/collision behavior before any accelerated run. | G5 and any duplicate-free persistence claim |
| OQ-6 | What official REFIT annotation fields, timestamp convention, and H1-window overlap exist? | Official dataset metadata is available; CSV/README are absent locally and direct automated access returned 403. | Obtain files through normal authorized download and perform a separate provenance/schema audit. | Genuine-label ML evaluation |
| OQ-7 | Is there a scientifically justified mapping from appliance annotations to aggregate intervals? | None is established by Task 2 or Task 3. | Pre-register and validate a mapping methodology, or retain appliance-level outcome only. | Aggregate-label accuracy claim |
| OQ-8 | What future feature recipe and maximum causal lookback will be used? | No Task 3 model or feature design exists. | Freeze feature definitions, scaling/fitting rules, and window/embargo policy before ML fitting. | G6 |
| OQ-9 | How will alert ownership, alerting settings, and existing alert state be isolated? | Alert deduplication is user/device/type and wall-clock based; default window is 15 minutes. | Identify an appropriate controlled account/device setup and record initial alert state/counter snapshots. | Alert-count interpretation |

## Non-blocking but mandatory reporting limitations

1. `derived_interval_energy_kwh` is a left-rectangle sample-hold estimate from whole-house active power, not a direct meter interval-energy reading.
2. `original_time_text` is preserved and cross-checked, but no formal source timezone is assigned to it; `original_unix` remains canonical.
3. H3/H11 retain documented solar interference and must remain solar-sensitivity-only.
4. `source_issues_raw`, IQR flags, cadence flags, and solar flags are not anomaly labels.
5. The source windows are historical and span different calendar periods; a relative concurrent replay is an artificial schedule.
6. HTTP acceptance does not prove downstream persistence or alert delivery.
7. Existing downstream instrumentation is partially observable but lacks a replay-run tag; a missing metric is not zero.

## Decision record

| Decision | Status | Rationale |
|---|---|---|
| Preserve Task 2 raw/processed artifacts unchanged | Frozen | Task 2 integrity and reproducibility are authoritative. |
| Primary cohort is H1/H2/H4 | Frozen | Pre-registered eligible data with no retained solar caveat. |
| H3/H11 are sensitivity-only | Frozen | Documented solar-generation interference; no correction performed. |
| Main live-like payload timestamp is current UTC | Frozen | Current dashboard/aggregation paths use wall-clock queries. |
| Original source time remains external provenance | Frozen | Existing payload/event contract has only one timestamp. |
| Automatic uncertain-transport retry | Rejected | No verified idempotency key; retry can create duplicate events. |
| Current primary claim | Frozen | System-integration/reproducibility only; no ML accuracy claim. |
| Official aggregate anomaly evaluation | Deferred | Schema/alignment/mapping evidence unavailable. |
| Controlled perturbation evaluation | Deferred pending Task 3 approval | Potentially defensible only after chronological split and explicit terminology. |

## Resolution order for a future task

1. Resolve OQ-1 and OQ-2 without changing Task 2 data or credentials in source control.
2. Establish OQ-3 through a run-specific accounting procedure; capture broker/Influx/alert baseline snapshots.
3. Execute only the G2 H1 smoke test if protocol approval is given.
4. Resolve OQ-5 before any accelerated or extended replay.
5. Resolve OQ-6 through an official-file provenance audit before considering a genuine-label result.
6. Resolve OQ-8 before training any experimental model.

Until these conditions are met, a future report must use the terms **planned**, **not measured**, or **unresolved** rather than filling the corresponding value with zero or inferring success from an HTTP response.
