# Task 2 — REFIT Data Cleaning and Energy Normalization

## Scope and provenance

This artifact processes only the five checksum-verified, Task-1-selected REFIT cleaned CSV files. It does not modify raw source data, upload data, invoke the project API, replay data, train ML, generate anomalies, send alerts, alter Docker/backend/device-token configuration, or update the research paper.

- Aggregate selected: `Aggregate` (whole-house active power, W).
- Chronology selected: `Unix`; `Time` is retained verbatim. UTC strings in outputs are derived from `Unix`, not a claim that the source `Time` text is timezone-tagged.
- Appliance channels were not summed: they are selected IAM channels and do not form a complete, synchronous household aggregate.
- Houses 1, 2, and 4 are the primary cohort. Houses 3 and 11 remain a distinct solar-affected sensitivity cohort.

## Normalization method

`Aggregate` is active power, not kWh. The output `derived_interval_energy_kwh` is an **estimated** interval value using the left-rectangle/sample-hold rule:

```text
estimated_interval_energy_kwh = interval_start_aggregate_power_w × actual_interval_seconds / 3,600,000
```

Only `0 < actual_interval_seconds <= 16` is integrated. A 7–9 second interval is marked native; 10–16 seconds is short irregular. For a longer gap, no value is interpolated, filled, capped, or synthesized; the cross-gap interval is logged as excluded and the next valid reading becomes a new anchor.

The REFIT source does not establish whether `Aggregate` is an instantaneous reading or an interval average. This is therefore a documented numerical estimate, not a claim of directly metered interval kWh. Valid high values are retained with an IQR diagnostic flag only. Source `Issues` values are preserved and are not anomaly labels.

## Quality and output results

| House | Cohort | Selected source rows | Cleaned interval records | Excluded source rows | Estimated retained energy (kWh) | Solar caveat |
|---:|---|---:|---:|---:|---:|---|
| 1 | primary | 153,762 | 153,578 | 184 | 104.820956111 | none documented |
| 2 | primary | 155,097 | 154,985 | 112 | 170.354373889 | none documented |
| 3 | solar_sensitivity | 153,566 | 153,375 | 191 | 206.346093611 | documented interference |
| 4 | primary | 160,324 | 160,284 | 40 | 111.223081389 | none documented |
| 11 | solar_sensitivity | 172,974 | 172,965 | 9 | 216.88969 | documented interference |

Primary-cohort total: **386.398411389 kWh** across **468,847** retained interval records.

Solar-sensitivity-cohort total: **423.235783611 kWh** across **326,340** retained interval records. This total must not be interpreted as a corrected net-import or consumption value.

## Manual unit-conversion validation

A retained record from House 1, source row 3763831, provides the manual check:

```text
P_start = 177.0 W
Δt = 8 s
E = 177.0 × 8 / 3,600,000 = 0.0003933333333333333 kWh
```

## Generated files

- `cleaned_primary_cohort.csv`: Houses 1, 2, and 4 only.
- `cleaned_solar_sensitivity_cohort.csv`: Houses 3 and 11 only, retaining solar caveats.
- `per_household_quality_report.csv`: schema, source integrity, missing/invalid/negative/zero counts, cohort and output reconciliation.
- `timestamp_interval_report.csv`: full-source and selected-window interval distributions and Time/Unix crosschecks.
- `excluded_records_log.csv`: one explicit reason for every selected source record not represented by a cleaned interval record.
- `data_manifest.json`: input/output hashes and exact processing configuration.

## Reproduction command

```powershell
python experiments/refit_task2_energy_normalization/preprocess_refit.py
python experiments/refit_task2_energy_normalization/verify_artifacts.py
```

## Output SHA-256

- `cleaned_primary_cohort.csv`: `dfdba435f35a1548661309fd67b267548f419edd489cacf25c7566098f189163`
- `cleaned_solar_sensitivity_cohort.csv`: `79fd722bad1abf6fabf2d2e8a1981f75ae14f201d7c04602abcecc7f3ece35e1`
- `excluded_records_log.csv`: `7065849ad71c4c9dc00040bc9182933a4eb037b27eb5da1de874f33b999da128`
- `per_household_quality_report.csv`: `06774437db358dee5e8152a9956a8f590b3cc8f931a7483c39af22ac74020949`
- `timestamp_interval_report.csv`: `6c132e43bcf4e4edf74f8ee0ae5c3f36c525e856ce8f339ed7b6c939f4fbe514`

## Limitations and non-claims

1. The dataset is a publisher-cleaned release; observed zero values can reflect upstream cleaning and are retained rather than reinterpreted as guaranteed physical zero demand.
2. Houses 3 and 11 have documented solar-generation interference. No solar or export correction is applied.
3. The source reading semantic (point sample versus interval average) is not resolved by this task. The kWh field remains an explicit sample-hold estimate.
4. Official appliance-level anomaly annotation schema and aggregate alignment remain unresolved and are not used.
5. This task produces local data artifacts only; it is not an end-to-end, alert, or model experiment.
