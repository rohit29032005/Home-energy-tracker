# Task 4 Device-Mapping Verification Report

**Status:** BLOCKED — Task 4 stops at Step 1.  
**Checked:** 2026-10-12  
**Scope:** Read-only verification of the currently running Docker deployment. No data was replayed, no HTTP ingestion request was sent, no token value was printed, and no Docker, backend, database, model, or protocol change was made.

## Decision

The required one-to-one mappings for REFIT Houses 1, 2, and 4 cannot be verified from the existing running configuration. The frozen three-house primary experiment must therefore **not** start a dry run, payload submission, or multi-household replay.

## Runtime authorization evidence

The live `ingestion-service` was checked without displaying any credential values:

| Runtime check | Result |
|---|---|
| `INGESTION_AUTH_REQUIRED` | `true` |
| Device-token mapping present | Yes |
| Parsed mapped backend device IDs | `1` only |
| Mapping syntax | Valid |
| Legacy global-token authorization | Disabled |
| Runtime simulator device ID | `1` |

The live `api-gateway` has the same single mapped device identifier. Its machine-token acceptance does not remove the ingestion service's device-bound authorization check.

The ingestion authorization implementation obtains the configured token by the payload's `deviceId`. Consequently, a request for backend device `2` or `4` cannot safely reuse the device-`1` credential.

## Existing backend devices are not REFIT-house mappings

Read-only database verification confirmed that backend device IDs `1`, `2`, and `4` exist. They are appliance records owned by backend user `1`, rather than records identifying REFIT households.

| Backend device ID | Existing application record | Authorized in the active device-token mapping | Verified REFIT household association |
|---:|---|---|---|
| 1 | Refrigerator | Yes | No |
| 2 | Air Conditioner | No | No |
| 4 | Desktop Workstation | No | No |

The device table/model stores only device metadata and `user_id`; it has no REFIT-household identifier. Therefore, the numeric overlap between REFIT House 1/2/4 and backend device ID 1/2/4 is **not** evidence of a valid mapping.

## Required primary-cohort mapping result

| REFIT household | Confirmed backend device ID | Confirmed distinct valid device credential | Eligible for Task 4 replay |
|---:|---|---|---|
| 1 | Not established | Not established | No |
| 2 | Not established | Not established | No |
| 4 | Not established | Not established | No |

## Separate energy-unit compatibility result

The unit gate was independently verified and would be safe **after** the mapping blocker is resolved:

```text
Task 2 derived_interval_energy_kwh  ->  ingestion API energyConsumed
```

`energyConsumed` is summed as kWh by the implemented usage and insight layers. `original_aggregate_power_w` must remain provenance only; sending it as `energyConsumed` would introduce a Watts-versus-kWh error. The original REFIT timestamp must remain in an external replay ledger, while the future live-like payload timestamp follows the frozen Task 3 protocol.

## Why implementation stopped

Task 4 expressly requires resolution of device mappings before building an adapter or replay engine. Writing a tool that assumes `REFIT House N = backend device N`, or that reuses device `1` for all three houses, would violate the frozen household separation and authorization requirements. Accordingly, these files were deliberately **not created**:

- `replay_stream.py`
- `refit_compatibility_adapter.py`
- `replay_config.example.yaml`
- `.env.example` changes
- `README_replay.md`
- `dry_run_report.md`
- `payload_validation_report.csv`

## Minimum safe options requiring explicit approval

1. **Use existing devices:** an authorized operator supplies a non-secret, documented one-to-one REFIT House 1/2/4 to existing backend-device-ID mapping, then configures distinct device-bound credentials for those mapped IDs using approved runtime secrets. The gateway and ingestion service would need an approved restart. Tokens must never be committed, printed, or placed in reports.
2. **Create isolated experiment devices:** approve creation of three dedicated backend device records plus distinct runtime device credentials and an explicit REFIT-house-to-device mapping. This is a configuration/data change and is outside the authority of Task 4 as currently approved.
3. **Use the authenticated owner/JWT path:** explicitly approve this alternate credential route and provide a documented house-to-owned-device mapping. This changes the agreed authorization approach and needs protocol approval before use.
4. **Restrict a later smoke test to device 1:** this is possible only if separately approved, and it does **not** satisfy the frozen three-house primary cohort.

## Safe reproducibility checks

Run from the repository root. These commands intentionally emit only boolean status and numeric device IDs, never token values.

```powershell
docker compose ps
```

```powershell
docker compose exec -T ingestion-service sh -lc 'printf "INGESTION_AUTH_REQUIRED=%s\n" "${INGESTION_AUTH_REQUIRED:-<unset>}"; if [ -n "${IOT_INGESTION_DEVICE_TOKENS:-}" ]; then printf "IOT_MAPPING_PRESENT=true\n"; mapping_syntax_bad=0; old_ifs=$IFS; IFS=,; for mapping_entry in $IOT_INGESTION_DEVICE_TOKENS; do device_id=${mapping_entry%%:*}; case "$device_id" in ""|*[!0-9]*) mapping_syntax_bad=1 ;; *) printf "MAPPED_DEVICE_ID=%s\n" "$device_id" ;; esac; done; IFS=$old_ifs; if [ "$mapping_syntax_bad" -eq 0 ]; then printf "MAPPING_SYNTAX_PARSEABLE=true\n"; else printf "MAPPING_SYNTAX_PARSEABLE=false\n"; fi; else printf "IOT_MAPPING_PRESENT=false\n"; fi'
```

## Required approval before Task 4 can resume

Provide one approved mapping option above, including the non-secret statement of which backend device represents each REFIT household. After that, the next safe activity is a configuration and CSV-schema-only validation; no actual ingestion request will be made without a separate confirmation.
