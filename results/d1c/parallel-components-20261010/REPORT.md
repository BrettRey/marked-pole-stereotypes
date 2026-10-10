# Cut-component run report

Observed: 2026-10-10T19:18:10.068199+00:00

Verified completed components: 2/8 assigned, out of 8 required for this cut.
These are conditional results for cell 10, replicate 0. The full grid remains stopped.

| Location | Component | State | Parameter diagnostics | Contrast diagnostics | Sample time | Peak process memory |
|---|---:|---|---|---|---|---|
| cloud | 0 | awaiting_cloud_export | pending | pending | pending | pending |
| local | 1 | verified_component | pass | pass | 85.7 min | 6.53 GiB |
| hf | 2 | verified_component | pass | pass | 88.6 min | 7.32 GiB |
| local-003 | 3 | running | pending | pending | pending | pending |
| hf-004 | 4 | queued | pending | pending | pending | pending |
| hf-005 | 5 | queued | pending | pending | pending | pending |
| hf-006 | 6 | queued | pending | pending | pending | pending |
| local-007 | 7 | queued | pending | pending | pending | pending |

Local component 3 sampler counts, including warmup: [3655, 0, 0, 0] / 6,000 per chain. These counts are not recoverable completion checkpoints.

Local queue: running; current component 3; completed from queue [].

HF batch compute ceiling: USD 0.72. Total authorized HF budget: USD 10.
Combined trial/batch provider-duration compute estimate: USD 0.0525; each job counted once, not an invoice.
HF batch stage: RUNNING; components 4–6, two workers.
Conservatively reserved across all three submissions: USD 2.16; the malformed first submission was cancelled while queued.

Different fixed latent draws, compile environments and local contention; not matched hardware trials.
Cloud memory is a sampled process-group sum; local and HF memory use the worker’s process peak. These measures are not identical.
Diagnostic failures remain in the record. No incomplete mixture is reported as a full cut or calibration result.

Machine-readable status: `status.json`. Conditional intervals: `conditional-summaries.csv`. Verified archives: `collected/`.
