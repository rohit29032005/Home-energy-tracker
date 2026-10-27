# Task 4E: Failure and Recovery Plan

## Scope and governing rule

This is a future operational safety plan. It performs no recovery action. The governing rule is: **preserve evidence, halt the affected isolated stage, and never delete or alter a resource until its exact identity and approval scope are confirmed.**

Do not use broad cleanup operations, root-level Compose commands, `prune` operations, automatic database recreation, unscoped `down -v`, direct SQL repair, security disablement, or reuse of development credentials. The provisioning and full telemetry stages may intentionally share one approved experiment-only MySQL state, so indiscriminate volume deletion could destroy required profile/device mappings.

## 1. Pre-start/configuration failure

| Failure | Detection | Safe response | Recovery boundary |
|---|---|---|---|
| Required Task 4C variable absent | Static Compose/interpolation validation fails before container creation. | Do not insert a placeholder or existing credential. Record the missing variable name only and return to the relevant approval gate. | No runtime state should exist. |
| Device map lacks returned IDs | Mapping review cannot link every ID to the approved ledger. | Stop. Do not guess IDs, use H1/H2/H4 as IDs, or enable legacy/global token fallback. | Resolve through approved provisioning only. |
| Gateway/Ingress map mismatch | Redacted parity check shows different identifiers or references. | Do not start full telemetry stage. Correct the approved secret injection package under G4. | No request/replay action is permitted. |
| Issuer/JWK configuration ambiguous | Isolated endpoint/issuer/client relationship is not documented. | Stop. Do not point Gateway to the existing development issuer or disable `SECURITY_ENABLED`. | Resolve through OIDC topology review. |

## 2. Persistent-store initialization failure

| Failure | Detection | Safe response | Recovery boundary |
|---|---|---|---|
| MySQL first initialization/migration fails | Future approved MySQL health or User Service/Flyway evidence indicates failure. | Stop before Device Service/Gateway provisioning. Preserve redacted service logs, exact volume identity, and Flyway history evidence. Do not direct-SQL repair. | Reuse/retry or delete/recreate only the verified experiment volume after a separate retention/destructive-action approval. |
| Device Service becomes available before migration completion | User Service/Flyway evidence is incomplete while Device Service is merely started. | Treat as not ready; do not create/read devices. | Resume only after User Service migration and application health are verified. |
| Isolated identity store bootstrap fails | Realm/issuer/JWK readiness cannot be verified. | Stop. Do not import/copy development realm/user/credential data. | Correct the separately approved isolated identity design; retain/destroy only isolated state under approval. |
| Kafka or Influx first initialization is partial | Future metadata/health evidence is incomplete. | Do not reformat, change Kafka cluster identity, or assume Influx setup is idempotent. Preserve resource identifiers and redacted diagnostics. | Disposition needs a separate explicit approval for only the named experiment resource. |

## 3. Provisioning failure

| Failure | Detection | Safe response | Recovery boundary |
|---|---|---|---|
| One profile create result is ambiguous | Future approved request times out or loses response. | Do not repeat blindly. Reconcile through supported authenticated application reads using the unique experiment alias/email. | Resume only missing work after approval; profile/device deletion is separate state-changing work. |
| Duplicate profile or device is found | Ledger/cardinality check reports more than one intended record. | Halt provisioning. Do not infer ownership or reuse a duplicate record. | Use an approved reconciliation/cleanup plan limited to the experiment-only state. |
| Returned ID does not match ledger | Evidence discrepancy or source-household label confusion. | Stop map preparation; no secret is generated for uncertain ID. | Correct ledger under two-person/approver review before continuing. |
| Alerting flag is unexpected | Profile verification does not show planned `alerting=false`. | Stop before full stage because Usage Service has a scheduled threshold path. | Correct only through approved administrative workflow. |

## 4. Authentication and authorization failure

| Failure | Detection | Safe response | Recovery boundary |
|---|---|---|---|
| Administrator token lacks required role | Gateway denies profile creation. | Do not broaden roles or bypass gateway. Check isolated realm role mapper and bootstrap identity design. | Identity changes require G2-level approval. |
| User ownership claim is missing/invalid | Non-admin route is denied or ownership cannot be established. | Do not impersonate with headers or map a REFIT label as an ID. | Correct only the isolated Keycloak attribute/mapper after approval and issue a fresh token. |
| Device token is rejected | Future approved mapping test fails exact binding. | Stop affected device; do not retry under another device ID or use global fallback. | Reconcile map reference and rotate only through approved external secret lifecycle. |
| Secret appears in logs/output | Review finds raw token/password/header/key material. | Stop affected activity; quarantine/redact evidence; treat secret as exposed. | Replace/revoke through approved secret and identity procedures, then assess whether any state was accessed. |

## 5. Isolation breach or accidental shared-resource reference

**STOP condition:** any connection, network attachment, volume mount, issuer, database, bucket, topic, or consumer group associated with the existing application or another environment.

Future response:

1. halt further writes and deployment progression;
2. capture redacted evidence of endpoint/resource identifiers only;
3. identify which containers/resources are clearly experiment-owned;
4. stop only those clearly identified experiment-owned containers if separately authorized;
5. do not attempt cleanup against a potentially shared database, network, volume, broker, or identity service; and
6. return to isolation design review.

## 6. Deployment-only smoke-test failure

If a future no-event smoke test detects an unexpected ingestion request, Kafka record, Influx point, scheduled alert publication, model call, simulator/replay process, or Alert/Insight call:

1. terminate the approved smoke-test procedure;
2. preserve redacted timing/log evidence and determine whether any state was produced;
3. do not run replay or repeat the condition;
4. reconcile state only within the identified experiment resources; and
5. require a revised approval gate and test plan before another attempt.

## 7. Safe resumption criteria

Resume a paused stage only when all are true:

- the failing resource is confirmed experiment-only;
- the underlying cause is documented without secrets;
- appropriate approval for the corrective action exists;
- profile/device/secret ledger consistency is restored; and
- a redacted recovery evidence record is accepted.

No Task 4E recommendation authorizes recovery execution.
