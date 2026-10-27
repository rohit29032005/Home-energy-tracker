# Real-world recorded data replay

`replay_stream.py` replays the Task 2 REFIT output through the existing Home Energy Tracker ingestion boundary:

```text
cleaned_dataset.csv
  -> replay_stream.py
  -> POST /api/v1/ingestion (API Gateway)
  -> Ingestion Service -> Kafka -> Usage / Insight / ML / Alert services
```

The source is **real-world recorded household electricity data replayed as a continuous/live-like stream**. It is not a real-time dataset.

## Verified payload contract

The replay tool uses the actual current gateway contract:

```http
POST http://localhost:8080/api/v1/ingestion
Content-Type: application/json
X-Device-Token: <WOKWI_INGESTION_TOKEN>
```

```json
{
  "deviceId": 101,
  "energyConsumed": 0.0005236111111111111,
  "timestamp": "2026-10-08T12:34:56.123456Z"
}
```

`energyConsumed` is the Task 2 **estimated interval energy in kWh**. It is not raw REFIT power in Watts and it is not a cumulative meter reading.

The gateway returns HTTP `201 Created` when it accepts a request. That proves only the ingress response; Kafka publication, InfluxDB persistence, alert processing, and dashboard visibility must be checked in a later verification task.

## Safety properties

- Default mode is dry-run. The script makes no HTTP request unless `--execute` is supplied.
- A JSON household-to-device mapping is mandatory. The script never assumes `deviceId == householdId`.
- The device token is taken from `REPLAY_DEVICE_TOKEN` or `WOKWI_INGESTION_TOKEN` in the environment/config. It is never recorded in logs or manifests.
- Each run stores original REFIT source time and the actual replay payload time separately.
- The current backend has no ingress idempotency key. The replay is therefore at-least-once at best, not exactly-once.
- Transport failures are not retried by default because the gateway may have accepted an event before its response was lost. `--retry-uncertain-transport` is an explicit opt-in and can duplicate data.
- Houses 3 and 11 retain their Task 2 solar-interference caveat in every receipt; they are not removed or treated as anomaly labels.

## One-time local configuration

```powershell
Set-Location 'C:\Users\anju2\Desktop\Home-Energy-Tracker'
Copy-Item real_data_replay\replay.env.example real_data_replay\replay.env
Copy-Item real_data_replay\device-map.seed-demo.example.json real_data_replay\device-map.json
```

Edit `real_data_replay\replay.env` and set `REPLAY_DEVICE_TOKEN` to the local `WOKWI_INGESTION_TOKEN` used by the running gateway. Do not commit that file.

`device-map.seed-demo.example.json` maps the five REFIT households to the repository's migration-defined demo device IDs 1–5. It is useful only for a controlled local smoke test and does **not** claim that the demo appliance labels correspond to REFIT appliances. For research replay, create or verify five dedicated local aggregate-meter devices (ideally isolated from alert-enabled demonstration accounts), then replace the IDs in `device-map.json`.

The gateway's device token is shared, and the ingestion service does not prove device existence or ownership. Device-map verification is an operator responsibility before `--execute`.

## Timestamp and timeline modes

| Option | Meaning | Suitable use |
|---|---|---|
| `--timestamp-mode current` | Uses the send-time UTC clock during execution. Original REFIT time remains in the receipt. | Practical live-like dashboard/pipeline exercise. |
| `--timestamp-mode rebased` | Preserves source-relative timing from `--replay-start-utc`, independent of replay speed. | Controlled replay-time analysis; accelerated execution can create future timestamps. |
| `--timestamp-mode source` | Sends original recorded REFIT timestamp. | Forensic/historical pipeline checks only. Current dashboard windows will not normally show 2014/2015 events. |
| `--timeline-mode relative` | Aligns each house's selected 14-day window at t=0 and preserves order inside each home. | Default concurrent multi-house simulation. This alignment is artificial and logged. |
| `--timeline-mode source` | Preserves global recorded UTC ordering across houses. | Historical-order work; it includes the large gap between 2014 and 2015 cohorts. |

`--speed` controls the wall-clock schedule, not the source data. `--max-events-per-second` is a conservative global HTTP start-rate ceiling and can make a high requested speed effectively slower. At `--speed 1`, the normal eight-second cadence is retained. The default relative timeline at speed 1000 represents roughly 14 days in about 20 minutes before rate limiting; this is a planning calculation, not a gateway capacity claim.

## Safe dry-run first

This creates receipts and validates input/mapping without sending any network request:

```powershell
python real_data_replay\replay_stream.py `
  --config real_data_replay\replay.env `
  --max-events 25 `
  --speed 100 `
  --timestamp-mode current
```

Inspect the generated directory beneath `real_data_replay\logs\`. It contains:

- `run_manifest.json` — selected config, input/map hashes, and caveats; no token.
- `sent_events.csv` — one final receipt per planned event, including source and replay timestamps.
- `failed_requests.csv` — every failed HTTP attempt, including retryability.
- `replay_summary.json` — event/status/energy totals. It explicitly does not claim downstream persistence.

## Controlled execute smoke test

Only after Docker/Gateway health and the device mapping have been verified:

```powershell
python real_data_replay\replay_stream.py `
  --config real_data_replay\replay.env `
  --max-events 5 `
  --speed 10 `
  --timestamp-mode current `
  --execute
```

This POSTs five real-data-derived interval-energy events. It can change local InfluxDB/MySQL/alert state depending on the mapped user and alert settings. Do not run a full replay against a demo user with a threshold alert enabled unless that alert behavior is intentional and recorded.

For an explicit normal-speed run, use `--speed 1`. For an explicit finite loop, use both `--loop --max-loops 2`; loops are allowed only with `--timestamp-mode current` so timestamp reuse is avoided.

## Retry interpretation

The tool retries confirmed retryable HTTP statuses (`408`, `429`, and `5xx`) with exponential backoff. Non-retryable client/authentication errors are logged and skipped unless `--stop-on-failure` is selected. A network/timeout error is logged as `TRANSPORT_UNCERTAIN` and is not retried unless `--retry-uncertain-transport` is passed explicitly. This is intentional because there is no backend event identifier or deduplication guarantee.

## Preflight commands

These are read-only and do not send telemetry:

```powershell
docker compose ps
Invoke-RestMethod -Method Get -Uri 'http://localhost:8080/actuator/health'
```

If the gateway is not healthy, fix the local stack first. A `POST` is never used as a health check because it mutates the pipeline state.
