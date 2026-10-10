# Cut-component run report

Observed: 2026-10-10T23:03:37.702285+00:00

Verified completed components: 8/8 assigned, out of 8 required for this cut.
These are conditional results for cell 10, replicate 0. The full grid remains stopped.

| Location | Component | State | Parameter diagnostics | Contrast diagnostics | Sample time | Peak process memory |
|---|---:|---|---|---|---|---|
| cloud | 0 | verified_component | pass | pass | 134.8 min | 7.46 GiB |
| local | 1 | verified_component | pass | pass | 85.7 min | 6.53 GiB |
| hf | 2 | verified_component | pass | pass | 88.6 min | 7.32 GiB |
| local-003 | 3 | verified_component | pass | pass | 92.0 min | 6.54 GiB |
| hf-004 | 4 | verified_component | pass | pass | 101.5 min | 7.24 GiB |
| hf-005 | 5 | verified_component | pass | pass | 102.5 min | 7.25 GiB |
| hf-006 | 6 | verified_component | pass | pass | 81.9 min | 6.94 GiB |
| local-007 | 7 | verified_component | pass | pass | 110.6 min | 6.44 GiB |

Local queue: complete; current component None; completed from queue [3, 7].

HF batch compute ceiling: USD 0.72. Total authorized HF budget: USD 10.
Combined trial/batch provider-duration compute estimate: USD 0.1590; each job counted once, not an invoice.
HF batch stage: COMPLETED; components 4–6, two workers.
Conservatively reserved across all three submissions: USD 2.16; the malformed first submission was cancelled while queued.

Different fixed latent draws, compile environments and local contention; not matched hardware trials.
Cloud memory is a sampled process-group sum; local and HF memory use the worker’s process peak. These measures are not identical.
Diagnostic failures remain in the record. No incomplete mixture is reported as a full cut or calibration result.

Machine-readable status: `status.json`. Conditional intervals: `conditional-summaries.csv`. Verified archives: `collected/`.
