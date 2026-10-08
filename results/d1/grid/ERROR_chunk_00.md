# Chunk 0 of 16: stopped, resume check never skips oracle fits

**Status:** stopped after 16 fit records (15 distinct jobs of 22). Seven jobs haven't run. No code, spec or plan file was changed.

## What happened

Fit 15 ran `s3_mechanism small rep4 oracle` (552.9 s). The next call of the CLOUD.md command (fit 16) ran **the same job again** (499.8 s) instead of moving on. Both runs are in `chunk_00_of_16.csv` (rows 114–117 and 118–121; same seed, so R-hat max is 1.0025 both times and the posteriors agree to about 1e-9). Neither row set has been dropped or edited.

## Cause

`scripts/d1/d1.py`, `run()`, lines 316–319. The resume set is built from the CSV with `.astype(str)`. Oracle jobs have `indicator=None`, which `to_csv` writes as an empty cell. `read_csv` reads that back as NaN, so the CSV key is `'nan'`, but the job key is `str(None)`, which is `'None'`. They never match.

Checked read-only against the current CSV:

```
CSV key:  ('s3_mechanism', 'small', '4', 'oracle', 'nan', '1.0')
job key:  ('s3_mechanism', 'small', '4', 'oracle', 'None', '1.0')
```

So an oracle job is never treated as done. This one comes before the 7 remaining jobs in the chunk's job list, so with `--max-fits 1` every call re-runs it. The runner can never report `0 to run now`.

## Scope

Every chunk has oracle jobs (`--list` counts for K = 0…15: 2, 4, 3, 2, 2, 2, 3, 3, 2, 2, 2, 3, 4, 2, 2, 2). Each chunk session following CLOUD.md will start repeating its first oracle job once it reaches it and will add a duplicate oracle fit to its CSV on every call.

## What I tried

Nothing that changes the runner. CLOUD.md forbids working around a failure by changing code or the job list, so I didn't patch `d1.py`, change `--max-fits`, or delete the duplicate rows.

## Not yet run (chunk 0)

- s3_mechanism small rep10 joint e_r50
- s3_mechanism small rep15 joint e_r80
- s3_mechanism large rep0 joint e_r50
- s3_mechanism large rep3 joint e_r80
- s3_mechanism large rep8 joint e_r50
- s3_mechanism large rep13 joint e_r80
- s3_mechanism large rep18 oracle

## Proposed fix (not applied)

Normalize the missing indicator on both sides of the comparison, for example in `run()`:

```python
done = {tuple(r) for r in prev[["scenario", "size", "rep", "model", "indicator", "prior_scale"]]
        .fillna({"indicator": "None"}).astype(str).drop_duplicates().itertuples(index=False)}
```

The summary step should also deduplicate oracle fits that were run twice (same job key), since chunks may already contain repeats.

## Other notes on this run

- From fit 2 onward each fit was started in the background with a 7,200,000 ms timeout. That's the CLOUD.md provision for fits over 10 minutes: fit 1 took 1,685.8 s, and fit 8 took 2,553.2 s.
- Python 3.14.6; PyMC 6.3.2; nutpie 0.16.11; PyTensor 3.3.3 (installed from `requirements-d1.txt`).
