# Task 4H Stage R0 — Kafka Capacity Assessment

## Scope and decision boundary

This assessment is read-only. No Kafka start, restart, configuration change,
Compose change, topic operation, endpoint request, log export, or volume action
was performed. It documents whether current evidence can justify a future
broker-only recovery configuration.

**Capacity decision: NO-GO.** The evidence does not justify a safe numeric
Kafka memory/JVM configuration or a broker start.

## Finding labels

- **VERIFIED** — directly supported by read-only Docker/source evidence.
- **INFERRED** — a possible explanation, not an established root cause.
- **UNRESOLVED** — evidence is insufficient to justify an action.
- **RECOMMENDED** — a future approval-gated safeguard; it was not executed.

## Evidence reviewed

- Task 4F Docker runtime and startup findings.
- Task 4G Kafka OOM diagnosis and current-state report.
- Non-secret Docker inspect and engine metadata reviewed during Task 4I.
- Redacted category scan of retained Kafka log tail; raw log lines were neither
  retained nor reported.
- Static Kafka service definition in docker-compose.yml lines 21-53.

## Verified evidence

| Classification | Finding | Supporting evidence | Significance |
|---|---|---|---|
| **VERIFIED** | Existing Kafka is exited with exit code 137 and OOMKilled=true. | Task 4G kafka_oom_diagnosis.md section 1; current non-secret Docker inspect. | Docker recorded a broker-specific out-of-memory termination. |
| **VERIFIED** | Kafka started on 2026-10-11 and ended about 7 hours 16 minutes later, before the later common exit-255 container pattern. | Task 4G kafka_oom_diagnosis.md section 1; Task 4F startup findings. | Do not attribute Kafka OOM to the later shared Docker interruption. |
| **VERIFIED** | Restart policy is no; restart count is zero. | Current non-secret Docker inspect; Task 4G section 1. | Kafka did not autonomously retry after its failure. |
| **VERIFIED** | Container-level memory, memory reservation, memory swap, CPU, and PID limits are not declared. | Current non-secret Docker inspect. | No existing per-container resource envelope is documented. |
| **VERIFIED** | Compose declares no Kafka resource limit, heap/JVM setting, restart policy, or health check. | docker-compose.yml lines 21-53. | Compose provides no verified capacity or readiness control for Kafka. |
| **VERIFIED** | Docker Engine reports 8 CPUs and about 3.70 GiB available to the engine. | Current read-only Docker Engine metadata; Task 4G section 1. | This is a current capacity snapshot, not a failure-time memory trace. |
| **VERIFIED** | Kafka uses a persistent named data volume and auxiliary internal mounts. | Task 4F network_volume_port_audit.md section 2; current non-secret inspect. | Persistent broker state must be preserved before any action. |
| **VERIFIED** | Retained log-tail category scan found no explicit JVM heap OOM, generic OOM, disk/lock, bind conflict, or graceful-shutdown signature. | Task 4G kafka_oom_diagnosis.md section 3; Task 4I redacted scan. | The retained evidence does not establish an application-level root cause. |
| **VERIFIED** | Historical Docker event context for the original failure is unavailable. | Task 4G kafka_oom_diagnosis.md section 3. | Failure-time causality cannot be reconstructed from event history. |
| **VERIFIED** | Kafka UI running while the broker is stopped is not broker health evidence. | Task 4F startup_and_health_findings.md section 1. | Kafka UI must not be used as a recovery-readiness signal. |

## Possible explanations

| Classification | Explanation | Assessment |
|---|---|---|
| **INFERRED** | Docker Desktop/host/VM memory pressure or concurrent workload contributed. | Plausible because engine memory is limited and the broker had no container cap; not proven at failure time. |
| **INFERRED** | Kafka JVM heap, direct memory, native memory, or workload burst contributed. | Plausible; no retained JVM diagnostic proves it. |
| **INFERRED** | Persistent-log recovery or storage conditions contributed. | Possible; retained log scan does not prove disk/lock failure. |
| **INFERRED** | The mutable apache/kafka:latest image tag reduces reproducibility. | It complicates incident attribution but is not evidence that image choice caused the OOM. |

## Unresolved evidence

1. Exact source of the OOM and peak memory use at failure time.
2. Docker Desktop allocation, WSL/host memory pressure, and competing workload
   at the original failure time.
3. Effective Kafka JVM heap/direct/native-memory settings and actual runtime
   footprint.
4. Current persistent log/metadata recovery condition, topics, consumer groups,
   offsets, and retained backlog.
5. A safe numeric memory/JVM configuration.
6. Broker readiness criteria beyond Compose service_started.

## Capacity conclusion

**UNRESOLVED:** Current evidence proves an OOM termination but does not prove a
safe resource envelope. No numeric Docker memory limit, JVM heap setting, image
change, or Compose modification may be inferred from this assessment.

A numeric configuration would require evidence of the approved Docker
Desktop/host capacity, concurrent workload budget, intended broker footprint,
headroom, and post-start observation criteria. None was established here.

## Recommended approval-gated prerequisites

1. Preserve the existing Kafka data volume and auxiliary mounts. Do not prune,
   remove, reformat, recreate, or initialize them.
2. Complete the backup/rollback gate before any broker action.
3. Under separate approval, collect non-secret capacity evidence: Docker
   Desktop allocation, host/engine headroom, current competing workload, and a
   documented broker/infrastructure reserve.
4. Decide how image identity/version will be controlled for reproducibility;
   do not change the Compose file during Stage R0.
5. Define broker readiness evidence stronger than service_started and define
   OOM/error abort criteria.
6. Define a no-producer/no-consumer gate and a plan for retained topics,
   consumer offsets, alert side effects, and replay risks.
7. Obtain explicit authorization for an exact existing-container,
   broker-only observation stage. Do not use a project-wide Compose startup.

## Stage R0 conclusion

**NO-GO for Kafka recovery execution.** The OOM termination is verified, while
its root cause, safe resource configuration, persistent-log recovery condition,
and downstream event implications remain unresolved. REFIT Task 4C remains
separate and is not part of a Kafka recovery decision.

