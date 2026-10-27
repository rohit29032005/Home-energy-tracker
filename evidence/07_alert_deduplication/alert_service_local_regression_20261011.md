# Alert service local deduplication and delivery-failure regression

**Execution date:** 2026-10-11  
**Execution mode:** focused local Maven tests; no Docker or SMTP runtime

## Command executed

~~~powershell
Set-Location alert-service
$env:MAVEN_OPTS='-Duser.home=<project-root> -Dmaven.repo.local=<project-root>\.m2-task6'
mvn -B -Dtest=AlertServiceDeduplicationTest test
~~~

## Observed result

**5 tests passed; 0 failures; 0 errors; 0 skipped.**

| Local contract | Observed behavior |
|---|---|
| Same user, same device, same alert type inside the configured 15-minute window | First alert is created; the later alert is suppressed |
| Different devices | Alert keys remain independent |
| Same device identifier but different users | Alert keys remain independent |
| Existing alert outside the deduplication window | A new alert is created |
| Email service returns failure | The alert is retained with sent=false and the delivery-failure metric is emitted |

## Boundary

The email case is a mocked local service result. It proves persistence and
metric behavior after the EmailService reports false; it does not prove a
working SMTP server, Mailpit delivery, retry scheduling, or eventual email
delivery.
