# REFIT Task 1 Pre-registered Household Selection Criteria

```json
{
  "minimum_window_days": 14,
  "minimum_valid_8_second_grid_coverage": 0.9,
  "maximum_estimated_missing_slot_fraction": 0.1,
  "maximum_gap_seconds": 3600,
  "minimum_native_cadence_share": 0.9,
  "native_cadence_definition": "abs(inter-sample interval - 8 s) <= 1 s",
  "selection_rule": "Select every accessible household that satisfies all gates. If more than five satisfy them, rank by coverage descending, longest usable segment descending, invalid-record rate ascending, then numeric household ID ascending. No model score is used."
}
```

The script selects based on data integrity only. It does not use labels, model output, alert counts, or other downstream results.
