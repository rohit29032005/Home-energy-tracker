# Task 4 — Generated Controlled-Perturbation Evidence

## Verified result

`scripts/refit_task4_verify_anomalies.py` returned **PASS** for the final artifact in `data/refit/labeled-verified/`.

| Item | Verified value |
|---|---:|
| Frozen Task 2 source events copied | 795,187 |
| Synthetic positive-label events | 3,914 |
| Controlled perturbation episodes | 40 |
| Sustained-high episodes | 32 |
| Sustained-low episodes | 8 |
| Stuck-signal episodes under seed `20261009` | 0 |
| Original Task 2 input SHA-256 | `1675be53ffe9ab5b89bc34316fc0459c8bd59bc03700288e8001230140e24c62` |

Positive labels mean **controlled synthetic perturbation only**. They are not genuine REFIT appliance anomalies.

## Per-household held-out test composition

| Household | Cohort | Test records | Controlled positive records | Realised positive rate | Episodes |
|---:|---|---:|---:|---:|---:|
| H1 | Primary | 23,037 | 735 | 3.191% | 6 |
| H2 | Primary | 23,248 | 762 | 3.278% | 8 |
| H3 | Solar-interference sensitivity | 23,007 | 782 | 3.399% | 9 |
| H4 | Primary | 24,043 | 771 | 3.207% | 8 |
| H11 | Solar-interference sensitivity | 25,945 | 864 | 3.330% | 9 |

The configured target was 3% of each household test partition. The realised rate is slightly higher because the generator injects complete 5–15 minute episodes rather than partial rows.

## Verification coverage

The independent verifier confirmed all of the following:

- the frozen Task 2 input hash and generated-artifact hashes match the manifest;
- all Task 2 source columns are identical in the derived CSV;
- each household's source-time split exactly matches the manifest's chronological 70% train / 15% validation / 15% test policy;
- train and validation records are unmodified and positive labels occur only in test;
- every positive row is non-negative, altered numerically, and `is_replayable=true`;
- no episode falls within a source-quality or material-gap guard window;
- each log event's household, type, duration, continuity, non-overlap buffer, row count, original/modified kWh sums, and start/end timestamps reconcile with the row-level dataset.

## Reproduction commands

```powershell
python -m unittest scripts\test_refit_task4_generate_anomalies.py -v
python -u scripts\refit_task4_verify_anomalies.py
```

The expected final verifier result is:

```text
PASS: verified 795,187 derived events and 40 episodes
```

## Research-report wording constraint

Safe wording:

> A reproducible controlled-perturbation benchmark was generated from the recorded REFIT aggregate-load baseline. A chronological train/validation/test separation was imposed before perturbation injection, and the test-only perturbations were independently reconciled with their generation log.

Do **not** replace “controlled-perturbation benchmark” with “real anomaly dataset,” “ground-truth appliance faults,” or “real-world anomaly-detection accuracy.”
