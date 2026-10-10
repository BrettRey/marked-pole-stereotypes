"""Calculate the registered scalar-parameter diagnostics in bounded batches.

Rank-normalized R-hat and ESS operate on one scalar parameter at a time.
Batching event coordinates avoids ranking copies of an entire large random-
effect array at once. It does not split draws or chains or change estimators.
"""
from __future__ import annotations

import numpy as np


def parameter_diagnostics(posterior, names, divergences, *, batch_size=256):
    import arviz as az
    import xarray as xr

    if batch_size < 1 or not names:
        raise ValueError("Positive batch size and sampled variable names required")
    maxima, bulk_minima, tail_minima = {}, {}, {}
    finite = True
    for name in names:
        variable = posterior[name]
        event_dims = [dim for dim in variable.dims if dim not in ("chain", "draw")]
        values = np.asarray(variable.transpose("chain", "draw", *event_dims))
        shape = values.shape[2:]
        count = int(np.prod(shape)) if shape else 1
        maximum, bulk_minimum, tail_minimum = -np.inf, np.inf, np.inf
        for start in range(0, count, batch_size):
            if shape:
                indices = np.unravel_index(np.arange(start, min(start+batch_size, count)), shape)
                # Advanced indexing copies only this batch, even when the
                # source array is not contiguous. Never reshape-copy a full
                # random-effect array just to flatten its event coordinates.
                batch = values[(slice(None), slice(None), *indices)]
            else:
                batch = values[:, :, None]
            dataset = xr.Dataset({name: (("chain", "draw", "parameter"), batch)})
            rh = np.asarray(az.rhat(dataset)[name])
            bulk = np.asarray(az.ess(dataset, method="bulk")[name])
            tail = np.asarray(az.ess(dataset, method="tail")[name])
            finite = finite and all(np.isfinite(x).all() for x in (rh, bulk, tail))
            # Propagate NaNs as np.max/np.min over the original variable do.
            maximum = np.maximum(maximum, np.max(rh))
            bulk_minimum = np.minimum(bulk_minimum, np.min(bulk))
            tail_minimum = np.minimum(tail_minimum, np.min(tail))
        maxima[name] = float(maximum)
        bulk_minima[name], tail_minima[name] = float(bulk_minimum), float(tail_minimum)
    # Keep the old variable/reduction order, including reporting behavior
    # when a failed diagnostic contains NaNs. The finite gate still fails.
    rhat = max(maxima.values())
    ess = min(value for minima in (bulk_minima, tail_minima) for value in minima.values())
    return dict(
        worst_rhat=max(names, key=maxima.__getitem__),
        worst_ess=min(names, key=lambda name: min(bulk_minima[name], tail_minima[name])),
        good=bool(finite and rhat <= 1.01 and ess >= 100 and divergences == 0),
        rhat=rhat, ess=ess, divergences=int(divergences))
