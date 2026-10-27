# Security and frontend regression validation

**Execution date:** 2026-10-11  
**Scope:** local source-level regression only

## Result summary

Four independently executed Java test commands completed with **46 tests
passed**, **0 failures**, **0 errors**, and **0 skipped**:

| Module | Command scope | Tests |
|---|---|---:|
| API Gateway | GatewaySecurityFilterTest | 8 |
| Usage service | UsageAccessVerifierTest and UsageControllerAuthorizationTest | 10 |
| Alert service | AlertControllerAuthorizationTest, AlertContextClientInternalAuthenticationTest, AlertServiceDeduplicationTest | 11 |
| Insight service | Full Maven test suite | 17 |

The frontend lint and Vite production build also passed. Vite reported only
the existing generated-chunk size advisory; it did not fail the build.

## Exact Java commands

Run each command from its named service directory:

~~~powershell
$env:MAVEN_OPTS='-Duser.home=C:\Users\anju2\Desktop\Home-Energy-Tracker -Dmaven.repo.local=C:\Users\anju2\Desktop\Home-Energy-Tracker\.m2-task6'
mvn -B -Dtest=GatewaySecurityFilterTest test

mvn -B '-Dtest=UsageAccessVerifierTest,UsageControllerAuthorizationTest' test

mvn -B '-Dtest=AlertControllerAuthorizationTest,AlertContextClientInternalAuthenticationTest,AlertServiceDeduplicationTest' test

mvn -B test
~~~

The final executions completed at approximately 01:14 Asia/Kolkata time.
Maven produced standard Mockito/JDK dynamic-agent warnings but no test
failure.

## Frontend commands

~~~powershell
Set-Location frontend
& 'C:\Program Files\nodejs\npm.cmd' run lint
& 'C:\Program Files\nodejs\npm.cmd' run build
~~~

## Configuration check

The development and production Compose files were parsed successfully with:

~~~powershell
$env:DOCKER_CONFIG='C:\Users\anju2\Desktop\Home-Energy-Tracker\.docker-config-validation'
docker compose -f docker-compose.yml config --no-interpolate --quiet
docker compose -f docker-compose.prod.yml config --no-interpolate --quiet
~~~

This is a syntax/environment-wiring check, not a running-container check.

## Runtime limitation

An earlier validation process received a permission-denied response while
connecting to the Docker named pipe. A later elevated 2026-10-11
`docker compose ps` recheck found that the
`//./pipe/dockerDesktopLinuxEngine` pipe did not exist. Therefore no live
Docker, browser, Keycloak, Kafka, InfluxDB, Mailpit, or service-to-service
network claim is made by this evidence record.
