# Cut-component run report

Observed: 2026-10-10T19:04:21.858749+00:00

Verified completed components: 2/8 assigned, out of 8 required for this cut.
These are conditional results for cell 10, replicate 0. The full grid remains stopped.

| Location | Component | State | Parameter diagnostics | Contrast diagnostics | Sample time | Peak process memory |
|---|---:|---|---|---|---|---|
| cloud | 0 | awaiting_cloud_export | pending | pending | pending | pending |
| local | 1 | verified_component | pass | pass | 85.7 min | 6.53 GiB |
| hf | 2 | verified_component | pass | pass | 88.6 min | 7.32 GiB |
| local-003 | 3 | running | pending | pending | pending | pending |
| local-004 | 4 | queued | pending | pending | pending | pending |
| local-005 | 5 | queued | pending | pending | pending | pending |
| local-006 | 6 | queued | pending | pending | pending | pending |
| local-007 | 7 | queued | pending | pending | pending | pending |

Local queue: running; current component 3; completed from queue [].

HF active-job compute ceiling: USD 0.72. Total authorized HF budget: USD 10.
Provider-duration compute estimate so far: USD 0.0520; this is not an invoice.
Conservatively reserved across both submissions: USD 1.44; the malformed first submission was cancelled while queued.

Different fixed latent draws, compile environments and local contention; not matched hardware trials.
Cloud memory is a sampled process-group sum; local and HF memory use the worker’s process peak. These measures are not identical.
Diagnostic failures remain in the record. No incomplete mixture is reported as a full cut or calibration result.

Machine-readable status: `status.json`. Conditional intervals: `conditional-summaries.csv`. Verified archives: `collected/`.
