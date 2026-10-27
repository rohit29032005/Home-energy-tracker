# REFIT Task 1 Reproduction Notes

## Scope

This evidence directory is a Task 1 source audit only. It does not preprocess
data, convert Watts to kWh, inject anomalies, replay telemetry, train a model,
or produce system-performance claims.

## Source acquisition

The locally available inputs were downloaded from the official Zenodo REFIT
cleaned-data record, which is listed by the University of Strathclyde REFIT
landing page:

- Record: https://zenodo.org/records/5063428
- DOI: https://doi.org/10.5281/zenodo.5063428
- University landing page: https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/

The record exposes only Houses 1, 2, 3, 4, 5 and 11. At audit time, House 5
was unavailable locally after a download timeout. The audit therefore covers
Houses 1, 2, 3, 4 and 11 only. Each locally present file was verified against
the publisher's MD5 value before profiling.

## Reproduce the audit

Run from the repository root:

```powershell
python -m py_compile scripts\refit_task1_audit.py
python -u scripts\refit_task1_audit.py `
  --input-dir data\refit\raw\zenodo_5063428 `
  --output-dir evidence\16_refit_dataset_audit
```

## Outputs

- `source_manifest.json` — source URLs, expected MD5 values, local SHA-256 values, and unresolved evidence limits.
- `dataset_inventory.csv` and `household_audit.csv` — source structure and household quality statistics.
- `candidate_14_day_windows.csv` — every evaluated 14-day candidate window.
- `household_selection.csv` — reproducible selection decision.
- `selection_criteria.md` — fixed quality gate used before selection.
- `data_audit_report.md` — concise human-readable results.

## Do not claim yet

- Results for the full 20-house REFIT archive.
- Raw-versus-cleaned transformation rates.
- Official anomaly-label schema, counts, or aggregate alignment.
- Anomaly-model metrics or end-to-end performance.
