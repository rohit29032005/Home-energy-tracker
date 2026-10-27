# ML evaluation summary

Models were selected by validation F1 after tuning their decision threshold on the validation interval. The test interval was not used for threshold selection. The selected model is `random_forest`.

| model | decision_threshold | validation_f1 | test_precision | test_recall | test_f1 | test_roc_auc | test_pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| random_forest | 0.31 | 0.914894 | 0.880952 | 0.925 | 0.902439 | 0.99743 | 0.948532 |
| logistic_regression | 0.28 | 0.113208 | 0.053333 | 1.0 | 0.101266 | 0.422852 | 0.05971 |
