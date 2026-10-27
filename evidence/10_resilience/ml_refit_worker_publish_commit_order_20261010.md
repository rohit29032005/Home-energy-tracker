# REFIT Kafka worker publication and commit-order validation

**Execution date:** 2026-10-10  
**Execution mode:** local Python worker doubles; no Docker or Kafka broker

## Command executed

~~~powershell
.\.venv\Scripts\python.exe -m pytest ml-service\tests\test_refit_kafka_worker.py -q
~~~

## Observed result

**5 tests passed in 1.21 seconds.**

Two tests exercise the input-offset boundary of the isolated experimental
REFIT worker:

| Case | Observed local behavior |
|---|---|
| A valid replay event cannot publish its result, and its subsequent failure record also cannot be acknowledged | The exception reaches the consume loop before consumer commit; the fake consumer recorded zero commits |
| An invalid replay event cannot publish its failure record | The exception reaches the consume loop before consumer commit; the fake consumer recorded zero commits |

The test also retains the normal dedicated result-topic and failure-topic
contracts for valid and invalid events. The worker therefore does not
acknowledge an input record when no outcome record can be durably acknowledged
by its producer interface.

## Important interpretation

If result publication fails but the failure record is successfully published,
the worker intentionally returns and commits the input record: the event is
then observable on the isolated failure topic. The tests above specifically
cover the harder case where that final failure publication also fails.

## Boundary

This is a local double-based ordering proof. It does not establish Kafka
broker delivery, producer idempotence, transactionality, exactly-once
semantics, consumer rebalance behavior, or a live Docker replay.
