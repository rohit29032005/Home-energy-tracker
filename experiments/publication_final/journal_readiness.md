# Journal readiness assessment

## Decision

**Not ready for a Q1 journal submission at this stage.** The manuscript is substantially stronger as a transparent controlled-prototype study after the newly reproduced ML evaluation, uncertainty analysis, input-contract tests, and offline component tests. However, the current evidence does not yet establish a transferable household-energy anomaly-detection result or a sufficiently broad systems evaluation for a defensible Q1 claim.

## Contribution that can be defended now

The contribution is an event-driven Home Energy Tracker architecture combining gateway-mediated telemetry, usage aggregation, ML inference, threshold/anomaly alert handling, and deduplication. The paper now contributes a traceable reproduction of the repository's supervised baseline: a chronological 5,000-record experiment with a Random Forest that reproduced the recorded held-out F1 of 0.902439 exactly, a 300-draw conditional bootstrap analysis, input-contract tests, and an explicit Wokwi/training-scale mismatch finding. The component evidence validates selected logic under mocks and in-memory test fixtures.

The novelty is therefore **integration plus evidence-aware evaluation**, not a new anomaly-detection algorithm. It should not be described as a real-world meter-validation study, a production deployment, or a generalizable multi-household benchmark.

## Publication-critical gaps

1. The supplied 5,000-record CSV lacks independently documented source, licence, physical units, label-generation process, and causal provenance for `Avg_Past_Consumption`.
2. The Wokwi interface experiment demonstrates an energy-scale mismatch: the model was trained with `Electricity_Consumed` in the range 0 to 1, while five of six documented simulator boundaries are above 1. The simulator input is synthetic and unlabelled.
3. The new tests are offline components or in-process inference. Full end-to-end, broker, persistence, deduplication, notification, load, and fault-recovery evidence is historical only and was not rerun because the existing stack is not authorized for recovery.
4. REFIT household replay remains gated by isolated identity/device provisioning and has not been deployed. No real REFIT result is included in the manuscript.
5. The current analysis lacks a documented external household test set, labelled real anomaly ground truth, multi-household temporal validation, and a formally comparable state-of-the-art baseline suite.

## Journal suitability, verified only by scope

The following journals are potential scope matches after the scientific gaps are closed; this is **not** a claim that they currently rank Q1 or would accept this manuscript. Current indexing/quartile, article-type rules, word limits, data/code policy, and author guidelines must be checked directly at the time of submission.

| Outlet | Scope fit after further evidence | Current manuscript suitability |
| --- | --- | --- |
| Applied Energy | Strong only if the work demonstrates a validated energy-management or demand-side contribution using real, well-documented household data. Official journal page: https://www.sciencedirect.com/journal/applied-energy | Not suitable yet: current value is mainly architecture and prototype evidence. |
| Energy and Buildings | Potentially suitable for robust residential/building-energy sensing, prediction, or control evaluation. Official journal page: https://www.sciencedirect.com/journal/energy-and-buildings | Not suitable yet: needs real/official data, external validation, and a stronger energy-analysis contribution. |
| Internet of Things | Potentially suitable for a well-evaluated IoT systems paper with reproducible deployment, security, and fault-performance evidence. Official journal page: https://www.sciencedirect.com/journal/internet-of-things | Potentially closest by scope, but still premature until the system evaluation is rerun in a fully isolated environment. |

## Highest-value next experiment

Obtain an official, licensed household dataset with documented sampling and units, such as the REFIT electrical-load dataset (official repository: https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements/; associated dataset paper DOI: https://doi.org/10.1038/sdata.2016.122). After isolated household/device provisioning is approved, first align aggregate power and interval-energy units with the ingestion contract, then evaluate a pre-registered temporal and household-held-out protocol. Any anomaly labels derived from controlled perturbations must remain explicitly labelled as controlled rather than observed real faults.

## Minimum submission gate

Before reconsidering a Q1 submission, the study needs: (i) documented data provenance and licences; (ii) unit- and feature-aligned real/official household evaluation; (iii) household-held-out or external temporal validation; (iv) a reproducible isolated end-to-end study including authorization, queue, persistence, alert-deduplication, and fault behavior; (v) repeated performance runs with documented resources; and (vi) a final reference and journal-policy check from official sources. Until then, submit only as a prototype/engineering evaluation to an appropriately scoped venue, if at all.
