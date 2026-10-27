# Task 3 — Cohort and Chronological Split Plan

## 1. Frozen cohort assignment

| Cohort | Households | Retained Task 2 interval records | Intended use | Prohibited use |
|---|---:|---:|---|---|
| Primary | H1, H2, H4 | H1: 153,578; H2: 154,985; H4: 160,284; total: 468,847 | Main historical replay/system-integration evidence; any future primary ML analysis | Do not treat as a population-representative sample or merge with solar cases. |
| Solar sensitivity | H3, H11 | H3: 153,375; H11: 172,965; total: 326,340 | Separate sensitivity reporting for the same processing workflow | Do not report as corrected net import, normal household consumption, or pooled primary ML evidence. |

The Task 1 selection criterion was a checksum-valid source file with at least one 14-day window satisfying all pre-registered gates. The Task 2 quality report then confirmed source-to-output reconciliation for all five selected houses. This protocol preserves those decisions and does not add House 5 or any other household.

## 2. Canonical event ordering

For any household, the canonical event ordering is:

```text
ascending original_unix, then ascending source_row_number
```

The Task 2 `Unix` field is canonical. `original_time_text` is retained as evidence only, while `timestamp_utc_from_unix` is derived from `Unix`. No partition, feature, or replay decision may use the visual order of CSV rows as a substitute for this explicit sort.

Cross-gap records (`interval_seconds > 16`) were excluded in Task 2 and must stay excluded. The solar cases remain assigned to their own cohort even if their timestamps are otherwise valid.

## 3. Frozen within-household temporal split

If and only if an offline ML stage is approved, each household will be partitioned **before** fitting transformations, selecting thresholds, or creating controlled perturbations. The deterministic count rule is:

```text
n_train      = floor(0.70 × N)
n_validation = floor((N - n_train) / 2)
n_test       = N - n_train - n_validation
```

The earliest records are training, the next records validation, and the latest records testing. There is no random row split.

| House | N | Train (earliest 70%) | Validation (next 15% approx.) | Test (latest 15% approx.) | Cohort |
|---:|---:|---:|---:|---:|---|
| H1 | 153,578 | 107,504 | 23,037 | 23,037 | Primary |
| H2 | 154,985 | 108,489 | 23,248 | 23,248 | Primary |
| H4 | 160,284 | 112,198 | 24,043 | 24,043 | Primary |
| H3 | 153,375 | 107,362 | 23,006 | 23,007 | Solar sensitivity |
| H11 | 172,965 | 121,075 | 25,945 | 25,945 | Solar sensitivity |

These are planned split counts only. Task 3 creates no training, validation, test, or labelled data file.

## 4. Leakage controls

1. **Chronology:** no train row may occur after any validation/test row for the same household.
2. **Feature fitting:** imputation values, normalisation/scaling parameters, thresholds, and feature-selection decisions must be estimated from the training partition only.
3. **Causal features:** a feature for time `t` may use only measurements at or before `t`; no future observation may enter it.
4. **Rolling windows:** before ML begins, the maximum lookback and stride must be specified. Evaluation windows must be non-overlapping, or all train/evaluation samples with an overlapping feature window across a split boundary must be purged. The exact rule is an approval gate because no feature recipe exists in Task 3.
5. **Source gaps:** a window containing a Task 2 material-gap boundary must be excluded or treated according to a pre-declared gap policy; it may not be silently imputed.
6. **Synthetic labels:** if later approved, construct them only after the chronological split and only in the pre-declared held-out partition. Never select anomaly locations using test-derived global statistics.
7. **Duplicate control:** preserve source identity in the experiment ledger. A duplicate/near-duplicate event cannot appear in both training and test merely because it was retransmitted.

## 5. Meaning of the two evaluation designs

### 5.1 Within-household temporal evaluation

A model fit on the early H1 interval sequence and evaluated on late H1 events tests temporal transfer within H1. The same applies independently to H2 and H4. A weighted or macro average across these separate primary-house results may be reported only with per-house values; it is not unseen-household generalisation.

### 5.2 Unseen-household evaluation

If enough approved labels are later available, use leave-one-primary-household-out folds:

| Held-out test household | Development households |
|---|---|
| H1 | H2, H4 |
| H2 | H1, H4 |
| H4 | H1, H2 |

All preprocessing parameters in each fold must be fit using only the development households. H3 and H11 never join these folds. With only three primary households, this is a limited stress test rather than broad population generalisation.

## 6. Label-dependent boundaries

The current frozen Task 2 aggregate stream has no verified aggregate anomaly target. Therefore:

- System-integration stages may use all retained primary records without creating ML accuracy labels.
- A genuine-label analysis is potentially H1-only and appliance-level until official annotation schema, timestamp alignment, appliance-channel mapping, and selected-window overlap are verified.
- A future controlled-perturbation benchmark must be called controlled-perturbation detection and must follow the chronological split above before labels are generated.

See `labeling_strategy.md` for the option comparison and `protocol_open_questions.md` for the blockers.

## 7. Future split-artifact manifest requirements

Before any model fitting, create a separate immutable split manifest containing the Task 2 input hash, cohort, source identities, sorted boundaries, final counts, feature-lookback rule, label source, seed if a controlled perturbation stage is approved, and software version. The manifest must not overwrite Task 2 artifacts.
