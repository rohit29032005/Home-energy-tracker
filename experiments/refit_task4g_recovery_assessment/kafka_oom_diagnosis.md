# Task 4G: Kafka OOM Diagnosis

## Scope

This is a read-only diagnosis of the existing `home-energy-tracker` Kafka broker. No broker was started, restarted, removed, recreated, configured, or connected to by this task. No environment value, credential, token, or raw log line was retained.

## 1. Verified facts

| Item | Observation | Evidence |
|---|---|---|
| Container identity | Existing container name `kafka`, Compose project `home-energy-tracker`, service `kafka`. | Docker labels and current inventory. |
| Image | `apache/kafka:latest`. | Current inspect and `docker-compose.yml:21-53`. |
| Failure state | `exited`, exit code `137`, `OOMKilled=true`, Docker state error empty. | Current Docker inspect metadata. |
| Failure timing | Started `2026-10-11T14:25:21.630Z`; finished `2026-10-11T21:41:52.327Z` (about 7 hours 16 minutes later). | Current Docker inspect metadata. |
| Relation to Docker restart pattern | Kafka's OOM predates the 2026-10-14 shared exit-`255` state by several days. | Current state timing compared with Task 4F evidence. |
| Restart behavior | `restart=no`; restart count `0`. | Current Docker inspect metadata. |
| Container resource limits | Memory, memory swap, and CPU limits are unset in Docker HostConfig. | Current Docker inspect metadata. |
| Engine capacity | Docker Desktop reports 8 CPUs and approximately 3.70 GiB memory available to the engine. | Read-only Docker Engine info. |
| Compose resource controls | No explicit Kafka memory/CPU resource or JVM heap setting was found in the inspected Kafka Compose block. | `docker-compose.yml:21-53`. |
| Broker health check | No Docker Compose Kafka health check is declared. | `docker-compose.yml:21-53`. |
| Persistent storage | Existing named Kafka data volume plus anonymous configuration/secrets mounts are attached. | Docker mount metadata; identifiers intentionally not reproduced. |

## 2. What `OOMKilled=true` proves

Docker recorded a kernel-level out-of-memory termination for the Kafka container. It establishes that memory pressure killed the broker process. It does **not** by itself prove whether the pressure originated from:

- Docker Desktop's global memory allocation;
- concurrent container or host workload;
- Kafka/JVM runtime footprint;
- a workload burst; or
- another environmental condition.

No source change or restart policy can be selected responsibly until this distinction is reviewed.

## 3. Redacted diagnostic evidence

| Evidence | Result | Interpretation |
|---|---|---|
| Historical Docker events for the Kafka failure window | No retained event was available. | Absence is inconclusive; event retention or Engine restart may have removed it. |
| Redacted category scan of retained Kafka log tail | No clear JVM heap-OOM, generic OOM, disk-full, filesystem-lock, bind-conflict, or graceful-shutdown signature was found. | Retained logs do not establish a causal application failure mode. |
| KRaft/metadata/error-category matches | Category matches existed but overlapped and were not correlated to raw failure context. | They cannot be treated as root-cause evidence. |
| Kafka UI runtime output | UI cannot resolve/reach `kafka:9092` while the broker is stopped. | Confirms current broker absence, not historical OOM cause. |

## 4. Hypotheses and explicitly unresolved questions

| Hypothesis or question | Status |
|---|---|
| Docker Desktop memory allocation and competing workload contributed to the OOM. | Plausible capacity-risk hypothesis; not proven. |
| Kafka JVM consumed an unsafe amount of memory. | Possible; no retained JVM heap error proves it. |
| Kafka data/log recovery or storage condition contributed. | Possible; no disk/lock signature was proven. |
| A configuration/image issue contributed. | Possible; the service uses mutable `latest`, but no causal evidence was found. |
| The broker can safely recover from its existing persistent log volume. | Unknown until separately authorized broker-only recovery evidence is collected. |

## 5. Prerequisites before any Kafka recovery action

1. Approve a broker-only recovery assessment; do not start the whole Compose project.
2. Preserve `home-energy-tracker_kafka-data` and the currently attached anonymous mounts. Do not prune, remove, reformat, or recreate them.
3. Review Docker Desktop memory allocation, current competing workload, and an explicit resource budget using approved non-secret evidence.
4. Decide whether existing Kafka image versioning must be pinned before recovery. `apache/kafka:latest` is mutable and reduces reproducibility.
5. Define broker-readiness evidence beyond Compose `service_started`.
6. Define how to handle existing topics, consumer groups, offsets, and any queued records without inadvertently replaying downstream processing.
7. Approve the exact existing-container start/observation action and rollback boundary separately.

## Current decision

**NO-GO for Kafka recovery execution.** The OOM termination is verified; its root cause and safe persistent-log recovery conditions are not yet proven.
