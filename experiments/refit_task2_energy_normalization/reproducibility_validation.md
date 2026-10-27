# Task 2 Reproducibility Validation

## Method

The preprocessing command was executed twice with the same five checksum-verified source files, Task 1 selection file, configuration, and script. The second run wrote to a separate temporary output directory. Both artifact sets then passed the read-only verifier, and their SHA-256 values were compared file-by-file.

```powershell
python experiments/refit_task2_energy_normalization/preprocess_refit.py
python experiments/refit_task2_energy_normalization/preprocess_refit.py `
  --output-dir experiments/refit_task2_energy_normalization/artifacts_reproducibility_check
python experiments/refit_task2_energy_normalization/verify_artifacts.py
python experiments/refit_task2_energy_normalization/verify_artifacts.py `
  --artifact-dir experiments/refit_task2_energy_normalization/artifacts_reproducibility_check
```

## Result

Both runs passed artifact verification. The two output sets were byte-identical for every generated file.

| Artifact | SHA-256 | Byte-identical across runs |
|---|---|---|
| `cleaned_primary_cohort.csv` | `dfdba435f35a1548661309fd67b267548f419edd489cacf25c7566098f189163` | Yes |
| `cleaned_solar_sensitivity_cohort.csv` | `79fd722bad1abf6fabf2d2e8a1981f75ae14f201d7c04602abcecc7f3ece35e1` | Yes |
| `data_manifest.json` | `9ca18e39ae0c5f234086c5d10840ca63e5a057a5cbfad1fa64a9e487173a8a42` | Yes |
| `excluded_records_log.csv` | `7065849ad71c4c9dc00040bc9182933a4eb037b27eb5da1de874f33b999da128` | Yes |
| `per_household_quality_report.csv` | `06774437db358dee5e8152a9956a8f590b3cc8f931a7483c39af22ac74020949` | Yes |
| `preprocessing_summary.md` | `f57320312ed4e5ac6e1192b30eb653b7084324da019347c1014adc37004435ab` | Yes |
| `timestamp_interval_report.csv` | `6c132e43bcf4e4edf74f8ee0ae5c3f36c525e856ce8f339ed7b6c939f4fbe514` | Yes |

The temporary duplicate output directory was removed after this comparison. The primary artifact directory remains the authoritative Task 2 result.
