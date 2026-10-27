# Task 4D: Isolated OIDC Architecture Review

## Scope and decision

This is a read-only design review for the proposed REFIT H1, H2, and H4 experiment. No container was started, no realm, user, profile, device, credential, token, database, or configuration was created or changed, and no HTTP request was made.

**Decision: NO-GO for an isolated deployment-only smoke test.** The application can technically use an independent issuer through configuration, but the isolated issuer, realm design, credentials, device identities, and initialization approval do not yet exist.

## 1. Verified current authentication architecture

| Area | Verified implementation evidence | Design implication |
|---|---|---|
| OIDC resource server | `api-gateway/pom.xml:32`; `api-gateway/src/main/resources/application.properties:7-11` | API Gateway is the OIDC/JWT validation boundary. Its issuer and JWK-set URLs are externally configurable. |
| Gateway authorization | `api-gateway/src/main/java/com/hometracker/api_gateway/config/SecurityConfig.java:31-69` | The gateway maps Keycloak `realm_access.roles` values to Spring `ROLE_*` authorities. `POST /api/v1/user` requires `ADMIN`; protected application routes require `USER` or `ADMIN`. |
| Ownership claim | `api-gateway/src/main/java/com/hometracker/api_gateway/filter/OwnershipGatewayFilter.java:75-105` | A non-admin browser token needs a numeric `home_energy_user_id` claim. An administrator may create application profiles without that claim. |
| Existing development realm | `docker/keycloak/home-energy-realm.json:2-66`; `docker-compose.yml:96-109` | The current `home-energy` realm is development/import based. It contains development accounts and credentials and must not be copied, reused, or connected to the experiment. |
| Existing browser client | `docker/keycloak/home-energy-realm.json:14-38`; `frontend/src/services/auth.ts:160-205` | The dashboard is a public Authorization Code + PKCE client. Its current callback is derived from `window.location.origin`; its current local origin must not be reused for the isolated deployment without an approved UI-origin decision. |
| Existing CLI client | `docker/keycloak/home-energy-realm.json:41-66` | The direct-grant CLI client is a development/test construct. It must not become an unattended experiment provisioning mechanism without a separate security review. |
| Claim mapper | `docker/keycloak/home-energy-realm.json:25-36,49-60` | The user attribute `homeEnergyUserId` is mapped into JWT claim `home_energy_user_id` as a numeric value. |
| Device-machine authorization | `api-gateway/src/main/java/com/hometracker/api_gateway/filter/IotIngestionTokenFilter.java:60-128`; `ingestion-service/src/main/java/com/hometracker/ingestion_service/security/IngestionAuthorizationService.java:67-185` | Device telemetry uses separately configured device-bound secrets; it is not authenticated by an OIDC user session. Gateway recognizes configured machine tokens and Ingestion Service makes the decisive exact device-ID-to-token check. |

### Current development Keycloak limitations

The existing Compose definition starts Keycloak in development import mode (`start-dev --import-realm`). In the inspected service block, it has no explicit Keycloak database, persistent identity volume, or hostname configuration. Therefore it is not an acceptable template for a durable isolated experiment identity service. The existing import also includes development credentials; their values are deliberately not reproduced here.

## 2. Isolated issuer compatibility

### Verified compatibility

The gateway reads the OIDC issuer and JWK-set endpoints from configuration keys `KEYCLOAK_ISSUER_URI` and `KEYCLOAK_JWK_SET_URI` (`api-gateway/src/main/resources/application.properties:8-9`). Therefore a separate Keycloak/OIDC issuer is technically compatible **without modifying backend source code**, provided that:

1. the configured issuer exactly matches the token `iss` claim;
2. the JWK-set URL is reachable from the isolated gateway network;
3. the issued access token contains the expected realm role structure; and
4. any non-admin household identity carries a valid numeric `home_energy_user_id` claim.

### Task 4C boundary

The static Task 4C Compose design contains eight services and intentionally has no Keycloak service. Its gateway reads externally supplied `REFIT_KEYCLOAK_ISSUER_URI` and `REFIT_KEYCLOAK_JWK_SET_URI` values (`experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml:202-205`). Consequently, it cannot become self-contained by itself. A future approved design must choose one of the following:

1. a separately operated, isolated Keycloak/OIDC service with isolated issuer/JWK URLs; or
2. a separately reviewed Compose overlay/new deployment composition that adds a dedicated Keycloak service, isolated identity storage, and an isolated identity network.

Neither option is implemented or authorized by Task 4D.

## 3. Recommended future isolated-realm design

The following is a proposed future configuration, not an implementation instruction to execute now.

| Identity or client | Required role/claim | Least-privilege purpose | Notes |
|---|---|---|---|
| Isolated bootstrap administrator | `ADMIN` only | Creates the three application profiles and devices through the secured gateway | Do not grant this identity device telemetry credentials or routine household access. |
| REFIT H1 household identity (optional) | `USER`, one `home_energy_user_id` | Browser demonstration of its own application profile | Only needed if a per-household browser login is in scope. It is not needed for machine replay. |
| REFIT H2 household identity (optional) | `USER`, one `home_energy_user_id` | Same as H1 | Must receive its own returned application profile ID, never source household number. |
| REFIT H4 household identity (optional) | `USER`, one `home_energy_user_id` | Same as H1 | Must receive its own returned application profile ID, never source household number. |
| Isolated dashboard client (optional) | Authorization Code + PKCE S256 | Interactive browser login | Add only after an isolated dashboard origin is chosen; restrict redirect URI and web origins to that exact origin. |
| Provisioning client (optional) | Narrowly scoped realm-management permissions | Controlled administrative automation, if separately approved | A confidential client and its secret require a separate approval and secret-management review. |

The future isolated realm must be distinct from `home-energy`; use independent administrative credentials, signing material, client configuration, and durable identity storage. It must not import existing user records or configuration wholesale because the development import includes identities and credentials that are out of scope for this experiment.

## 4. Profile-to-identity relationship

An application profile and a Keycloak identity are separate records:

1. An `ADMIN` gateway session creates an application profile; the User Service database assigns and returns its ID (`user-service/src/main/java/com/hometracker/user_service/controller/UserController.java:25-30`; `.../service/UserService.java:21-32`).
2. If an optional individual household browser identity is required, an authorized administrator sets that returned ID as the identity's `homeEnergyUserId` attribute.
3. The identity receives a fresh token, whose mapper produces `home_energy_user_id`.

There is no source-side Keycloak Admin API integration, no application database field for a Keycloak subject, and no automatic synchronization. This mapping is therefore a future controlled operational step. It must be recorded in an experiment ledger using only source household label, returned application profile ID, Keycloak identity alias, and approval record; it must contain no passwords, client secrets, or device secrets.

## 5. Device authorization relationship

Machine telemetry does not require the three optional OIDC household identities. After a profile and one `GENERAL` device exist, a future operator would generate one unique device secret for that database-generated device ID. The mapping format accepted by the services is `deviceId:token`; the parser rejects duplicate device IDs and token reuse (`IngestionAuthorizationService.java:149-177`).

The same isolated mapping must be injected into both API Gateway and Ingestion Service. Gateway's token recognition alone is insufficient: Ingestion Service compares the submitted device ID and device secret exactly (`IngestionAuthorizationService.java:84-104`). The backend has no token issuance, persistence, rotation, or retrieval API; token lifecycle is external to the application.

## 6. Callback, issuer, and storage decisions still required

| Decision | Why it is required | Current status |
|---|---|---|
| Isolated issuer hostname/URL | It defines the immutable token issuer and gateway configuration. | Unresolved. |
| Isolated JWK-set network route | Gateway must retrieve verification keys without reaching the existing identity service. | Unresolved. |
| Identity persistence | Realm, roles, users, and mappings must survive restart. | Unresolved. |
| Isolated admin interaction method | Required to obtain an `ADMIN` token without reusing a development account or unsafe grant. | Unresolved. |
| Dashboard callback/web origin | Task 4C has no frontend service; no isolated browser origin is defined. | Unresolved and not required for telemetry-only replay. |
| Optional per-household browser identities | Needed only for individual UI demonstrations, not machine telemetry. | Scope decision pending. |

## 7. Conclusion

The existing source supports a future separate issuer through configuration and already separates browser JWT authorization from device-bound ingestion authorization. However, no isolated issuer, realm, trusted issuer URL, durable identity storage, safe administrator bootstrap path, or approved credential injection mechanism exists. The proposed design is suitable for a future **planning review only**. It is not ready for deployment-only smoke testing.
