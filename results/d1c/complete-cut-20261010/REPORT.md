# Completed D1c cut: one artificial dataset

Cell 10, replicate 0: uwa, baseline, target 0.0, register reliability 0.8, prior scale 1.0.

Status: **converged**. All eight assigned components are present, with equal weight. Each supplies 16,000 draws; each contrast has 128,000 draws.

| Contrast | Generated truth | Mean | Median | 50% interval | 90% interval | Mean error |
|---|---:|---:|---:|---|---|---:|
| h2_prevalence_bridge | 0.00000 | 0.02740 | 0.03141 | [-0.05851, 0.11579] | [-0.18218, 0.22546] | 0.02740 |
| h1_fixed_usage | -0.01301 | -0.25169 | -0.24451 | [-0.43902, -0.05603] | [-0.73406, 0.20497] | -0.23867 |
| b_z | -0.10868 | -0.01913 | -0.01420 | [-0.10993, 0.07517] | [-0.24883, 0.19454] | 0.08955 |
| marking | -0.04910 | -0.02069 | -0.02123 | [-0.03557, -0.00658] | [-0.05398, 0.01475] | 0.02841 |

H2 and H1 are mean log production-probability contrasts. Marking is a probability difference; b_z is the direct production coefficient.

| Module | Parameter R-hat | Parameter ESS | Divergences | Contrast R-hat | Contrast ESS | Pass |
|---|---:|---:|---:|---:|---:|---|
| upstream | 1.004 | 1236 | 0 | n/a | n/a | yes |
| component 0 | 1.003 | 1801 | 0 | 1.001 | 1.248e+04 | yes |
| component 1 | 1.005 | 1642 | 0 | 1 | 1.253e+04 | yes |
| component 2 | 1.003 | 1386 | 0 | 1 | 1.217e+04 | yes |
| component 3 | 1.003 | 1413 | 0 | 1.001 | 1.298e+04 | yes |
| component 4 | 1.004 | 1234 | 0 | 1.001 | 1.208e+04 | yes |
| component 5 | 1.003 | 1303 | 0 | 1.001 | 1.252e+04 | yes |
| component 6 | 1.003 | 1497 | 0 | 1.001 | 1.217e+04 | yes |
| component 7 | 1.003 | 1479 | 0 | 1.001 | 1.203e+04 | yes |

This is the finite eight-component approximation to one cut posterior. Inner-chain diagnostics do not establish the accuracy of the eight-draw outer approximation.
One artificial dataset cannot establish coverage, power or empirical-design calibration. Conditional components and posterior draws are not study replications.
The original provisional vocabulary and response structure remain in this engineering run. No substantive support threshold or D1 verdict is assigned. The full grid remains stopped.
Diagnostic failures, if any, are retained. R-hat and ESS are assessed within each module, not across different conditional distributions.

`assembly.json` records provenance and diagnostics; `summaries.csv` holds the numeric table. `contrasts.npz` preserves arrays as [component, draw].
