# Usage-service InfluxDB retry and DLT validation

**Execution date:** 2026-10-10 (local embedded Kafka test; no Docker daemon)

## Purpose

This test verifies the failure path for a consumed `energy-usage` event when
the Usage Service cannot write the corresponding time-series point to InfluxDB.
It replaces the previous silent-log-and-ack behaviour with bounded retry and
dead-letter routing.

## Command executed

```powershell
Set-Location usage-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=UsageKafkaFailureRecoveryTest test
```

## Observed result

**2 tests passed; 0 failures; 0 errors; 0 skipped.**

The tests start an embedded one-partition Kafka broker. One configures the
Influx write mock to fail permanently; the other fails once and then succeeds
on the first retry. They send a valid energy-usage event and observed all of
the following:

| Expected behaviour | Observed result |
|---|---|
| Initial write plus configured retry attempts | Exactly 3 Influx write invocations (1 initial + 2 retries) |
| Permanent failure destination | One event was read from `energy-usage.DLT` |
| DLT payload | Serialized event includes `"deviceId":1` |
| Partition routing | Source and DLT record both used partition 0 |
| Transient failure recovery | Exactly 2 write invocations (1 initial failure + 1 successful retry) |
| DLT after transient recovery | A DLT observer initialized before publishing the source record read no new DLT record |

## Implemented policy

- `UsageService` now throws `InfluxWriteException` when an InfluxDB write
  fails instead of returning normally.
- `DefaultErrorHandler` applies a default 1-second fixed delay and two retries.
- `DeadLetterPublishingRecoverer` routes permanent failures to
  `<source-topic>.DLT` and is configured to fail if that DLT publish fails.
- `spring.kafka.listener.ack-mode=record` scopes successful acknowledgement to
  individual records.

## Boundaries

This is a broker-backed local test, not a live Docker/InfluxDB outage test. It
demonstrates the Spring Kafka retry/DLT wiring and same-partition routing under
a mocked write failure. The transient case proves recovery in this embedded
test; it does not measure a real InfluxDB reconnection or network fault. The
behaviour is **at-least-once**, not exactly-once:
a write that succeeds remotely but whose acknowledgement is lost may be
retried. A production DLT replay/runbook and a live Docker fault test remain
**NOT YET MEASURED**.
