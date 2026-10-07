# Data

- `raw/`: downloads exactly as obtained. Not in git; licences vary.
- `derived/`: files built from `raw/` by scripts, committed only where the source licence allows.
- `manifests/sources.csv`: one row per input, with URL, DOI, access date, SHA-256, licence, local path and status. A source that can't be obtained gets a row with `status = unavailable` and the reason, and its strand stops (brief, ground rules).

No stand-in or simulated data replace an unavailable source. Strand A's simulated data are the experiment, not stand-ins, and live under `results/`.
