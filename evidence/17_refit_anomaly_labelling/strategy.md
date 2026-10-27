# REFIT Task 4 — Label Availability Decision and Controlled-Perturbation Protocol

## Decision

This task uses **Case B: controlled synthetic perturbations on a real recorded baseline**. It does not use the REFIT `Issues` field, IQR flags, a solar-interference marker, or an unverified legacy CSV label as anomaly ground truth.

The decision is driven by a compatibility audit, not by an assumption that no related labels exist. The University of Strathclyde publishes [Annotated load anomalies from the REFIT Dataset](https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/) (DOI: `10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33`). Its landing page identifies an appliance-level resource for Houses 1, 10, 16, 18, and 20. The selected Task 1/2 aggregate cohort is Houses 1, 2, 3, 4, and 11.

| Audit item | Verified state | Consequence |
|---|---|---|
| Household overlap | Only H1 overlaps (`{H1,H2,H3,H4,H11}` ∩ `{H1,H10,H16,H18,H20}` = `{H1}`) | A five-house supervised evaluation cannot be claimed. |
| Label level | Official resource is appliance-level; Task 2 is aggregate-only estimated interval energy | An appliance label cannot automatically become an aggregate-event binary label. |
| Official CSV/README schema and timestamps | **Not locally audited.** The official browser/download route required Cloudflare verification and non-browser retrieval returned 403. | No label counts, class distribution, exact timestamps, source-column mapping, or selected-window overlap is reported. |
| H1 selected window compatibility | **Unknown** until official label files are manually obtained and audited | No H1 label-based result is reported. |

The official source must be manually downloaded through the normal browser flow and placed in a separate provenance-controlled directory before an H1-only mapping is considered. No protection was bypassed and no mirror was used.

## Semantic boundary

The output label means only:

```text
0 = unmodified recorded REFIT aggregate-load baseline event
1 = controlled synthetic perturbation applied after Task 2 preprocessing
```

It **does not** mean a verified appliance failure, meter fault, user behaviour anomaly, or real REFIT anomaly. Thus any later detection measurement must be named a **controlled-perturbation detection result**, never real-world anomaly accuracy.

## Frozen baseline and unit

Input is `data/refit/processed/cleaned_dataset.csv`, whose `estimated_interval_energy_kwh` is Task 2's trapezoidal numerical estimate from the REFIT `Aggregate` active-power channel using the actual Unix timestamp delta. It is not directly metered interval energy. The Task 4 generator reads this frozen file only and copies every source column unchanged into the derived dataset.

The generated feature `synthetic_replay_energy_kwh` is the only altered numeric signal. `original_estimated_interval_energy_kwh` and the original source field are retained side by side on every row.

## Leakage-resistant chronological protocol

For each household separately, source-time order is split before any perturbation selection:

| Partition | Fraction | Use in the current protocol | Synthetic perturbations |
|---|---:|---|---|
| Train | 70% earliest events | Future model fitting / baseline learning only | No |
| Validation | next 15% | Future threshold selection / false-alert control only | No |
| Test | final 15% | Held-out controlled-perturbation evaluation only | Yes |

No random row split is used. Positive labels are limited to continuous test episodes requested at 5–15 minutes; the final observed endpoint may extend an episode by at most 16 seconds so that an 8-second sampled sequence actually reaches the requested duration. The generator excludes source-quality-marked records and material-gap neighbourhoods, prevents overlapping episodes, and records the fixed seed and all episode parameters.

## Scenarios and physical interpretation

Magnitude parameters are household-specific and derived only from each household's chronological training partition. They are stored in `anomaly_generation_config.yaml` and duplicated in each injection-log record.

| Scenario | Transformation | Interpretation boundary |
|---|---|---|
| `sustained_high` | Multiply a continuous eligible interval-energy episode by a configured factor while remaining below the household training 99.5th-percentile reference. | Controlled elevated-load signal, not proof of an actual appliance fault. |
| `sustained_low` | Multiply a continuous eligible higher-baseline episode by a factor in `[0.25, 0.70]`. | Controlled suppressed-load signal, not proof of a meter outage. |
| `stuck_signal` | Available generator mode: hold a varying positive episode at its first value. | Simulates a frozen signal only if selected; it was not present in the current seed's accepted episodes. |

The generator keeps energy non-negative and rejects a no-op transformation. Its default target is 3% of each household's held-out test rows. Because complete episodes—not individual rows—are injected, the realised rate can slightly exceed the target; the actual rate is reported rather than rounded to a claimed target.

## Cohort reporting boundary

- **Primary cohort:** H1, H2, H4.
- **Sensitivity cohort:** H3, H11. The REFIT descriptor documents solar-generation interference for these homes; they must be reported separately and must not be silently pooled into household-consumption findings.

## Generated evidence and verification

The generated, ignored local data artifacts are under `data/refit/labeled-verified/`:

- `anomaly_dataset.csv`
- `anomaly_injection_log.csv`
- `anomaly_generation_config.yaml`
- `anomaly_dataset_quality_report.csv`
- `anomaly_generation_summary.md`
- `anomaly_generation_manifest.json`

The independent verifier report is `anomaly_dataset_verification.json`. It verifies the frozen input hash, all copied source fields, row alignment, chronological ordering, unmodified train/validation records, non-negative modified energy, source-quality exclusion, and row-level/log-level episode reconciliation.

## Not permitted claims

- “The model was trained/evaluated on real REFIT anomaly labels.”
- “REFIT `Issues=1` is an anomaly.”
- “An IQR-high aggregate value is an anomaly.”
- “The full five-house cohort has official appliance-level labels.”
- “H1 official labels overlap the selected 14-day window.”
- “A synthetic-label metric is a real-world precision, recall, F1-score, or accuracy result.”

## Sources

- University of Strathclyde, [REFIT Electrical Load Measurements — Cleaned](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/).
- H. Rashid *et al.*, [“Evaluation of Non-Intrusive Load Monitoring Algorithms for Appliance-Level Anomaly Detection,” IEEE ICASSP 2019](https://strathprints.strath.ac.uk/66988/1/Rashid_etal_IEEE_ICASSP_2019_Evaluation_of_non_intrusive_load_monitoring_algorithms_for_appliance.pdf), DOI: `10.1109/ICASSP.2019.8683792`.
- University of Strathclyde, [Annotated load anomalies from the REFIT Dataset](https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/), DOI: `10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33`.
