# Continue the registered baseline comparisons

2026-10-10. After confirming completion of all eight components, Brett said
“well, don't just sit there”. Continue the existing simulation work with this
bounded batch, within his standing instruction to keep Mac and HF working
and the existing USD 10 HF budget. Do not restart the stopped 240-cell sweep.

| Location | Registered cell | Fit | Replicate |
|---|---:|---|---:|
| Mac, one worker | 4 | UWA joint | 0 |
| HF, separate machine, starts concurrently | 124 | Nicolas joint | 0 |
| HF, four machines with two component workers each | 130 | Nicolas cut | 0 |

All three are the registered baseline, H2 target zero, measured register
reliability .8 and prior scale 1. The completed UWA cut (cell 10, replicate 0)
is reused in the paired report. Each joint/cut pair uses the same generated
dataset and seed within its production design. The two designs have distinct
datasets. These fits check computation and compare conditional results; they
do not provide replicated calibration or adjudicate the empirical hypothesis.

Keep four chains, 4,000 downstream/joint production draws, 8,000 upstream
draws, 2,000 warmup, target acceptance .95, one sampler/BLAS core and the
original eight selected upstream draws. Keep the original priors, code,
estimands, data seeds, fit seeds and contrast-selection RNG ordering.

The driver imports the original fit and component functions. For HF it runs
the original fit only to its upstream checkpoint boundary, then assigns its
eight downstream components to eight workers. The four machines own components
0–1, 2–3, 4–5 and 6–7 respectively. Machine 0 computes the upstream fit once;
the other machines receive its verified checkpoint through the private bucket.
Every component has a separate
checkpoint directory. Cached final assembly requires all nine records and
uses the original summary calculation. Joint models also save their compact
contrast archives. Diagnostic failures remain completed results; execution
failures stop dispatch without automatic retries. No completed fit is repeated.

HF uses the already tested pinned Python image and exact requirements. Each
CPU Upgrade job has an eight-hour provider timeout, one attempt and at most USD
.24 compute. The five-machine batch has a USD 1.20 compute ceiling; reserve USD 3.36
across the eight historical/current submissions,
including the earlier cancelled setup job, below the USD 10 authorization.
Persist completed archives to the existing private bucket after each module.
No account token enters the container. Mac uses nice 10 and one worker.

Current HF UWA components took 1.595–1.971 hours end to end (median 1.833;
four observations). The earlier Nicolas/UWA measured-register downstream
timing ratio was about 1.825 at the smaller sampler budget. Applying that
ratio provisionally gives about 3–4 hours for one wave of eight Nicolas
components, plus setup/upstream work. Four cut machines cost USD .12/hour in total;
the joint machine adds USD .03/hour. Joint runtime has not yet been measured at
this budget. Provider queuing and account capacity can affect elapsed time. There
are no running HF jobs at preparation; no account-specific concurrency quota
was exposed by the documented CLI, so acceptance is checked at submission.
This is a planning extrapolation, not
a measured Nicolas/HF forecast. The new result will replace that missing
timing evidence. The old 18-day estimate must not be described as a validated
current forecast, nor scaled to one day from this benchmark.

Brett queried the initial concurrency limit twice and rejected the preference
for serial work. Both joint fits now start independently, with Nicolas on a
fifth HF machine and UWA on the Mac. There is no local serial queue. This uses
all ten independent downstream/joint tasks in the bounded comparison. A larger
16-configuration baseline batch was offered separately; it is not launched by
this specification. Completed UWA cut results must be reused, never refitted.

Report per-module runtime, peak memory, parameter and contrast diagnostics;
whole-fit estimates and 50%/90% intervals; and joint-minus-cut differences
within each design. Omit historical substantive-support labels. Preserve the
finite-cut limitation and the single-dataset denominator. The resulting four
configuration summaries are an engineering comparison, not four independent
replications. No new empirical outcome inputs are opened.

Publish this specification, driver, launcher, monitor and tests before fitting.
The local and HF assignments end at their listed boundaries. Further batches
can be scoped from their results and the remaining resources; no unattended
full-grid expansion is encoded here.

Price verified 2026-10-10: [HF Jobs pricing](https://huggingface.co/docs/hub/jobs-pricing).
