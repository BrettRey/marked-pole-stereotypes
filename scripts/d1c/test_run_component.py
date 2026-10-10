"""Verify independent component scheduling against real contrast selection."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import xarray as xr

import d1c
from component_state import ComponentState, contrast_arrays
from run_component import component_rng, export_files, run_one


class ComponentSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(d1c, "DRAWS", 12).start()
        patch.object(d1c, "CHAINS", 4).start()
        patch.object(d1c, "POST_DRAWS", 48).start()
        patch.object(d1c, "P", 1).start()
        names = ("bz", "bm", "bf", "bv", "bs", "item_sd", "content_sd", "ell", "g0", "gz", "gv",
                 "gs", "f0", "lz", "ls", "lv", "lm", "sig_f", "b_z")
        rng = np.random.default_rng(20261010)
        data = {n: (("chain", "draw"), rng.normal(size=(4, 12))) for n in names}
        for name in ("item_raw", "content_raw"):
            data[name] = (("chain", "draw", "item"), rng.normal(size=(4, 12, 1)))
        self.trace = SimpleNamespace(posterior=xr.Dataset(data))
        self.observed = {"m": np.zeros(1)}
        # Cheap contrast arithmetic, keeping the production function's actual
        # draw selection and ArviZ diagnostics. No model fit occurs.
        patch.object(d1c, "contrasts", side_effect=lambda t: dict(
            h2=float(t["bz"]) + float(np.asarray(t["z"])[0]),
            h1_fixed_usage=float(t["bf"]), marking=float(t["bm"]))).start()
        self.selected = {name: np.arange(8.)[:, None] for name in ("z", "v", "s")}
        self.metadata = {"rng_state": np.random.default_rng(33).bit_generator.state}

    def test_skipped_rng_matches_actual_sequential_contrast_function(self):
        sequential = component_rng(self.metadata["rng_state"], 0, chains=4, draws=12, contrast_draws=48)
        for component in range(8):
            fixed = {f"{name}_fixed": values[component] for name, values in self.selected.items()}
            expected = d1c.posterior_contrasts(self.trace, self.observed, fixed, sequential)
            independent = component_rng(self.metadata["rng_state"], component,
                                        chains=4, draws=12, contrast_draws=48)
            actual = d1c.posterior_contrasts(self.trace, self.observed, fixed, independent)
            self.assertEqual(actual, expected)
            self.assertEqual(independent.bit_generator.state, sequential.bit_generator.state)

    def test_assigned_component_keeps_sequential_draws_and_failed_diagnostics(self):
        job = dict(next(cell for cell in d1c.cells() if cell["cell"] == 10), rep=0)
        sequential = component_rng(self.metadata["rng_state"], 0, chains=4, draws=12, contrast_draws=48)
        expected = None
        for component in range(2):
            fixed = {f"{name}_fixed": values[component] for name, values in self.selected.items()}
            expected = d1c.posterior_contrasts(self.trace, self.observed, fixed, sequential)[0]
        with tempfile.TemporaryDirectory() as tmp:
            with ComponentState(Path(tmp), {"job": job, "component": 1}) as store:
                with patch.object(d1c, "generate", return_value=(self.observed, {}, 123)), \
                     patch.object(d1c, "downstream_data", return_value={}), \
                     patch.object(d1c, "sample", return_value=(self.trace, {"good": False})) as sample:
                    result = run_one(job, 1, copy.deepcopy(self.metadata), self.selected, store)
                    second = run_one(job, 1, copy.deepcopy(self.metadata), self.selected, store)
                self.assertEqual(sample.call_count, 1)
                self.assertEqual(sample.call_args.args[3], d1c.seed(4, 10, 0, 1))
                self.assertEqual(second, result)
                self.assertFalse(result["diagnostic"]["good"])
                self.assertEqual(list(store.records), ["downstream-001"])
                metadata, arrays = store.load("downstream-001")
                self.assertEqual(metadata["rng_state"], sequential.bit_generator.state)
                for name, values in contrast_arrays(expected).items():
                    np.testing.assert_array_equal(arrays[name], values)

    def test_export_survives_source_loss_and_excludes_incomplete_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, exported = Path(tmp) / "source", Path(tmp) / "exported"
            spec = {"job": {"cell": 10}, "component": 2}
            with ComponentState(source / "checkpoints", spec) as store:
                store.save("downstream-002", {"good": False}, {"h2": np.arange(16.)})
            (source / "checkpoints/component-downstream-003.npz").write_bytes(b"unfinished")
            (source / "runtime.json").write_text(json.dumps({"state": "component_complete"}))
            export_files(source, exported)
            import shutil
            shutil.rmtree(source)
            with ComponentState(exported / "checkpoints", spec) as restored:
                metadata, arrays = restored.load("downstream-002")
                self.assertFalse(metadata["good"])
                np.testing.assert_array_equal(arrays["h2"], np.arange(16.))
            self.assertFalse((exported / "checkpoints/component-downstream-003.npz").exists())

    def test_export_rejects_corruption_before_copying_commit_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, exported = Path(tmp) / "source", Path(tmp) / "exported"
            with ComponentState(source / "checkpoints", {"job": {"cell": 10}}) as store:
                store.save("downstream-002", {}, {"h2": np.arange(16.)})
            (source / "checkpoints/component-downstream-002.npz").write_bytes(b"damaged")
            with self.assertRaises(ValueError):
                export_files(source, exported)
            self.assertFalse((exported / "checkpoints/component-downstream-002.json").exists())


if __name__ == "__main__":
    unittest.main()
