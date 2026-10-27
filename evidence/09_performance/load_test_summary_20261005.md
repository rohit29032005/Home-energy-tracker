# k6 Ingestion Load-Test Summary

**Run:** `k6-summary-20261005-214732.json`  
**Executor:** official `grafana/k6` Docker image (used because no native k6
binary was installed)  
**Target:** `POST /api/v1/ingestion` through the local API gateway with the
configured device token

## Scenario

The real k6 script used a ramping-arrival-rate scenario: 1 request/s initially,
then 2 requests/s for 30 seconds, 5 requests/s for 30 seconds, 10 requests/s
for 30 seconds, and a 15-second ramp down. It submitted randomized 0.2–0.3 kWh
telemetry readings for device 1. This is a local, single-host capacity check;
it is not a distributed production benchmark.

## Measured results

| Measure | Observed value |
|---|---:|
| Ingestion requests / checks | 450 / 450 |
| Successful checks | 450 (100.00%) |
| HTTP failures | 0 (0.00%) |
| Mean HTTP duration | 39.44 ms |
| Median HTTP duration | 24.85 ms |
| p90 HTTP duration | 74.78 ms |
| p95 HTTP duration | 109.77 ms |
| Maximum HTTP duration | 503.36 ms |
| Mean achieved request rate | 4.281 requests/s |
| k6 p95 threshold | Passed (`p(95) < 2000 ms`) |
| k6 failure-rate threshold | Passed (`rate < 0.05`) |

Raw event-level output is retained in
`k6-raw-20261005-214732.json`; the exact k6 aggregate source is
`k6-summary-20261005-214732.json`. Hardware information captured with the run
is in `hardware-20261005-214732.json`.
