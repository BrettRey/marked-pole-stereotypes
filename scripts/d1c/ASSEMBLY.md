# Assemble the completed eight-component cut

2026-10-10. Brett asked to continue after the lexical pilot. This reporting
step completes the already assigned cell 10, replicate 0. It submits no
jobs, fits no model and changes no sampler or scientific source file.

The collector remains responsible for retrieval. The assembler reads its
saved archives, independently verifies every manifest, checksum, assignment,
seed and draw budget, and requires all eight distinct components plus the
shared upstream checkpoint. Missing or corrupt components cannot be replaced
by other components or omitted from a partial mixture. Nonfinite contrast
draws stop assembly. Failed diagnostics remain results, with a failure label.

Replay the original `d1c.fit` summarization from a read-only cache that raises
on every missing key and refuses writes. No fallback to sampling is possible.
The pinned generator reproduces this same artificial dataset and its known
truths using the original seed; this is neither a new replicate nor empirical
data. Check current generator/source hashes and package versions first.

Each component contributes its original 16,000 contrast draws, giving equal
weight to eight selected upstream draws and 128,000 draws per contrast. Keep
the component axis in the exported array archive. Report means, medians,
50% and 90% intervals, generated truths and errors. Omit the older code's
substantive-threshold labels, in accordance with Brett's reporting decision.
Report upstream and within-component diagnostics separately; there is no
R-hat computed across different conditional distributions.

This is a finite eight-component approximation to one cut posterior for one
simulated dataset. Successful inner-chain diagnostics do not establish the
accuracy of the eight-draw outer approximation. Posterior draws and
conditional components are not independent study replications. No power,
coverage-rate, empirical-design calibration or D1 verdict follows from this
single result. The full grid remains stopped.

Publish this specification, the assembler and tests before execution. Run:

```bash
.venv/bin/python scripts/d1c/assemble_cut.py --source <published-commit> --watch
```

Without `--watch`, incomplete input exits with a clear pending message.
Watching waits for the existing collector, records progress in stdout, and
exits after writing `results/d1c/complete-cut-20261010/`. A cache lock prevents
two assemblers. Output publication uses a staging directory and a final
rename; an existing result is never overwritten. A terminal incomplete
collection or verification error stops the watcher without retrying a fit.
The output contains the original component hashes, software versions,
assembly source identity, summaries and all nine diagnostic records.
