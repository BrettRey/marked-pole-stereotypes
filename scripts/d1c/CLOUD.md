# One D1c Claude-cloud benchmark

Run exactly the benchmark authorized on 10 October 2026 and specified in
`scripts/d1c/README.md`: upstream preparation and downstream component 0 of
cell 10, replicate 0. This is artificial-data computation. Do not edit any
scientific code, sampler settings, plan, or specification. Do not start the
full grid, other cells, retries, extra sessions, or replacement fits.

Use the source commit supplied in the launch prompt. Work on the cloud
session's assigned branch, never master or main. Verify that HEAD is the
supplied commit and tracked files are clean. Keep that assigned branch name;
do not switch to a new branch that the session cannot push.

Make one environment setup attempt, with no version substitutions:

```bash
uv venv .venv --python 3.14
uv pip install --python .venv/bin/python -r requirements-d1.txt
```

Run the prewritten driver, substituting the source commit and assigned branch:

```bash
.venv/bin/python scripts/d1c/cloud_benchmark.py --source SOURCE_COMMIT --branch ASSIGNED_BRANCH
```

Keep the session active until the driver exits. A shell-tool wait limit is
not a computation deadline: retain the running command and use sparse waits
or progress checks, about every five minutes. Do not kill a working fit
because a foreground tool call yielded. The driver has no wall-clock cutoff.
It stops at the one-component boundary, even when diagnostics fail. Do not
end the cloud conversation while leaving only an unattended background fit.
Do not start a goal loop or use additional agents.

The driver automatically commits and pushes its start record, each completed
component archive with its checksum record, and its final report. It exports
only files under `results/d1c/cloud-canary-20261010/`. Never commit caches,
full traces, third-party inputs, or credentials. The driver checks an empty
index before export and stops its worker if an export fails. Git command
timeouts protect an individual export operation, not the sampler duration.

If setup or the driver fails, preserve the error in
`results/d1c/cloud-canary-20261010/ERROR.txt`, commit that explicit path and
any unexported completed checkpoint files, and push to the assigned branch.
Do not change dependencies or run another fit. If a push fails, report it
without repeated retries. Leave all completed local outputs intact.

At completion report the branch, worker result, runtime, peak memory and
diagnostics. A completed conditional component is not a complete cut
estimate or calibration. If credit readings are unavailable, say so;
elapsed time is not a credit-spend estimate.
