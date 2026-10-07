# D1 grid on cloud sessions: protocol for one chunk
<!-- SUMMARY: Instructions a Claude Code cloud session follows to run one chunk of the D1 grid and push its results to its own branch · status: active · updated: 2026-10-07 -->

You are running **one chunk** of a pre-specified fake-data simulation (D1). The design is fixed in `scripts/d1/README.md` and committed. **Don't change any code, spec or plan file, and don't push to `master`.** Your only outputs are the chunk's results CSV, the run logs and, if something fails, an error note, all pushed to your own branch.

Your chunk number K and the total N are given in the message that started this session.

## 1. Set up (once)

```bash
uv venv .venv --python 3.14 || uv venv .venv
uv pip install --python .venv/bin/python -r requirements-d1.txt \
  || uv pip install --python .venv/bin/python "pymc==6.3.2" "nutpie==0.16.11" "pytensor==3.3.3" arviz numpy pandas scipy
.venv/bin/python scripts/d1/d1.py chunk --reps 20 --chunk K --of N --list | tail -1
```

The last line should report the chunk's job count (33 or 32 for N = 16). Record the Python and package versions (`.venv/bin/python -c "import sys, pymc, nutpie, pytensor; print(sys.version, pymc.__version__, nutpie.__version__, pytensor.__version__)"`). The run logs also record them.

## 2. Run, one fit per command, pushing after each

Repeat this command, **in the foreground with a 600000 ms timeout**, until its first line says `0 to run now`:

```bash
.venv/bin/python scripts/d1/d1.py chunk --reps 20 --chunk K --of N --max-fits 1 \
  && git add results/d1/grid logs/d1-*.json \
  && git commit -q -m "D1 grid chunk K of N: progress" \
  && git push -q origin HEAD:d1-grid-chunk-K
```

(Use the zero-padded chunk number in the branch name, e.g. `d1-grid-chunk-03`.) Each call runs at most one new fit and appends it to `results/d1/grid/chunk_KK_of_NN.csv`. The runner resumes, skipping fits already in the CSV, so a killed command loses at most one fit.

If one fit takes longer than the 10-minute foreground limit: run that same command in the background with a 7200000 ms timeout, check on it every few minutes with short commands (e.g. `tail -2` of its output), and push when it finishes. Then go back to the foreground loop.

## 3. Finish

When the runner reports `0 to run now`, push once more and reply with:

- the number of fits in the CSV;
- the median of the `seconds` column;
- how many fits have `rhat_max > 1.01` or `divergences > 0` (report them; don't drop or rerun them);
- the Python and package versions.

## If something goes wrong

Don't work around a failure by changing code, priors, sampler settings or the job list. Write the error and what you tried to `results/d1/grid/ERROR_chunk_KK.md`, push it to your branch, and stop.
