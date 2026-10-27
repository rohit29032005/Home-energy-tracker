# Preprocessing report

1. Parsed `Timestamp` using the observed `%Y-%m-%d %H:%M:%S` format.
2. Checked numeric conversion, missing values, negative electricity values, and complete duplicate rows.
3. Removed only invalid or duplicate rows found by the audit.
4. Sorted records chronologically with a stable sort.
5. Encoded `Normal` as 0 and `Abnormal` as 1.
6. Derived `Hour` and `DayOfWeek` from the same row timestamp.
7. Derived `ConsumptionDeviation = Electricity_Consumed - Avg_Past_Consumption` from fields available on the same row.

The pipeline does not calculate lags or rolling windows. It never uses a later timestamp to construct a feature for an earlier timestamp. `Avg_Past_Consumption` is retained as a dataset-provided historical field; its source construction cannot be independently verified from the repository.
