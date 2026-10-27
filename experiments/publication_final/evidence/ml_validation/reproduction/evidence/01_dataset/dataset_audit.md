# Dataset audit

## Identity and provenance

- Filename: `smart_meter_data.csv`
- Size: 619684 bytes
- SHA-256: `d48df940fd29444fb9222fc0b59cfde632e147ccd1d49dc7bed9d5f9dc88f588`
- Source/license/version: not available in the CSV or repository metadata; no provenance claim is made.

## Structure

- Raw data rows: 5000
- Retained rows after valid-row and duplicate checks: 5000
- Columns: 7
- Timestamp range: 2024-01-01 00:00:00 to 2024-04-14 03:30:00
- Sampling interval: median 30.0 minutes; unique observed intervals: [30.0]
- Duplicate rows: 0
- Invalid timestamp rows: 0
- Invalid numeric rows: 0
- Negative electricity rows: 0
- Entity identifier columns: none are present; the dataset is a single unlabeled entity stream.

## Labels

The label column is `Anomaly_Label` with values `Normal` and `Abnormal`; it is binary after encoding `Normal=0`, `Abnormal=1`.

| label | count | percentage |
| --- | --- | --- |
| Normal | 4750 | 95.0 |
| Abnormal | 250 | 5.0 |

## Suitability

The dataset has a timestamp, numeric consumption/environmental attributes, and a binary anomaly label. It is suitable for supervised anomaly classification with a chronological split. No claim is made about the original label-generation process because that provenance is not present in the repository.
