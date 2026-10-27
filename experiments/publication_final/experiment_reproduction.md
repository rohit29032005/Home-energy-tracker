# Reproduction guide

## Scope and safety boundary

This guide reproduces only the offline evidence generated for the final manuscript. It must be run from `C:\Users\anju2\Desktop\Home-Energy-Tracker` with the pre-existing project virtual environment. It does not require Docker, an HTTP endpoint, Kafka, MySQL, InfluxDB, Keycloak, credentials, or application configuration changes. Do not run the repository's live replay, load-test, alert, database, or Docker scripts under this guide.

The copied input CSV used by the experiments is `experiments\publication_final\evidence\ml_validation\input\smart_meter_data.csv`. Its SHA-256 is `d48df940fd29444fb9222fc0b59cfde632e147ccd1d49dc7bed9d5f9dc88f588`.

## Environment recorded for the reproduced baseline

- Operating system: Windows 11 10.0.26300-SP0
- Python: 3.13.2
- pandas: 2.3.3; NumPy: 2.5.3; scikit-learn: 1.9.1; Joblib: 1.6.0; Matplotlib: 3.11.2
- Reproduction input: copied CSV named above
- Split: stable chronological sort followed by 70% train, 15% validation, and 15% held-out test
- Threshold selection: maximum validation F1 only; the test interval is not used for threshold selection

## 1. Verify the copied input and split safeguards

```powershell
& .\.venv\Scripts\python.exe `
  experiments\publication_final\evidence\ml_validation\analysis\validate_supervised_baseline.py `
  --dataset experiments\publication_final\evidence\ml_validation\input\smart_meter_data.csv `
  --output experiments\publication_final\evidence\ml_validation\analysis `
  --historical-evidence-root evidence
```

Expected outputs include `schema_validation.json`, `split_leakage_checks.json`, and `validation_check_status.csv`. Treat the `Avg_Past_Consumption` causal-provenance and label-provenance statuses as unresolved unless new documentary evidence is supplied.

## 2. Reproduce the supervised baseline into a disposable output directory

Use a new output directory if the prior evidence must be preserved:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MPLCONFIGDIR = Join-Path (Resolve-Path -LiteralPath 'experiments\publication_final\evidence\ml_validation\reproduction') 'matplotlib-cache'
& .\.venv\Scripts\python.exe ml-service\training\train.py `
  --dataset experiments\publication_final\evidence\ml_validation\input\smart_meter_data.csv `
  --model-dir experiments\publication_final\evidence\ml_validation\reproduction\model `
  --evidence-root experiments\publication_final\evidence\ml_validation\reproduction\evidence
```

Expected result: the random-forest model should report a validation F1 of 0.914894 and held-out test F1 of 0.902439 for the supplied copied CSV. Compare the generated `model_comparison.csv` with the historical one by running the first command again with `--reproduction-evidence-root experiments\publication_final\evidence\ml_validation\reproduction\evidence`.

## 3. Recalculate held-out test uncertainty without retraining

```powershell
& .\.venv\Scripts\python.exe `
  experiments\publication_final\evidence\ml_bootstrap_ci\bootstrap_test_metrics.py `
  --dataset experiments\publication_final\evidence\ml_validation\input\smart_meter_data.csv `
  --model experiments\publication_final\evidence\ml_validation\reproduction\model\anomaly_model.joblib `
  --metadata experiments\publication_final\evidence\ml_validation\reproduction\model\model_metadata.json `
  --output experiments\publication_final\evidence\ml_bootstrap_ci\results_300 `
  --iterations 300 --seed 42
```

Expected result: `bootstrap_summary.json` contains the fixed-model confusion matrix `[[705, 5], [3, 37]]` (rows actual; columns predicted) and a test F1 interval of 0.838300 to 0.957444. These intervals are conditional on the supplied held-out CSV and fixed model.

## 4. Re-run the in-process input-contract and Wokwi-scale checks

```powershell
& .\.venv\Scripts\python.exe `
  experiments\publication_final\evidence\ml_robustness\validate_ml_input_robustness.py `
  --model-dir experiments\publication_final\evidence\ml_validation\reproduction\model `
  --output experiments\publication_final\evidence\ml_robustness\results
```

Expected result: five input-validation cases pass. Five of the six documented Wokwi energy boundaries are outside the training `Electricity_Consumed` range of 0 to 1. The predictions are controlled synthetic inputs and have no ground-truth labels; do not present them as classification accuracy.

## 5. Re-run the offline, single-worker inference microbenchmark

```powershell
& .\.venv\Scripts\python.exe `
  experiments\publication_final\evidence\ml_inference_benchmark\benchmark_ml_inference.py `
  --dataset experiments\publication_final\evidence\ml_validation\input\smart_meter_data.csv `
  --model experiments\publication_final\evidence\ml_validation\reproduction\model\anomaly_model.joblib `
  --output experiments\publication_final\evidence\ml_inference_benchmark\results_single_worker_repeated `
  --sample-size 100 --repetitions 3 --single-worker
```

Expected result: a 300-observation local inference sample. The recorded run reported 98.719 ms mean and 129.680 ms p95 single-record inference latency. This excludes endpoint, queue, database, and alert-processing overhead.

## 6. Fresh component-test evidence

Only the following pre-recorded safe commands were executed. The Maven command writes test reports to the service `target` directory in this repository, so do not repeat it until using an approved disposable build workspace.

```powershell
Set-Location api-gateway
mvn -o -B -Dtest=GatewaySecurityFilterTest test
```

The other 11 test cases are in-memory Python/standard-library tests listed in `evidence\component_tests\execution_summary.json`. They require the exact existing test setup. The two Kafka-worker suites are intentionally not reproduced here because the current interpreter lacks the `kafka` package; no package installation was performed for the evidence collection.

## What this guide does not reproduce

- Docker-stack health or recovery
- HTTP gateway authorization, live JWT validation, device-token authorization, or database persistence
- Kafka delivery, consumer recovery, alert deduplication, or Mailpit delivery
- REFIT replay, REFIT controlled-model training, or real-household experiments
- k6 load testing or fault injection

Historical integration and load results remain traceable in the evidence manifest, but they are not newly rerun by these commands.
