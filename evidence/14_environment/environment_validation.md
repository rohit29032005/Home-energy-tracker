# Environment validation

**Execution date:** 2026-10-04 (local environment)

| Item | Observed value/status |
|---|---|
| Operating system | Microsoft Windows, version `10.0.26300.9550` |
| System Java | Oracle JDK 23 (`23+37-2369`) |
| Java used for Maven validation | Temurin OpenJDK `17.0.20.1+1` from a temporary local runtime |
| Maven | Apache Maven `3.9.16` |
| Python | Python `3.13.2` |
| Node.js | `v22.13.1` |
| npm | `10.9.2` (invoked through `npm.cmd`) |
| Docker CLI | Available (`29.7.2` client) |
| Docker engine | Unavailable: the `//./pipe/docker_engine` named pipe was not present |
| k6 | Not found on `PATH` |

The project virtual environment contains FastAPI 0.142.2, pandas 2.3.3, scikit-learn 1.9.1, Kafka Python NG 2.2.3, prometheus-client 0.26.0, and pytest 8.4.2, among other transitive dependencies.

The Docker CLI also warned that `C:\Users\anju2\.docker\config.json` could not be read in this execution context. The Compose configuration still parsed successfully; it does not establish that containers can start.
