# Live Alert-Deduplication Validation

**Validation date:** 2026-10-05  
**Deduplication window:** 15 minutes

## Controlled duplicate event

Two identical authenticated machine-token telemetry submissions were made to
`POST /api/v1/ingestion` for device 1. Both carried `energyConsumed = 1.0` and
the same UTC timestamp, and both returned HTTP 201.

The ML worker published two anomaly results. The alert service created one
`ML_ANOMALY` alert with the key `1:1:ML_ANOMALY` and logged:

`Suppressed duplicate alert with key 1:1:ML_ANOMALY inside 15 minutes`

The database observation after the pair was one ML anomaly alert for that key
(alert id 481). This demonstrates that duplicate event delivery does not create
a second notification record during the configured window.

## Delivery confirmation

After restoring the Mailpit container, a separate high-energy telemetry event
for device 2 returned HTTP 201. The alert service logged successful email
delivery; the persisted alert (id 482) was `ML_ANOMALY`, `sent = true`, and
Mailpit recorded one message to `alex.j@example.com` with subject
`Energy Usage Alert for User 1`.

The controlled end-to-end run recorded later is stronger, independent delivery
evidence: `evidence/13_end_to_end/review2_e2e_results_20261005-214326.json`
requires a matching `THRESHOLD` alert with `sent = true` and a new matching
Mailpit message before it passes.
