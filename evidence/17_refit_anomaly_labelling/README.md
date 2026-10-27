# Task 4 Reproduction and Verification

Task 4 produces a labelled **controlled-perturbation** copy of the frozen Task 2 REFIT interval-energy events. It is not an official REFIT anomaly-label ingestion and it does not alter the raw or Task 2 data.

## Generate

Run from the repository root. The default destination must not already exist; that safeguard prevents silent replacement of prior evidence.

```powershell
python -m py_compile scripts\refit_task4_generate_anomalies.py
python -u scripts\refit_task4_generate_anomalies.py
```

For a new deliberate rerun, specify a new destination:

```powershell
python -u scripts\refit_task4_generate_anomalies.py `
  --output-dir data\refit\labeled-verified-rerun `
  --seed 20261009
```

## Regression test

```powershell
python -m unittest scripts\test_refit_task4_generate_anomalies.py -v
```

The test checks deterministic output for the same seed, source immutability, and the rule that only test rows may receive positive labels.

## Independently verify the generated artifact

```powershell
python -u scripts\refit_task4_verify_anomalies.py
```

Expected result for the current generated artifact:

```text
PASS: verified 795,187 derived events and 40 episodes
```

The verifier writes `anomaly_dataset_verification.json`; it does not generate or modify labels.

## Read before using this data

Read [strategy.md](strategy.md). In particular, report any later scores only as controlled-perturbation detection performance. Do not call them genuine REFIT anomaly results.
