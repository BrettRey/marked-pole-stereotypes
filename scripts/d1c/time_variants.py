#!/usr/bin/env python3
"""Time each D1c computational graph at the registered sampler sizes.

Representative baseline data, prior SD 1, register reliability .8 (when used).
A downstream benchmark conditions on one upstream posterior draw; the full
cut still uses eight separately normalized downstream fits in d1c.py.
"""
import json
import time
from datetime import datetime, timezone
from importlib.metadata import version

import d1c

import numpy as np
import pandas as pd


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = d1c.ROOT / 'results/d1c' / f'timings-{stamp}.csv'
    log = d1c.ROOT / 'logs' / f'd1c-timings-{stamp}.json'
    records = []
    for design in d1c.DESIGNS:
        for reliability in (0., .8):
            job = next(c for c in d1c.cells() if c['design'] == design
                       and c['scenario'] == 'baseline' and c['target'] == 0.
                       and c['feedback'] == 'joint' and c['reliability'] == reliability
                       and c['prior'] == 1.)
            job['rep'] = 0
            observed, truths, data_seed = d1c.generate(job)
            upstream = d1c.upstream_data(observed, reliability)
            downstream = d1c.downstream_data(observed)
            fixed = None
            for mode in ('upstream', 'downstream', 'joint'):
                started = time.perf_counter()
                try:
                    data = (upstream if mode == 'upstream' else
                            dict(downstream, **fixed) if mode == 'downstream' else
                            dict(upstream, **downstream))
                    trace, diagnostic = d1c.sample(
                        job, mode, data, d1c.seed(5, job['cell'],
                                                ('upstream', 'downstream', 'joint').index(mode)))
                    contrast_seconds = 0.
                    if mode == 'upstream':
                        fixed = {f'{k}_fixed': d1c.flattened(trace, k)[0]
                                 for k in ('z', 'v', 's')}
                        if reliability:
                            fixed['h_fixed'] = d1c.flattened(trace, 'h')[0]
                    else:
                        contrast_started = time.perf_counter()
                        values, good, crhat, cess = d1c.posterior_contrasts(
                            trace, observed, fixed if mode == 'downstream' else None,
                            np.random.default_rng(d1c.seed(6, job['cell'])))
                        contrast_seconds = time.perf_counter() - contrast_started
                        diagnostic.update(contrast_good=good, contrast_rhat=crhat, contrast_ess=cess)
                    record = dict(design=design, reliability=reliability, prior=1.,
                                  data_seed=data_seed, **diagnostic,
                                  contrast_seconds=contrast_seconds,
                                  total_seconds=time.perf_counter()-started)
                    del trace
                except Exception as exc:
                    record = dict(design=design, reliability=reliability,
                                  prior=1., mode=mode, error=repr(exc),
                                  total_seconds=time.perf_counter()-started)
                records.append(record)
                pd.DataFrame(records).to_csv(output, index=False)
                log.write_text(json.dumps(dict(
                    timestamp=stamp, records=records,
                    sampler=dict(draws=d1c.DRAWS, tune=d1c.TUNE, chains=d1c.CHAINS,
                                 cores=1, cut_draws=d1c.CUT_DRAWS),
                    packages={p: version(p) for p in
                              ('pymc', 'nutpie', 'pytensor', 'numpy', 'arviz')},
                    root_seed=d1c.SEED, pytensor_flags=d1c.os.environ['PYTENSOR_FLAGS'],
                    note='Wall time under concurrent CPU load; prior 1 and measured reliability .8.'
                ), indent=2))
                print(record, flush=True)
    frame = pd.DataFrame(records)
    if 'sampling_seconds' not in frame or len(frame.dropna(subset=['sampling_seconds'])) != 12:
        raise RuntimeError('Incomplete benchmark; inspect timing CSV and JSON')
    # 5 scenarios x 2 targets x 2 priors x 40 replicates for each
    # design-feedback-reliability stratum. Reliability .5 uses the measured
    # graph timing at .8; prior 2.5 uses timing at prior 1.
    seconds = 0.
    for design in d1c.DESIGNS:
        for reliability in (0., .5, .8):
            subset = frame[(frame.design == design) &
                           (frame.reliability == (0. if reliability == 0. else .8))]
            costs = {row['mode']: row['total_seconds']-row['compile_seconds']
                     for row in subset.to_dict('records')}
            seconds += 5*2*2*40*(costs['joint']+costs['upstream']+8*costs['downstream'])
    # Each worker builds each shape/register/prior/mode once. Prior 2.5
    # assumed to have the same compilation cost as prior 1.
    compile_seconds = 3*2*float(frame.compile_seconds.sum())
    estimate = dict(grid_cells=len(list(d1c.cells())), replicates_per_cell=40,
                    workers=3, serial_fit_seconds=seconds,
                    compilation_cpu_seconds=compile_seconds,
                    estimated_wall_hours=(seconds+compile_seconds)/3/3600,
                    assumptions='Warm graph reuse, three effective worker cores; .5 approximated by .8, prior 2.5 by 1; baseline timing across scenarios.')
    path = d1c.ROOT / 'results/d1c' / f'grid-time-{stamp}.json'
    path.write_text(json.dumps(estimate, indent=2))
    print(estimate, flush=True)


if __name__ == '__main__':
    main()
