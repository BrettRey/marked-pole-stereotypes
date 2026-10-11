# First volunteer job: one archived timing fit

Authorized by Brett's request to start the ready volunteer Mac on 2026-10-11.
This is a hardware timing and portability repeat, excluded from calibration.
The agreed empirical-input freeze still precedes replicated D1c assessment.

Assignment `volunteer-001-timing-20261011` repeats archived UWA baseline joint
cell 12, replicate 0: H2 target −.10, register omitted, prior SD 1, 400 words,
12 participants per group, 40 groups. The code verifies the job, scientific source
hashes, seed root, sampler and package versions against the archived manifest.
Four chains run sequentially in one worker, with 2,000 warmup and 4,000 retained
draws per chain, target acceptance .95, and all 16,000 contrast draws retained.
There is no model change, fresh replicate, empirical-data access or cloud job.

The corresponding HF fit took about 103 minutes and peaked at 7.73 GiB process
RSS. This does not predict an M5 Air's speed or total memory pressure. This run
records compile, sampling and total elapsed time, process peak RSS and sampled
process-group RSS. The supervisor samples every two seconds and stops at 10 GiB
group RSS or six hours. These are stop triggers, not guaranteed memory limits;
the operating system and other applications also need memory. Close heavy apps.
The result preserves diagnostics even if they fail. There are no automatic
retries or subsequent jobs, and an existing assignment directory prevents a
second invocation. Ctrl-C stops the supervisor and its worker process group.
An interrupted fit does not resume automatically.

Run on the prepared Mac, plugged in with its lid open:

```sh
cd "$HOME/marked-pole-volunteer" && git pull --ff-only && \
  caffeinate -i .venv-volunteer/bin/python -u scripts/volunteer/first_job.py
```

Leave that Terminal window open. Progress appears about every 30 seconds.
The command ends after this one fit. The receipt is
`results/volunteer/volunteer-001-timing-20261011/receipt.json`; return it to Brett,
including any failure. It contains environment details, elapsed time, memory,
diagnostics, summaries and hashes, but no hostname, account name or credentials.
No result is uploaded automatically. Draws and the worker log remain on the Mac.

Coordinator validation uses `first_job.py --check` with the pinned environment
after publishing the implementation. This checks the archived assignment and
environment without fitting. Tests exercise process termination, memory/time
stop triggers, error receipts and successful completion using tiny software
fixtures, not substitute research observations. The actual M5 performance check
occurs only when Brett executes the command there.
