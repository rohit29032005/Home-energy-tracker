# Task 4D: Secret Management Plan

## Scope and principle

This is a non-executing design plan. It identifies secret classes, custody boundaries, and future controls. It contains no secret value, generated token, credential, private key, or connection string.

The existing repository excludes common environment and key files through `.gitignore` (`.gitignore:23` onward), but it does not show a dedicated secret manager, Docker-secrets workflow, device-token issuance API, or automated rotation lifecycle. The isolated experiment must therefore use new values and an approved external secret-injection process; it must not reuse development values.

## 1. Verified secret-related facts

| Fact | Evidence | Consequence |
|---|---|---|
| The current development realm import contains development identity records and credentials. | `docker/keycloak/home-energy-realm.json`; `docker-compose.yml:96-109` | Do not copy the realm import, accounts, passwords, client configuration, or signing context into REFIT. |
| Gateway issuer/JWK configuration is environment-driven. | `api-gateway/src/main/resources/application.properties:7-11` | Isolated issuer values may be supplied without source changes, but must be new isolated values. |
| Device mappings are parsed at service startup from configuration. | `ingestion-service/src/main/java/com/hometracker/ingestion_service/security/IngestionAuthorizationService.java:67-81,149-177` | Device credentials cannot be created or rotated through a backend API. Future rotation requires external secret replacement and an approved service restart. |
| Gateway and Ingestion Service both need the device mapping. | `api-gateway/.../IotIngestionTokenFilter.java:60-128`; `IngestionAuthorizationService.java:84-104` | The two services must receive the same mapping atomically enough to avoid an authorization mismatch. |
| Existing internal credentials are development shared-secret controls, not mutual TLS or workload identity. | `README.md:43-48` | New isolated values reduce cross-environment risk but do not turn the design into per-service identity. |

## 2. Secret inventory and least-privilege distribution

| Secret class | Future holder(s) only | Must not be exposed to | Required control |
|---|---|---|---|
| Isolated Keycloak bootstrap administrator credential | Isolated identity-service bootstrap process; approved identity administrator | Application containers, replay client, reports, source control, terminal logs | Generate independently; store in approved secret storage; change or retire after bootstrap according to the approved identity policy. |
| Keycloak signing/identity-store material | Isolated identity service only | Gateway runtime configuration, replay client, application services, source control | Persistent encrypted identity storage and least-privilege service access; no development signing material reuse. |
| Optional confidential provisioning-client secret | Approved provisioning automation only, if separately approved | Browser client, replay client, ordinary application services | Narrow realm-management permission; short expiry/rotation plan; do not use a public password grant for unattended administration. |
| OIDC issuer/JWK URLs | Gateway configuration only (not secret values, but trusted security configuration) | Existing development stack if cross-environment access would occur | Validate exact issuer/JWK pair; restrict network path to isolated issuer. |
| Gateway internal proof | API Gateway, User Service, Device Service, Ingestion Service, Usage Service as required by source checks | Replay client, browser clients, external simulator, reports | New isolated value only; inject at runtime; avoid application logs. |
| Internal-service credential | User Service, Device Service, Usage Service only where internal reads are allowed | Replay client, browser clients, Gateway unless source requires it | New isolated value only; never conflate with gateway proof. |
| H1 device secret | Gateway, Ingestion Service, H1 replay process only during an approved H1 run | H2/H4 processes, browser users, other services | Generate after H1 device ID exists; unique value; exact device binding. |
| H2 device secret | Gateway, Ingestion Service, H2 replay process only during an approved H2 run | H1/H4 processes, browser users, other services | Same rule as H1. |
| H4 device secret | Gateway, Ingestion Service, H4 replay process only during an approved H4 run | H1/H2 processes, browser users, other services | Same rule as H1. |
| MySQL credentials | MySQL and the isolated services that require database access | Replay client, OIDC identities, reports | Separate experiment database/user; no existing stack credential reuse. |
| InfluxDB bootstrap credential | Initialization workflow only | Usage Service after a scoped writer credential is available; replay client | First initialization needs explicit approval; later use a least-privilege writer credential if available. |
| InfluxDB scoped writer credential | Usage Service only after approved provisioning | Replay client, OIDC identities, other services | Limit to experiment org/bucket write scope. |

## 3. Required storage and injection model

The future deployment must use one approved secret source outside Git. Acceptable selection is pending user/institutional approval; examples include an approved secret manager, protected local environment injection, or a secure CI/CD secret store. Plaintext values must not be placed in:

- tracked Compose files;
- `.env.example` files;
- the replay source, configuration examples, or reports;
- Keycloak realm JSON committed to the repository;
- terminal commands or PowerShell history where practical;
- `docker compose config` screenshots/logs;
- application, simulator, or replay logs; or
- the profile/device mapping ledger.

Example configuration files may name variables and contain placeholders only. The Task 4C convention of `REFIT_`-prefixed values should be retained for environment separation. The placeholder files must remain harmless if inspected or committed.

## 4. Secret-reference ledger

Before any future deployment, maintain an access-controlled non-secret ledger with these fields:

| Field | Allowed content |
|---|---|
| Experiment environment identifier | Non-secret isolated deployment label |
| REFIT source household | H1, H2, or H4 |
| Returned application profile ID | Database-generated numeric identifier |
| Returned `GENERAL` device ID | Database-generated numeric identifier |
| Device-secret reference | Vault/secret-store reference label only; never the secret value |
| Issuance/rotation timestamp | Administrative metadata |
| Approver and operator | Accountability metadata |
| Verification status | Mapping parity and cardinality evidence |

The ledger is not a credential store. It must not contain passwords, bearer tokens, JWTs, internal proofs, client secrets, connection URLs with embedded credentials, or private keys.

## 5. Device-token lifecycle

1. Do not generate any device token until the corresponding database-generated device ID is known.
2. Generate a unique high-entropy secret independently for each H1/H2/H4 device.
3. Bind one secret to one returned device ID only; `IngestionAuthorizationService` rejects duplicate IDs and reused token values.
4. Inject the complete device-ID-to-secret mapping into API Gateway and Ingestion Service through the approved secret channel.
5. Validate identifier parity without printing token values.
6. Give an approved replay process only the active household's secret.
7. If a token is suspected exposed, stop its associated replay, generate a replacement through the approved workflow, replace the mapping in both services, and restart only with explicit future approval. Record only the secret-reference change in the ledger.

Because device credentials are configuration-only in the inspected implementation, revocation is operational rather than API-driven. It cannot be safely claimed as available until the future procedure is approved and tested.

## 6. Logging and evidence rules

Future validation evidence should record variable names, service names, device IDs, secret-reference labels, status codes, and redacted fingerprints only if a separate approved method exists. It must never log raw tokens or authorization headers. Troubleshooting must not enable broad debug logging for authentication libraries if such logs could include credentials.

No Task 4D command printed or created a secret. No secret lifecycle action is authorized by this plan.

## 7. Open decisions

1. Select and approve the secret-management/injection mechanism.
2. Approve the isolated Keycloak persistent identity-store and bootstrap procedure.
3. Decide whether a confidential provisioning client is needed; if not, use a manual administrator workflow under supervision.
4. Define the InfluxDB post-bootstrap least-privilege writer-token procedure.
5. Approve a future token rotation/restart procedure before real device secrets are issued.
