# Frontend production build

**Execution date:** 2026-10-04 (local environment)

Command executed from `frontend`:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run build
```

Result: **successful**. Vite 8.2.2 transformed 2,431 modules and completed in 849 ms.

Generated asset sizes reported by Vite:

| Asset | Size | Gzip |
|---|---:|---:|
| CSS bundle | 36.08 kB | 7.16 kB |
| JavaScript bundle | 652.62 kB | 191.94 kB |

Vite emitted a non-blocking warning that a JavaScript chunk exceeds 500 kB after minification. This is a future code-splitting optimisation item, not a build failure.
