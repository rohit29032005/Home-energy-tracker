# Static Test-Configuration Audit

This audit intentionally records configuration **keys and behavior only**. It does not copy or expose configuration values, credentials, tokens, or passwords.

| Service | Test configuration observed | Static conclusion | Execution decision |
|---|---|---|---|
| `alert-service` | Datasource, JPA, Flyway, Kafka, scheduler, mail, device-service, and user-service keys in `src/test/resources/application.properties` | A full application context can initialize persistence, messaging, scheduling, mail, or HTTP-client-related behavior despite test-specific settings. | Application-context test excluded; mock-only source tests catalogued. |
| `device-service` | Datasource, JPA, Flyway, and scheduler keys in `src/test/resources/application.properties` | Full context has persistence and migration-relevant configuration. | Application-context test excluded; controller/security tests catalogued. |
| `ingestion-service` | Kafka, scheduler, and simulation keys in `src/test/resources/application.properties` | A full context can activate messaging or simulation-related paths. | Application-context test excluded; MockMvc/Mockito/MockRestServiceServer tests catalogued. |
| `usage-service` | Kafka, scheduler, InfluxDB, device-service, and user-service keys in `src/test/resources/application.properties` | Full context or embedded-broker tests are unsuitable for the zero-side-effect scope. | Application context and embedded Kafka excluded; mock/unit tests catalogued. |
| `api-gateway`, `insight-service`, `user-service` | No service test resource file was found by this audit in the inspected conventional test-resource location. | Absence of a conventional local test properties file does not prove side-effect freedom. | Only the fully in-process gateway filter test was freshly run; remaining suites catalogued. |

## Source-level test harness classification

- `MockMvcBuilders.standaloneSetup`, `MockServerWebExchange`, Mockito, `MockHttpServletRequest`, and `MockRestServiceServer` are in-process test doubles; they do not bind a real network listener or contact the current Docker stack when configured as shown in the inspected test sources.
- `@WebMvcTest` is a web-slice context rather than an end-to-end deployment test. It may still write build reports when Maven is run.
- `@SpringBootTest` and application context-loading suites were considered potentially side-effecting for this audit even when historical reports were available.
- `@EmbeddedKafka` explicitly starts an embedded broker and was treated as a component-integration test, not a pure unit test.

## Test frameworks and dependencies observed

- Maven services declare Spring Boot test dependencies; alert, ingestion, and usage services additionally declare Spring Kafka test dependencies.
- The ML service declares test/development dependencies separately. The active local interpreter did not have its Kafka client import available; this blocked two otherwise mock-based worker test modules.

The configuration audit is static only. It makes no claim about the effective configuration of a running container or deployed service.

