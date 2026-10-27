# Publication Experiment Checklist

## Safety boundary

- [x] Existing Home Energy Tracker containers, volumes, databases, Compose files, and credentials are out of scope.
- [x] REFIT Task 4C remains undeployed.
- [x] Only offline or isolated disposable experiments may contribute newly generated evidence.

## Evidence and manuscript baseline

- [ ] Identify the current manuscript source and retain its verified author details, architecture, figures, and references.
- [ ] Inventory historical evidence and distinguish it from newly reproduced or newly generated evidence.
- [ ] Verify dataset provenance, feature definitions, labels, units, and references.

## Experiment 1: ML validation

- [ ] Verify data shape, labels, missingness, construction, partitions, and duplication/leakage.
- [ ] Reproduce supported Random Forest and logistic-regression baseline evaluation.
- [ ] Measure held-out classification metrics, threshold behavior, robustness checks, and reproducibility metadata.

## Experiment 2 and 5: Functional and access-control validation

- [ ] Run safe, self-contained component tests and preserve exact outputs.
- [ ] Classify end-to-end links as demonstrated, component-tested, or blocked.
- [ ] Record authorization, validation, alert-deduplication, and deterministic-insight evidence.

## Experiment 3 and 4: Performance and resilience

- [ ] Reuse valid existing results only when raw evidence supports them.
- [ ] Run an isolated workload/fault test only if it can be proven independent of the retained stack.
- [ ] Otherwise report the precise blocked links rather than extrapolating.

## Experiment 6 and 7: Reproducibility, dataset, and literature

- [ ] Record reproducible commands, software versions, seeds, dataset identifiers, and artifact identities.
- [ ] Verify dataset provenance and citation metadata using authoritative sources.
- [ ] Assess journal scope and current indexing/quartile only with current authoritative evidence.

## Deliverables

- [ ] `experiment_results.csv`
- [ ] `experiment_reproduction.md`
- [ ] `evidence_manifest.md`
- [ ] `journal_readiness.md`
- [ ] `Home_Energy_Tracker_Research_Paper_Final.docx` with every numerical claim traced to evidence.
