# Hardware checks for a mixed compute pool

Specified 2026-10-11, before execution. Brett requested the fastest overall run for the least overall budget, allowing a blend of providers, and asked Codex to keep working while he was away. These bounded hardware checks use the existing USD 15 ceiling. The full empirical-design calibration remains deferred until its input specification is frozen.

## Hugging Face: two versus three workers

Two `cpu-upgrade` machines run concurrently. Each repeats components 0–5 of archived cell 142, replicate 0: the Nicolas-style baseline, target −0.1, reliability .8, prior 1, cut feedback. One machine uses two simultaneous workers; the other uses three. Six tasks fill an integer number of waves in both configurations. This is a comparison of these two machines, not replicated evidence about the provider's hardware distribution.

The six fixed upstream selections come from the existing archived upstream fit, hash `28683a3209b6dfadb1054d1f8bbae142e4cf5a37816fd2cf902e4c0c6984af3e`. The runner reads that existing artifact from historical commit `b54f265f57197b81d6ba43f6c6701246052b1174`; it does not recommit draw archives. All model source hashes, package versions, data and sampling seeds, four chains, 2,000 warmup iterations, 4,000 retained draws per chain and all 16,000 contrast draws remain fixed. These repeats never enter the calibration totals or replace existing results.

Each provider job has one attempt and a 12-hour timeout. The controller stops after 11.5 hours or sampled aggregate worker RSS reaches 28 GiB. A worker failure stops further queued starts; there are no model retries. Checkpoints and receipts export to the existing private HF bucket every 30 seconds, with storage failures isolated from fitting and a bounded final export retry. The sampling interval cannot guarantee interception of a sudden OOM; a killed job remains a failed benchmark.

Maximum new compute: 2 × 12 × USD .03 = **USD .72**. Even retaining the old over-conservative USD 13.80 reservation, the ceiling is USD 14.52, below USD 15. Prior completed work's duration-based compute estimate is USD 2.3845, not an invoice. No further jobs are automatically launched by these checks.

Report elapsed time, six-task makespan, completed fits per machine-hour, provider compute cost per completed fit, per-worker RSS and diagnostics, aggregate sampled RSS and any failures. Compare identical component seeds between arms. Three workers are usable only if all six archives validate and the original diagnostic requirements pass. Prefer the faster/cheaper observed arm; do not describe the expected 33% cost reduction as an observed result. Concurrent machine variation and this single dataset limit generalization. Joint fits retain the two-worker limit because their observed memory demands are higher.

## Colab: one matched timing fit

`colab-one` repeats archived cell 12, replicate 0, with one worker, the same assignment used for the volunteer Mac timing. It has a six-hour controller limit and 10 GiB sampled worker RSS limit. Source and package checks match the archived fit. The remote bootstrap uses an isolated Python 3.14.8 environment; the notebook kernel's Python version is irrelevant. It retains a ZIP with receipts and completed checkpoints for download. No Google or HF tokens are placed in the VM by this code.

Google's [AI Pro help](https://support.google.com/googleone/answer/14534406?hl=en-en) states that eligible members get 200 Colab compute units; the [September announcement](https://developers.googleblog.com/colab-is-now-part-of-your-google-ai-plan/) says rollout is gradual and distinguishes Ultra background execution. The public evidence does not establish Brett's current balance, unit renewal date, CPU unit rate, machine availability or concurrent runtime limit. Google AI Pro must not be treated as Colab Pro+.

The official [Colab CLI](https://github.com/googlecolab/google-colab-cli), locally checked at 0.7.4, supports CPU sessions, usage reporting, remote execution and file download. CLI authentication is not yet available in this session. Query `colab usage` after signing in, record the account balance and rate, then allocate at most one CPU runtime for this check. Do not buy credits or select a GPU. Measure actual CPU/RAM and rate before starting the fit. A GPU allocation does not accelerate this unchanged CPU sampler.

Colab fitting requires verified account access, available units and the displayed consumption rate. The account now reports 400 available units; Brett rejected the analyst-imposed 10-unit trial allowance, which is withdrawn. The available balance is the compute pool, with no additional credit purchase authorized. The prepared timing fit retains its six-hour stop. The first standard CPU runtime reports .08 units/hour, so six hours of fitting costs .48 units, plus setup and export time. Run availability and safe artifact retrieval must be checked before assigning batches to ephemeral Colab storage.

## Allocation after the checks

Keep Yoko's current timing run. Additional volunteer environments are optional; their hardware descriptions alone are not throughput measurements. Use included Colab units where they buy useful completed work without extra payment, then HF for additional parallel capacity. Compare elapsed time and failure-adjusted cost per valid component, including setup and idle time. Preserve distinct logical module IDs and a central assignment record; a hardware repeat is not an additional independent simulated dataset.

More machines shorten wall time but do not reduce the required number of fits. The preliminary 4,000-module design budget is dominated by 3,200 conditional fits. Better packing may lower its HF cost; included Colab capacity may lower additional cash cost. Neither change resolves the still-unfrozen empirical specification or justifies launching that full design now.

## After the first Colab sign-in attempt (2026-10-11)

The stock 0.7.4 CLI received only identity scopes and rejected the narrower grant before saving a token. Its partial-consent handling is also reported in [upstream issue 116](https://github.com/googlecolab/google-colab-cli/issues/116). The local `colab_access.py` entry point requests identity and Colab access, omitting the optional Cloud and Drive scopes. It uses a separate `colab-only-token.json` credential file, applies the same narrower scope list during refresh, and retains ordinary scope validation. No token contents are logged or committed. The launcher sets a private file-creation mask.

Use the entry point consistently for subsequent project commands:

```bash
uvx --from google-colab-cli==0.7.4 python scripts/compute/colab_access.py --auth oauth2 usage
```

The user must approve the Colab permission on Google's consent screen and paste the returned authorization code into their own Terminal. A successful balance query, not browser identity sign-in alone, confirms readiness. This correction does not change the running HF benchmark source, sampler or assignments.

After successful sign-in (2026-10-11): the balance query confirms 400 units and no pre-existing runtime. The assigned standard CPU runtime has two logical CPUs, 13,605,822,464 bytes RAM and an available C++ compiler. `run_colab_timing.py` owns only `Brett-colab-timing1`, runs the published bootstrap, polls its receipt, downloads the finished archive, verifies its manifest and hashes, and releases that runtime after success or failure. It never starts a replacement fit. The local lifecycle limit is six hours forty minutes, covering the six-hour fit limit plus bounded setup/export. The original 10-unit proposal is not an active restriction.

## Event alerts (2026-10-11)

`watch_events.py` reads the two existing monitor status files every ten seconds, without model calls or extra cloud queries. It records newly verified fits, diagnostic failures, job endings, collection errors, runtime-release failures and monitor updates stale for over five minutes. Stable event IDs suppress duplicate alerts. Events and acknowledgements persist under `results/compute/event-watch-20261011/`.

Brett could not see the Notification Center test but confirmed the persistent macOS dialog test. The watcher therefore uses one persistent dialog at a time. It continues recording events while that dialog awaits acknowledgement, then groups any waiting events in the next dialog. It keeps the Mac from idle-sleeping only while either existing monitor process is alive, then releases the sleep assertion. Closing the lid or shutting down still suspends local monitoring. The watcher stops after both monitors end and all event dialogs are acknowledged. These local alerts do not wake a Codex turn automatically.
