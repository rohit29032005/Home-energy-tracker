# Experiment 1: Offline supervised-baseline validation

## Scope and safety boundary

This experiment validated the legacy supervised smart-meter classifier only. It used a copied local CSV and created all outputs under `experiments/publication_final/evidence/ml_validation/`. No Docker command, container operation, HTTP request, application endpoint, Kafka action, persistent volume, secret, repository source edit, installed model edit, or historical-evidence edit occurred.

The copied input has SHA-256 `d48df940fd29444fb9222fc0b59cfde632e147ccd1d49dc7bed9d5f9dc88f588`, which matches both the source CSV and the historical dataset provenance record. The exact commands and execution boundary are recorded in `experiment_manifest.json`.

## Existing ML assets found

| Asset group | Evidence classification | Finding |
| --- | --- | --- |
| Legacy supervised data and trainer | Historical source inspected and newly reproduced | `smart_meter_data.csv` and `ml-service/training/train.py` support a deterministic Random Forest versus logistic-regression experiment. |
| Installed legacy model | Historical source inspected only | The installed Joblib was hashed but not deserialized. Its metadata matches the historical training metadata exactly. |
| Historical legacy evaluation | Historical evidence | Existing evidence stores the chronological 70/15/15 split, configuration, feature list, metrics, and plots. |
| REFIT controlled pipeline | Static source inspected only | `train_refit_controlled.py` describes a separate per-household Isolation Forest benchmark using controlled synthetic perturbations. |
| REFIT controlled artefacts | Unavailable to this experiment | Labelled input and controlled model/evidence contents were access-restricted. They were not read, bypassed, substituted, or reproduced. |
| ML tests | Static inventory only | Endpoint-invoking tests and unrelated REFIT tests were not executed under the experiment boundary. |

## Newly generated data-quality and split checks

The copied supervised CSV contains 5,000 rows and the seven expected fields: `Timestamp`, five numeric predictors, and `Anomaly_Label`. All timestamps and numeric predictors parsed successfully. There were no negative `Electricity_Consumed` values and no complete duplicate records. Labels consist of 4,750 `Normal` records (95.0%) and 250 `Abnormal` records (5.0%).

The trainer's stable chronological split was recomputed as follows:

| Split | Rows | Normal | Abnormal | Period |
| --- | ---: | ---: | ---: | --- |
| Train | 3,500 | 3,335 | 165 | 2024-01-01 00:00:00 to 2024-03-13 21:30:00 |
| Validation | 750 | 705 | 45 | 2024-03-13 22:00:00 to 2024-03-29 12:30:00 |
| Test | 750 | 710 | 40 | 2024-03-29 13:00:00 to 2024-04-14 03:30:00 |

All splits contain both classes. No timestamp, complete raw-record fingerprint, or engineered-feature-row fingerprint overlapped across train/validation, train/test, or validation/test. The feature contract excludes the label and encoded target. The derived `ConsumptionDeviation` exactly equals `Electricity_Consumed - Avg_Past_Consumption` for every copied record.

These checks are safeguards, not proof that all leakage is absent. The CSV does not document how `Avg_Past_Consumption` was constructed, so causal availability of that feature remains unresolved. The repository also does not establish the external source, licence, or label-generation process for `smart_meter_data.csv`; therefore the resulting performance is not an independently validated real-world anomaly-detection claim.

## Newly generated reproduction result

The current trainer was run offline against the copied input with new model and evidence output paths. It completed successfully. The reproduction used Python 3.13.2, pandas 2.3.3, NumPy 2.5.3, scikit-learn 1.9.1, Joblib 1.6.0, and Matplotlib 3.11.2. The bundled document-analysis Python runtime lacked scikit-learn, so the pre-existing project virtual environment was used without installing or changing packages.

| Model | Validation F1 | Test precision | Test recall | Test F1 | Test ROC-AUC | Test PR-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Random Forest | 0.914894 | 0.880952 | 0.925000 | 0.902439 | 0.997430 | 0.948532 |
| Logistic regression | 0.113208 | 0.053333 | 1.000000 | 0.101266 | 0.422852 | 0.059710 |

The random-forest decision threshold was 0.31, selected by validation F1. The test interval was not used to select the threshold. The newly generated comparison CSV is byte-identical to the historical model-comparison CSV. All reported metric differences are exactly zero. The reproduced Random Forest Joblib SHA-256 is also byte-identical to the installed legacy model. Reproduced metadata differs only in the timestamped `model_version` value; all other fields match.

This establishes deterministic reproduction of the repository's legacy supervised baseline on the available copied input and current pinned local environment. It does not establish external validity, real-household generalization, or validity of undocumented source labels.

## REFIT boundary and blocker

The REFIT controlled trainer is intentionally separate from the legacy baseline. Static source inspection confirms that it treats labels as controlled synthetic perturbations and prohibits label, split, quality, source, and original-signal fields from entering its feature contract. However, the required labelled REFIT input and controlled model/evidence directories were inaccessible to this task process. No REFIT training, evaluation, replay, anomaly generation, endpoint call, or substitution was attempted. A future REFIT result must remain labelled as controlled-perturbation evidence unless official aligned anomaly labels are independently verified.

## Reproducibility artefacts

- Machine-readable input, schema, split/leakage, environment, and historical-comparison records: `analysis/`.
- New Random Forest and logistic-regression model outputs, metrics, reports, and figures: `reproduction/`.
- Command manifest and raw console output: `experiment_manifest.json` and `raw_outputs/`.
- Asset and test inventory: `artifact_inventory.json` and `test_inventory.csv`.

## Conclusion

Experiment 1 is complete for the legacy supervised baseline. The available CSV and code reproduce the historical Random Forest and logistic-regression results exactly, while two scientific limitations remain unresolved: the causal provenance of `Avg_Past_Consumption` and the origin and label-generation process of the source CSV. REFIT controlled-model validation is blocked by access restrictions and was not represented as a completed result.
