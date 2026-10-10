# Parallel baseline batch

2026-10-10. Brett said “max it out” after the 16-configuration expansion was
offered, then raised the total HF authorization to USD 15. Run the remaining
registered baseline configurations with the maximum useful parallelism below
that budget. This replaces the pending scope question. Another Roughdraft
checkpoint is unnecessary under his instruction to keep moving.

The fixed scope is the Cartesian product of UWA/Nicolas design, target
0/−.1, joint/cut, and register reliability 0/.8, with prior scale 1 and
replicate 0. These are original cells, not new model variants.

| Work | Original cells | Placement |
|---|---|---|
| Completed, reuse | 10 | Existing verified UWA cut |
| Already running, reuse | 4, 124, 130 | Existing Mac and five HF machines |
| Six additional joints | 0, 12, 16, 120, 132, 136 | Three HF machines, two workers each |
| Six additional cuts | 6, 18, 22, 126, 138, 142 | Four HF machines per cut, two downstream workers each |

There are 27 new machines, 54 additional downstream/joint workers, and six
upstream fits. With the current work, peak useful concurrency is 64 model
workers on 32 HF machines plus the Mac. Each cut's upstream fit runs once;
its eight downstream components wait only for that verified checkpoint.
Independent cells, both joint workers on a machine, and all ready cut
components run concurrently. No completed or currently assigned fit repeats.
The earlier baseline pilot used 2,000 draws, 1,000 warmup and a 100-draw
summary subsample; it is retained as a distinct pilot and cannot replace
the frozen 4,000-draw production specification for cell 0.

Keep the existing scientific code, data and fit seeds, priors, four chains,
4,000 downstream/joint draws, 8,000 upstream draws, 2,000 warmup, target
acceptance .95 and eight selected upstream draws. Preserve contrast RNG
ordering. The absent-register upstream has z/v/s only; the measured-register
upstream additionally has h with shape [8, 400, 3]. This distinction changes
checkpoint validation, not either registered model.

All new jobs use the tested pinned Python image, exact requirements and
CPU Upgrade hardware at USD .03/hour, with one provider attempt and a
12-hour timeout: at most USD .36 each, or USD 9.72 for 27. Reserve the full
historical ceilings of USD 2.16 and the active batch's USD 1.20 as well.
The resulting conservative compute ceiling is USD 13.08, below USD 15.
The earlier unused reservations are not needed to make this bound hold.
No automatic rerun of a failed or timed-out model is permitted. A clearly
rejected capacity/rate-limit submission may wait for capacity and resubmit;
an ambiguous response must be reconciled by its unique job name first.

Launch upstream-owning hosts and independent joint hosts first, then all
other cut hosts, without an artificial concurrency limit. HF may queue jobs
or reject submissions at its account limit; keep an explicit receipt for
every accepted job and pending assignment. No credential enters a container.
Each host writes to its own private bucket prefix, with immutable checkpoints
verified before their readiness marker. Existing running code stays frozen.

The monitor collects all outputs, verifies hashes, seeds, package versions
and assignment identity, then replays summaries from complete caches only.
Report per-module diagnostics, runtime and memory, all fit estimates with
50%/90% intervals, and paired joint/cut mean differences and width ratios.
Keep failed diagnostics visible. This remains one artificial dataset per
design/target combination, not replicated calibration. The eight-draw outer
approximation and provisional empirical-design inputs remain limitations.
The remaining scenarios, priors and reliability .5 cells are outside this
batch; the stopped 240-cell sweep is not restarted by this launcher.

Publish this specification, runner, launcher, monitor and fixture tests
before fitting. Provider price: [HF Jobs pricing](https://huggingface.co/docs/hub/jobs-pricing).
