# Alert deduplication unit validation

**Execution date:** 2026-10-10 (local environment)

Command executed from `alert-service` with Java 17:

```powershell
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\\.m2-task6'
mvn -B -Dtest=AlertServiceDeduplicationTest test
```

Result: **4 tests passed; 0 failures; 0 errors; 0 skipped.**

The focused `AlertServiceDeduplicationTest` executed four cases against mocked repository and mail dependencies:

| Scenario | Observed result |
|---|---|
| First alert for a user/device/type key | Created and email invoked once |
| Repeated alert for the same key inside 15 minutes | Suppressed; no second email |
| Existing alert older than 15 minutes | New alert created |
| Same user, different devices | Two independent alerts created |
| Different users with the same device identifier | Two independent alerts created |

The service key format is `userId:deviceId-or-HOUSEHOLD:alertType`. Runtime persistence, Kafka delivery, and SMTP delivery have **NOT YET BEEN MEASURED**: on 2026-10-10, `docker compose ps --all` could not connect to `//./pipe/docker_engine`.
