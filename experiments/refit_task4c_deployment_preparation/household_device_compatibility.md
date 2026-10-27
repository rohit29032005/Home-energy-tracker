# Task 4C — Household and Device Compatibility Review

## Result

**Supported by the existing application model, subject to later approved provisioning.** No schema, backend, authorization, or token-lifecycle change is required merely to represent the three household profiles and their aggregate devices.

## Proposed future records

| REFIT source household | Application record relationship | Planned device type | Rationale |
|---:|---|---|---|
| H1 | One separate application household profile -> one logical aggregate meter | `GENERAL` | Keeps aggregate REFIT power distinct from appliance-level semantics. |
| H2 | One separate application household profile -> one logical aggregate meter | `GENERAL` | Prevents dashboard/usage aggregation with H1 or H4. |
| H4 | One separate application household profile -> one logical aggregate meter | `GENERAL` | Preserves source-household identity in the application model. |

## Verified implementation evidence

| Requirement | Evidence | Conclusion |
|---|---|---|
| Independent profile creation | `UserController.java:25-29` calls `UserService.createUser`; `UserService.java:21-32` persists a new user | Separate application profiles are supported. |
| Device ownership relationship | `DeviceDto.java:15-28` requires a `userId`; `DeviceService.java:27-35` persists it | Each device can belong to a distinct profile. |
| Aggregate meter category | `DeviceType.java:3-15` includes `GENERAL` | The proposed meter type is valid. |
| Referential integrity | `V2__device_table.sql` defines device ownership through `user_id` | Database model supports one device per profile. |
| Secure provisioning boundary | `SecurityConfig.java:39-46` requires `ADMIN` for `POST /api/v1/user`; `UserController.java:25-29` delegates to the gateway proof | Profiles must be created through the authorized gateway workflow, not by direct database insertion. |
| Device credentials | `IngestionAuthorizationService.java:67-81,149-177` parses deviceId-to-token mapping and fails closed | Three distinct returned device IDs and three distinct credentials are required later. |

## Important constraints

1. REFIT identifiers `1`, `2`, and `4` are source-household identifiers only. They must not be mapped to backend IDs 1, 2, or 4 by numerical coincidence.
2. The fresh database will run the existing User Service Flyway migrations when a later deployment is approved; existing seed data means future IDs are database-assigned and cannot be predicted.
3. Create the profile first, create its device using the returned profile ID, capture the returned device ID in a non-secret ledger, then inject its unique secret by reference into both Gateway and Ingestion configuration.
4. Set future experiment profiles to `alerting=false`. Usage Service otherwise contains a scheduled threshold pathway that can publish `energy-alerts` on the isolated broker. Alert Service is absent in Task 4C, but avoiding such messages is still the appropriate bounded experiment setting.
5. The verified data contract remains `derived_interval_energy_kwh -> energyConsumed`; neither a house number nor aggregate power in watts substitutes for a device ID or kWh interval value.

## Current state

No Task 4C profile, device, mapping, credential, or request exists. This document describes compatibility only and grants no provisioning authority.
