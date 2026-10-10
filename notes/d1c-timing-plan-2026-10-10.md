# D1c next step: time the model variants

The two-replicate baseline pilot now passes every convergence gate. The next step in the handoff is to time the remaining computational variants, so we can decide how much D1c simulation is practical. This is a bounded timing stage. The full simulation grid needs a later resource decision based on these results.

## Proposed run

Run the existing `scripts/d1c/time_variants.py` once. It performs 12 fits: two designs (UWA-like and Nicolas-like), two register settings (omitted and measured at reliability .8), and three components (upstream measurement, downstream conditional, and joint).

All use baseline artificial data, null H2 and coefficient prior SD 1. Retain the current fixed budget: four chains, 1,000 warmup steps, 2,000 retained draws per chain, target acceptance .95, and the existing seeds and diagnostic thresholds. Run sequentially, with one sampler core. Record parameter diagnostics and, where defined, predictive-contrast diagnostics using every retained draw.

The downstream benchmark conditions on one upstream posterior draw. It measures the cost of one component; it does not validate the full cut model, which mixes eight conditional fits. A failed diagnostic remains a failure. There are no automatic retries, sampler changes or grid launches.

## Resources and limits

Allow several hours, potentially longer. The completed joint baseline fits took about 26–29 minutes each including diagnostics; the other variants have not been timed at this budget. Twelve fits include four simpler upstream fits and eight production-model fits. This is a planning estimate, not a measured runtime for the whole benchmark.

The timing script contains a hypothetical 40-replicate grid calculation. That is an extrapolation, not an approved replication count. Its 240 cells would require 9,600 cell-replicate evaluations, including 4,800 joint fits and 4,800 cuts, each with eight downstream fits. At the observed baseline cost, the joint portion alone would imply roughly 31 days on three effective cores if all joint cells cost the same. Actual costs could differ substantially.

The benchmark also approximates reliability .5 with the .8 timing and prior SD 2.5 with the SD 1 timing, and extends baseline costs to stress scenarios. Report these assumptions with any estimate. No full-grid job follows automatically.

## Execution and deliverables

1. Record this scope, source hashes, sampler budget, package versions, command and environment before launch. Keep the model code unchanged and preserve the successful pilot.
2. Run the 12-fit benchmark once, keeping its incremental CSV, JSON and console output. Preserve exceptions and diagnostic failures; stop if a runtime fault makes further benchmark results invalid. Do not silently repair the model and continue.
3. Summarize timings and convergence by component, distinguish measurements from extrapolations, and update the D1c README, decisions and status. Use those results to propose a feasible next stage.

Your no-commit/no-push instruction remains in force. This step uses no empirical outcomes and does not enter D1b, threshold examples, Part 8 or Norman extraction.

Review checkpoint: proceed with this bounded 12-fit timing stage, or annotate a different resource limit before launch.

---
comments:
  c1:
    body: approved
    by: user
    at: 2026-10-10T11:20:50.370Z
