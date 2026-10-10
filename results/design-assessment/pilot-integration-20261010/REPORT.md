# Design-assessment integration check

Engineering integration report; not empirical-design calibration or a power claim.

The input registry still has unresolved empirical-design inputs. Substantive benchmarks remain unset.

| Cell | Estimand | Attempted | Converged | Mean 90% width | Width MCSE | 90% coverage | Exact 95% interval for coverage |
|---|---|---:|---:|---:|---:|---|---|
| 0 | h2_prevalence_bridge | 2 | 2 | 0.4116 | 0.0233 | 2/2 | 0.1581–1.0000 |
| 0 | h1_fixed_usage | 2 | 2 | 0.9397 | 0.0042 | 2/2 | 0.1581–1.0000 |
| 0 | b_z | 2 | 2 | 0.5214 | 0.0226 | 2/2 | 0.1581–1.0000 |
| 0 | marking | 2 | 2 | 0.0751 | 0.0026 | 2/2 | 0.1581–1.0000 |

Two pilot datasets do not establish design performance.
Original per-component contrast budget: 100; historical summaries are not recomputed from full traces.
Quantile and RMSE bootstrap SEs may be unstable with few independent datasets.
Rate denominators can vary; selected metrics use only selected nonzero-truth fits.
A failure counts as no usable detection in the per-attempt measure, not evidence of a null effect.

All metrics, failure denominators, pairing and provenance: `assessment.json`.
