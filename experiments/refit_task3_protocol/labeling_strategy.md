# Task 3 — Anomaly-Label Strategy

## Decision at protocol freeze

The current Task 2 artifacts do **not** support a genuine aggregate-household anomaly-detection accuracy claim. The scientifically defensible immediate experiment is therefore a **historical-data replay and system-integration study without ML accuracy metrics**.

If a later ML study is approved, a controlled-perturbation benchmark on the frozen real REFIT aggregate baseline is the practical option, provided it is generated only after the chronological split and is reported strictly as detection of controlled perturbations. It must never be described as genuine REFIT anomaly accuracy.

## 1. Official annotation evidence actually available

The University of Strathclyde publishes the companion dataset [Annotated load anomalies from the REFIT Dataset](https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/) (DOI: `10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33`). The official landing-page metadata states that it contains real **appliance-level** anomalies for Houses 1, 10, 16, 18, and 20; it lists `README_ICASSP.txt` and `REFIT_anomalies.csv` under CC BY 4.0.

The current Task 2 selection is H1, H2, H3, H4, and H11. Thus, only H1 overlaps the official annotated-house set. H2, H3, H4, and H11 do not have official annotation coverage according to the official dataset description.

Local audit results:

- `data/refit/raw/zenodo_5063428/` contains the five checksum-verified `CLEAN_House*.csv` files, but neither `REFIT_anomalies.csv` nor `README_ICASSP.txt`.
- The published direct file endpoints returned HTTP 403 in this environment on 2026-10-12. This is an environment access limitation, not evidence that the official files do not exist.
- Consequently, the official label schema, exact timestamps/timezone, appliance identifier mapping, label count, and overlap with the selected H1 14-day window are unverified.

## 2. What Task 2 fields are not labels

The following Task 2 fields are not accepted as anomaly ground truth:

| Field or signal | Why it is not an anomaly label |
|---|---|
| `source_issues_raw` / `source_issue_marked` | Preserved REFIT source-quality context only. |
| IQR diagnostic flag | A descriptive outlier diagnostic; valid high/low observations were retained. |
| cadence/interval flags | Sampling-quality information, not consumption anomaly truth. |
| solar-interference marker | A documented measurement caveat, not an anomalous household event. |
| appliance-level official annotation | Cannot automatically become a binary aggregate-household label because other loads can mask or dominate the aggregate. |

## 3. Option comparison

| Option | What could be claimed | Preconditions | Limitation |
|---|---|---|---|
| A. Genuine official-label evaluation | An appliance-level H1 result, if the official annotations can be matched correctly. | Obtain official files through normal access; audit schema, timestamp convention, H1 selected-window overlap, appliance-to-channel mapping, and evaluation unit. | Only H1 overlaps; no automatic aggregate label follows from an appliance annotation. |
| B. Controlled synthetic perturbations on recorded baseline | Detection of explicitly injected, documented perturbations. | Freeze chronological split first; generate only after approval; retain originals, seed, episode log, and independent verification. | Measures controlled-perturbation detection, not real appliance-fault or real-world anomaly accuracy. |
| C. System-integration experiment without ML accuracy | Delivery/accounting/persistence/alert-pipeline behavior for historical replayed data. | Verified data adapter, device mapping, and observability plan. | Cannot report classification metrics. |

## 4. Recommendation and permitted terminology

**Recommended immediate route: Option C.** It is directly supported by the verified Task 2 records and requires no unverified label conversion.

**Conditional later route: Option B.** If the research objective requires an ML component before official-label access is resolved, use a pre-registered controlled-perturbation protocol after the frozen split. Report metrics only as, for example, “controlled-perturbation detection precision/recall under the declared scenarios.”

**Optional later route: Option A.** Use only after a separate provenance audit proves the official schema and alignment. Any aggregate proxy mapping must be labelled a weak proxy, not direct ground truth.

Never use these phrases for the current dataset without the missing evidence:

```text
real aggregate anomaly labels
REFIT Issues ground truth
five-house official-label evaluation
real-world anomaly accuracy
```

## 5. Future ML evaluation boundary

No standard supervised metric (accuracy, precision, recall, F1, ROC-AUC, PR-AUC) is scientifically interpretable for the current aggregate stream without an approved target. If controlled labels are later approved, select decision thresholds using validation only, evaluate once on the untouched test partition, and report both event-level and episode-level definitions. If genuine official labels are later used, their appliance-level target must remain distinct from aggregate-household inference.

The chronological split and anti-leakage constraints are specified in `cohort_and_split_plan.md`.

## 6. Existing repository material outside Task 3

The repository contains `evidence/17_refit_anomaly_labelling/`, described by its own files as an earlier controlled-perturbation exercise. It was not executed, changed, or adopted in Task 3. Its strategy describes a different frozen-source representation and explicitly forbids genuine REFIT anomaly claims. It must not be assumed compatible with the present authoritative Task 2 left-rectangle output without a separate provenance-compatibility audit.

## 7. Evidence references

- [Official annotation dataset and DOI](https://pureportal.strath.ac.uk/en/datasets/annotated-load-anomalies-from-the-refit-dataset/)
- [Rashid et al., ICASSP 2019, appliance-level anomaly detection](https://pureportal.strath.ac.uk/en/publications/evaluation-of-non-intrusive-load-monitoring-algorithms-for-applia/)
- `experiments/refit_task2_energy_normalization/artifacts/data_manifest.json`
- `experiments/refit_task2_energy_normalization/preprocessing_config.yaml`
- `evidence/17_refit_anomaly_labelling/strategy.md` (context only; not adopted)
