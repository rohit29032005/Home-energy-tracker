# Task 1 — REFIT Dataset Verification and Scientific Selection

**Status:** complete as a source-feasibility and data-selection audit only.  
**Scope boundary:** no backend, Docker configuration, baseline model, device-token mapping, research paper, training, anomaly generation, replay, or end-to-end experiment was changed or run.

## 1. Decision

**Select the official REFIT cleaned dataset as the primary data source for the later experiment.**

The selected source is suitable because it provides recorded household-level aggregate electrical-power measurements at a nominal 8-second cadence, includes an official provenance chain, has a compatible time-series structure, and five local files were independently checksum-verified against the official Zenodo file manifest.  This conclusion is based on scientific fit, not on the convenience of the existing project data.

The exact later-study wording, if a replay is subsequently approved and completed, is: **"real-world recorded household electricity data replayed as a continuous live-like stream."** Task 1 has not performed that replay.

## 2. Official-source verification

| Item | Verified evidence | Task 1 interpretation |
|---|---|---|
| Primary cleaned dataset | University of Strathclyde, *REFIT: Electrical Load Measurements (Cleaned)*, DOI [10.15129/9ab14b0e-19ac-4279-938f-27f643078cec](https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec) | Official primary cleaned-data record. |
| Zenodo distribution | *REFIT: Electrical Load Measurements (Cleaned)*, DOI [10.5281/zenodo.5063428](https://doi.org/10.5281/zenodo.5063428) | Officially published individual-file manifest used for MD5 verification. |
| Original/raw record | University of Strathclyde, DOI [10.15129/31da3ece-f902-4e95-a093-e0a9536983c4](https://doi.org/10.15129/31da3ece-f902-4e95-a093-e0a9536983c4) | Records the original REFIT electrical-load study and its temporal scope. |
| Data descriptor | Murray *et al.*, *Scientific Data*, DOI [10.1038/sdata.2016.122](https://doi.org/10.1038/sdata.2016.122) | Primary description of acquisition, schema, and source cleaning. |
| Licence | The University source pages for the original and annotated datasets display **CC BY 4.0**. | Use the University record for licence evidence. The retrieved Zenodo page lists a Rights/License section but did not render a licence value, so this audit does **not** attribute the licence claim to Zenodo alone. |
| Household scope | 20 households, with aggregate and appliance-level measurements. | The local subset below is not a claim that all 20 households were inspected. |
| Temporal scope | October 2013 to June 2015; Loughborough, United Kingdom. | Historic household recordings; not a current live feed. |
| Nominal sampling interval | 8 seconds. | Use actual inter-sample intervals in a later power-to-energy conversion; do not blindly multiply every row by 8 seconds across gaps. |
| Measurement quantity/unit | Electrical consumption / active electrical power in watts. | The later ingestion contract requires interval energy, so a documented conversion policy will be needed in a future task. |
| Timestamp structure | The source descriptor documents a human-readable date-time (`YYYY-MM-DD HH:mm:ss`) and a UNIX timestamp. Locally verified files have header `Time,Unix,Aggregate,Appliance1...Appliance9,Issues`; first records conform to that paired time representation. | The human-readable `Time` timezone convention has not been independently verified here. Use the numeric `Unix` field for chronological ordering. |
| Aggregate data | Every verified local file contains the `Aggregate` column plus appliance channels. | `Aggregate` is the correct whole-home signal for this project's later ingestion/replay path. |

### 2.1 Source-cleaning provenance

The data descriptor documents upstream cleaning such as daylight-saving-time correction, duplicate-timestamp handling, appliance-monitor spike handling, and different treatments for short and long gaps. Consequently, the following quality gates describe the **cleaned release**, not the original raw sensor feed. They must not be represented as a raw-data-quality result.

## 3. Downloadable file manifest and local verification

The official Zenodo record currently exposes six individual CSV downloads (total listed size about 2.2 GB). It is a six-file convenience distribution, not an inventory of all 20 REFIT houses.

| Official file | Published size | Official MD5 | Local state | Task 1 result |
|---|---:|---|---|---|
| `CLEAN_House1.csv` | 400.8 MB | `f5336d80c700f866af0d997ea8d39146` | Present | Verified exact match |
| `CLEAN_House11.csv` | 255.8 MB | `5b41bae97ab28871fcfe5167b41c0347` | Present | Verified exact match |
| `CLEAN_House2.csv` | 325.4 MB | `13957fd139bf8f6ba8bceea36e85bb3d` | Present | Verified exact match |
| `CLEAN_House3.csv` | 407.3 MB | `ab6e34ea386eb4563bfcb9762619dc8f` | Present | Verified exact match |
| `CLEAN_House4.csv` | 395.8 MB | `efbfab2b04a61fbf7595422f15cacfb1` | Present | Verified exact match |
| `CLEAN_House5.csv` | 435.3 MB | `03938c844fdb09d787eb637bcf65f956` | Not present | Not downloaded or inspected |

The fresh local MD5 results are stored in [local_checksum_verification.csv](local_checksum_verification.csv). The five present files were checksum-verified **before** their header and quality-evidence inspection in this task.

### 3.1 Exact official download procedure for the missing House 5 file

House 5 is not needed to establish the current sufficient local cohort, so it was deliberately not downloaded during Task 1. If a future, approved study needs it, run the following from the repository root and inspect it only after the hash matches:

```powershell
$out = 'data\refit\raw\zenodo_5063428\CLEAN_House5.csv'
Invoke-WebRequest `
  -Uri 'https://zenodo.org/records/5063428/files/CLEAN_House5.csv?download=1' `
  -OutFile $out
(Get-FileHash -LiteralPath $out -Algorithm MD5).Hash.ToLowerInvariant()
```

Expected result:

```text
03938c844fdb09d787eb637bcf65f956
```

If the value differs, delete neither the existing verified files nor any audit evidence; treat the new download as invalid and re-download it from the [official Zenodo record](https://zenodo.org/records/5063428).

## 4. Official anomaly annotations

The official companion dataset is *Annotated load anomalies from the REFIT Dataset*, DOI [10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33](https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33), published by the University of Strathclyde under CC BY 4.0.

| Annotation fact | Verified status | Consequence for this experiment |
|---|---|---|
| It contains real, not simulated, appliance-level anomalies. | Verified from the official landing page. | It is potentially valuable for later appliance-level analysis. |
| It covers only Houses 1, 10, 16, 18, and 20. | Verified. | It does **not** provide a five-house aggregate ground truth for the locally verified cohort (only House 1 overlaps). |
| Listed appliance types include cold appliances, dishwasher, washing machine, tumble dryer, electrical heater, and microwave. | Verified. | Do not generalize these labels to whole-home aggregate anomalies without a separately verified alignment method. |
| `README_ICASSP.txt` and `REFIT_anomalies.csv` are published. | Verified; the CSV is listed as 26 KB. | The official file endpoint returned 403 during this audit, so its columns, label counts, timestamp semantics, and alignment to aggregate readings remain **UNRESOLVED**. |

Therefore, Task 1 does **not** claim any genuine aggregate anomaly label, anomaly count, precision/recall value, or label-based model evaluation.

## 5. Household-selection criteria and evidence

### 5.1 Pre-registered selection gates

A locally accessible household is considered sufficient for a future 14-day streaming experiment only if at least one exact 14-day window meets **all** of the following data-quality gates:

1. Verified source file: local MD5 equals the official Zenodo MD5.
2. Valid nominal-slot coverage: at least 90% (capped at 100% because source timestamps can jitter).
3. Estimated missing-slot fraction: at most 10%.
4. Maximum observed gap in the selected window: at most 3,600 seconds.
5. Native-cadence share: at least 90%, where native cadence means `abs(inter-sample interval − 8 s) <= 1 s`.

The gates do not use downstream model scores, alerts, or labels. Existing reproducible selection evidence is retained in [household_selection.csv](../16_refit_dataset_audit/household_selection.csv) and [selection_criteria.md](../16_refit_dataset_audit/selection_criteria.md).

### 5.2 Result: how many households are sufficient?

**Five of the five locally checksum-verified households are sufficient under the above 14-day-window gates.** This is a selection result, not an assumption that five households are required. It does **not** establish the number of usable households among REFIT's full 20-house archive, because the remaining files were not downloaded and inspected.

| House | Eligible 14-day window (UTC, per existing audit) | Coverage | Missing fraction | Max gap | Native-cadence share | Scientific treatment |
|---:|---|---:|---:|---:|---:|---|
| 1 | 2014-10-01T00:00:02Z to 2014-10-15T00:00:02Z | 100.00% | 0.8571% | 275 s | 95.97% | Primary candidate; only local house overlapping official anomaly-annotation coverage. |
| 2 | 2014-10-01T00:00:03Z to 2014-10-15T00:00:03Z | 100.00% | 0.4193% | 270 s | 95.64% | Primary candidate. |
| 3 | 2014-10-01T00:00:01Z to 2014-10-15T00:00:01Z | 100.00% | 0.7917% | 392 s | 95.98% | Eligible, but use as a solar-affected sensitivity case. |
| 4 | 2015-04-22T00:00:02Z to 2015-05-06T00:00:02Z | 100.00% | 0.5813% | 863 s | 99.30% | Primary candidate. |
| 11 | 2015-04-17T00:00:04Z to 2015-05-01T00:00:04Z | 100.00% | 0.1971% | 789 s | 98.79% | Eligible, but use as a solar-affected sensitivity case. |

The official data descriptor warns that aggregate values for Houses 3, 11, and 21 are affected by solar generation. Thus the scientifically conservative primary cohort is **Houses 1, 2, and 4**; Houses 3 and 11 are suitable to test robustness of a data-ingestion pipeline but should be identified as solar-affected rather than treated as ordinary consumption-only households.

## 6. Dataset comparison and recommendation

| Source | Scientifically relevant characteristics | Provenance / licence | Fit for this experiment | Decision |
|---|---|---|---|---|
| **REFIT cleaned data** | 20-house UK study; whole-home aggregate plus appliance channels; watts; nominal 8-second sampling; historic longitudinal records. | Official University record; CC BY 4.0; six-file Zenodo manifest supports local checksum verification. | Direct match for a later recorded household aggregate-power stream and the project's interval-energy ingestion path. | **Selected primary source.** |
| **REFIT anomaly annotations** | Real appliance-level anomalies, but only Houses 1/10/16/18/20; annotation file schema not yet inspected. | Official University record; CC BY 4.0. | Not a five-house aggregate-label dataset. May be a future companion resource after its schema is obtained and verified. | Not selected as primary replay or evaluation ground truth. |
| **UK-DALE (contingency only)** | Five UK homes; whole-house and appliance data at 6-second resolution; selected homes also have higher-frequency measurements. | Dataset owner page reports CC BY 4.0 and DOI [10.5286/UKERC.EDC.000004](https://doi.org/10.5286/UKERC.EDC.000004). | Scientifically suitable for future external validation, but its cadence differs and it has not been downloaded or verified locally. | No download and no use needed for Task 1. |
| `smart_meter_data.csv` currently used by the baseline model | Existing project CSV; prior audit found source, licence, acquisition method, and label provenance unverified. | Not established. | Cannot support a real-household or label-based research claim. | Not selected for this real-data experiment. |

**Recommendation:** retain REFIT as the primary dataset. A fallback is not needed for Task 1. UK-DALE should be considered only later if an external-validation experiment is explicitly approved; it must first undergo its own source, licence, checksum, and schema verification.

## 7. Device-token mapping limitation — explained, not changed

Task 0 established the following implementation limitation:

- The current Compose default binds a machine token only to device `1`.
- The existing replay utility accepts a single `REPLAY_DEVICE_TOKEN` per run, while its example household-to-device map uses device IDs `1` through `5`.
- The ingestion service checks the exact `deviceId:token` mapping and rejects reusing one configured device token across multiple device IDs.

Accordingly, the selected five-house cohort **must not be executed** with the current mapping. A later, explicitly authorized task must choose and document a valid credential and device mapping for the selected cohort before any replay. No mapping, credential, service, Docker configuration, or device data has been modified in Task 1.

## 8. Unresolved issues and non-claims

1. `CLEAN_House5.csv` is absent locally. It is not needed for the selected local cohort, but it is not checksum-verified.
2. The remaining REFIT households in the official 20-house archive have not been downloaded or evaluated. Therefore **five is not claimed to be the total number of usable REFIT households**.
3. The official annotation CSV and README are listed but could not be fetched from the official endpoint in this environment (HTTP 403). Its schema, label counts, timestamps, and aggregate alignment are unverified.
4. Solar generation affects Houses 3 and 11 in the local cohort. Results involving them must not be interpreted as pure consumption behavior without a stated treatment policy.
5. The cleaned dataset already contains publisher-applied cleaning. Do not describe its quality metrics as raw-sensor quality.
6. A future power-to-energy transformation must use actual consecutive sample intervals and document its gap rule; Task 1 has not computed it.
7. The device-token limitation prevents an authorized five-device execution as currently configured.
8. No model was trained, no synthetic anomaly was generated, no real-data event was replayed, and no end-to-end result was produced in Task 1.

## 9. Evidence locations

- Fresh hashes: [local_checksum_verification.csv](local_checksum_verification.csv)
- Existing selection results: [household_selection.csv](../16_refit_dataset_audit/household_selection.csv)
- Existing full local cleaned-file audit: [data_audit_report.md](../16_refit_dataset_audit/data_audit_report.md)
- Existing source manifest: [source_manifest.json](../16_refit_dataset_audit/source_manifest.json)

