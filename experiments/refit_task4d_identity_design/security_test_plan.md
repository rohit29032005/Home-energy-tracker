# Task 4D: Future Security Test Plan

## Status

This is a test **plan**, not test execution. Task 4D performed no runtime test, started no service, created no identity/device, issued no token, and sent no HTTP request. Entries below describe future evidence required after separate deployment and request-execution approvals.

## Entry gates before any future test

1. Approve the isolated OIDC/Keycloak topology, storage, issuer/JWK URLs, and administrator bootstrap workflow.
2. Approve persistent initialization of the isolated provisioning environment and any later Task 4C telemetry environment.
3. Approve the secret-management/injection mechanism and new secret generation.
4. Approve the two-stage profile/device provisioning procedure and mapping ledger controls.
5. Pin/approve the runtime images and resolve the current Kafka transport-security review item.
6. Obtain a separate explicit authorization before a first HTTP request, even if the request is framed as a smoke test.

## Planned checks

| ID | Future test objective | Method at future approval | Expected evidence / pass condition | Current status |
|---|---|---|---|---|
| ST-01 | Verify isolated issuer configuration | Compare configured issuer/JWK URLs with isolated token issuer and gateway reachability. | Gateway trusts only the isolated issuer; no route to existing development Keycloak is used. | Not run. |
| ST-02 | Reject invalid OIDC tokens | Use controlled tokens with invalid signature, wrong issuer, expired time, or missing role. | Gateway denies access; no profile/device change occurs. | Not run. |
| ST-03 | Verify ADMIN role boundary | Attempt permitted profile creation with isolated `ADMIN`; attempt same action with `USER`. | `ADMIN` is authorized; `USER` is denied. Returned profile IDs are recorded only after approved state-changing test. | Not run. |
| ST-04 | Verify `home_energy_user_id` ownership boundary | Use separate optional H1/H2/H4 user tokens after attributes are configured. | Each non-admin identity accesses only its mapped application profile; cross-household request is denied. | Not run; optional UI scope. |
| ST-05 | Verify private-service boundary | Attempt direct host access to User/Device/Ingestion/Usage services from outside the isolated network. | Private services are not host-exposed; API Gateway is the intended entry point. | Not run. |
| ST-06 | Verify one-profile/one-device provisioning ledger | Inspect approved returned records after provisioning. | Exactly one `GENERAL` device is linked to each H1/H2/H4 experiment profile; no source label is treated as an ID. | Not run. |
| ST-07 | Verify machine token exact binding | Test each valid device ID/secret pair and controlled wrong-token/cross-device pairs. | Only the correct pair is accepted; wrong, missing, duplicate, or cross-bound pairs are denied. | Not run; requests require separate approval. |
| ST-08 | Verify Gateway/Ingestion map parity | Use a redacted configuration parity check after secret injection. | Same three device identifiers exist at both endpoints; secret values are never printed. | Not run. |
| ST-09 | Verify JWT-originated ingestion path | Use a valid owner JWT and gateway proof path only after approved test design. | Ownership is enforced and caller-supplied privileged headers cannot bypass it. | Not run. |
| ST-10 | Verify secret non-disclosure | Inspect redacted logs, config outputs, replay logs, and reports. | No password, JWT, device token, internal proof, or private key appears. | Not run. |
| ST-11 | Verify fresh-store isolation | Inspect only approved experiment database/identity/Influx/Kafka resources after startup. | No existing-stack volume, database, issuer, bucket, topic, or user is accessed. | Not run. |
| ST-12 | Verify restart/rotation plan | Conduct a separately approved controlled token-rotation exercise. | Revoked/replaced device secret no longer works; new mapping works; evidence has no values. | Not run; procedure not yet approved. |
| ST-13 | Verify safe failure behavior | Test absent mapping, malformed mapping, missing gateway proof, and schema error before replay. | Service fails closed or rejects request; no security bypass is introduced. | Not run. |

## Test data and evidence handling

- Use a controlled isolated test fixture only; never development profiles, existing device tokens, or real household credentials.
- Do not place raw authorization headers, JWTs, device tokens, or database passwords in test scripts, screenshots, terminal history, CSV results, or research artifacts.
- Record only redacted configuration identifiers, timestamp, component, test ID, assertion, result, and approver.
- State-changing tests must be ordered from profile/device provisioning tests to authentication-negative tests and then to any first telemetry smoke test; no replay or data ingestion is part of this plan.
- Ambiguous network outcomes must be treated as not proven. Do not rerun a potentially state-changing request until its side effect is reconciled through an approved method.

## Coverage boundary

This test plan evaluates identity, authorization, configuration parity, and isolation. It does not validate ML model quality, REFIT replay correctness, anomaly generation, alerting effectiveness, or research-paper results. Those need separate approved protocols after the identity/provisioning boundary is complete.
