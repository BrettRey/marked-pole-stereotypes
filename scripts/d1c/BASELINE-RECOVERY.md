# Recovery of two interrupted baseline fits

2026-10-11. The authorized 16-configuration batch ended with 14 completed
configurations, all passing diagnostics. HF host `joint-0` stopped at
01:46:51 UTC because a bucket write raised `OSError: [Errno 5] Input/output
error`. The controller then stopped both active samplers. Cells 0 and 12
have no completed checkpoints; the last exported iteration counts were
[6000, 6000, 6000, 4106] and [6000, 6000, 6000, 4398]. These are interrupted
computations, not completed diagnostic failures. Preserve the provider log,
original partial exports and the 14-result report.

This is a manually diagnosed infrastructure recovery within Brett's
authorization to complete these 16 configurations and spend up to USD 15.
It does not enable the original launcher's prohibited automatic model
retries. Run cells 0 and 12 once more, independently on two CPU Upgrade
machines, with the original source specification, packages, data and fit
seeds, four chains, 4,000 draws, 2,000 warmup and target acceptance .95.
Both attempts use separate output prefixes and retain their provenance.
No completed fit, including any diagnostic failure, is repeated or replaced.

The recovery controller invokes the unchanged original worker from source
94eb4e41ec22a4e00de7ef243e6da6985af7756a. It checks the separately published
recovery code as well. Bucket I/O errors are logged and retried every 30
seconds without interrupting the sampler. After the worker exits, export
may retry for at most 30 minutes; success requires the exported archive to
pass the original byte-hash, specification, shape and seed checks. Other
exceptions remain failures. No sampler is relaunched by this controller.

Both provider jobs have one attempt and a 12-hour timeout. At the previously
verified USD .03/hour price, this adds at most USD .72, bringing the full
conservative reservation to USD 13.80 of USD 15. No additional scope or
scientific variant is introduced. Publish the recovery code and fixture
tests before launch. Existing batch and scientific files remain unchanged.

The recovery monitor collects only these two assignments, combines them
with the original 14 results and preserves diagnostic failures. It cannot
fit or submit models. Its report retains the one-artificial-dataset-per-
design/target and eight-outer-draw limitations; no calibration verdict is
inferred from completion or convergence.
