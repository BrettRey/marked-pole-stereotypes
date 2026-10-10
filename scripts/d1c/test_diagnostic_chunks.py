"""Compare batching against the existing ArviZ calculation; no model fits."""
import unittest
import warnings

import arviz as az
import numpy as np
import xarray as xr

from diagnostic_chunks import parameter_diagnostics


def original_diagnostics(posterior, names, divergences):
    rh = az.rhat(posterior, var_names=names)
    bulk = az.ess(posterior, var_names=names, method="bulk")
    tail = az.ess(posterior, var_names=names, method="tail")
    rhat = max(float(np.max(rh[n])) for n in names)
    ess = min(float(np.min(x[n])) for x in (bulk, tail) for n in names)
    finite = all(np.isfinite(np.asarray(x[n])).all()
                 for x in (rh, bulk, tail) for n in names)
    return dict(
        worst_rhat=max(names, key=lambda n: float(np.max(rh[n]))),
        worst_ess=min(names, key=lambda n: min(float(np.min(x[n])) for x in (bulk, tail))),
        good=finite and rhat <= 1.01 and ess >= 100 and divergences == 0,
        rhat=rhat, ess=ess, divergences=divergences)


class DiagnosticBatchTests(unittest.TestCase):
    def fixture(self):
        # Fixed synthetic diagnostic fixtures, not research data or MCMC fits.
        rng = np.random.default_rng(20261010)
        random_effects = rng.normal(size=(4, 600, 5, 7))
        random_effects[0, :, 4, 6] += .5
        return xr.Dataset({
            "scalar": (("chain", "draw"), rng.normal(size=(4, 600))),
            "vector": (("chain", "draw", "item"), rng.normal(size=(4, 600, 9))),
            "matrix": (("chain", "draw", "group", "word"), random_effects),
        })

    def check_same(self, posterior, names, divergences=0):
        expected = original_diagnostics(posterior, names, divergences)
        for size in (1, 6, 256):
            actual = parameter_diagnostics(posterior, names, divergences, batch_size=size)
            for key in ("worst_rhat", "worst_ess", "good", "divergences"):
                self.assertEqual(actual[key], expected[key], (size, key))
            for key in ("rhat", "ess"):
                np.testing.assert_allclose(actual[key], expected[key], rtol=1e-12,
                                           atol=1e-12, equal_nan=True)

    def test_scalar_vector_and_matrix_diagnostics_match(self):
        data = self.fixture()
        self.check_same(data, list(data))

    def test_noncontiguous_reordered_dimensions_match(self):
        data = self.fixture().isel(word=slice(None, None, 2))
        data["matrix"] = data.matrix.transpose("word", "draw", "group", "chain")
        self.check_same(data, list(data))

    def test_constant_parameter_remains_a_failed_diagnostic(self):
        data = self.fixture()
        data["constant"] = (("chain", "draw", "constant_item"), np.ones((4, 600, 3)))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            self.check_same(data, ["constant", "scalar", "matrix"])
            self.check_same(data, ["scalar", "constant", "matrix"])
            self.assertFalse(parameter_diagnostics(data, ["constant", "scalar"], 0)["good"])

    def test_divergences_keep_the_original_failure_rule(self):
        data = self.fixture()
        self.check_same(data, ["scalar", "vector"], divergences=1)
        self.assertFalse(parameter_diagnostics(data, ["scalar", "vector"], 1)["good"])


if __name__ == "__main__":
    unittest.main()
