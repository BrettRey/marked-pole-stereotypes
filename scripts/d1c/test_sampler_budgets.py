"""Verify budget routing to a mocked sampler backend; no model fits."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import d1c
import numpy as np
import xarray as xr


class CompiledFixture:
    def with_data(self, **data):
        return self


class SamplerBudgetTests(unittest.TestCase):
    def test_actual_sample_entry_point_routes_mode_budgets(self):
        job = dict(design="uwa", reliability=0., prior=1., cell=0, rep=0)
        cache = {(40, 1, False, 1., mode): (CompiledFixture(), ["theta"])
                 for mode in ("upstream", "downstream", "joint")}

        def backend(compiled, **kwargs):
            shape = kwargs["chains"], kwargs["draws"]
            return SimpleNamespace(
                posterior=xr.Dataset({"theta": (("chain", "draw"),
                    np.random.default_rng(123).normal(size=shape))}),
                sample_stats={"diverging": np.zeros(shape, dtype=bool)})

        with patch.multiple(d1c, DRAWS=128, UPSTREAM_DRAWS=256, TUNE=64, COMPILED=cache):
            with patch("nutpie.sample", side_effect=backend) as sampler:
                for mode, expected in (("upstream", 256), ("downstream", 128), ("joint", 128)):
                    trace, diagnostic = d1c.sample(job, mode, {}, 456)
                    self.assertEqual(sampler.call_args.kwargs["draws"], expected)
                    self.assertEqual(sampler.call_args.kwargs["tune"], 64)
                    self.assertEqual(sampler.call_args.kwargs["seed"], 456)
                    self.assertEqual(sampler.call_args.kwargs["cores"], 1)
                    self.assertEqual(sampler.call_args.kwargs["target_accept"], .95)
                    self.assertEqual(trace.posterior.sizes["draw"], expected)
                    self.assertEqual(diagnostic["draws"], expected)
                    self.assertEqual(diagnostic["tune"], 64)


if __name__ == "__main__":
    unittest.main()
