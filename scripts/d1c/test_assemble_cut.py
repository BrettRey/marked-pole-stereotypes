"""Reporting-only fixture tests; no research observations or model fits."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import assemble_cut as assembly
import collect_parallel as collection
import d1c
from component_state import ComponentState
from run_state import digest


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / "collection"
        self.output = self.root / "assembled"
        self.job = dict(next(c for c in d1c.cells() if c["cell"] == 10), rep=0)
        self.truths = dict(h2_prevalence_bridge=0., h1_fixed_usage=.1, b_z=-.2, marking=-.03)
        self.spec = dict(job=self.job, root_seed=20261009, seeds=dict(data=123),
            sampler=dict(chains=4, draws=4000, tune=2000, cut_draws=8, contrast_draws=16000),
            sources={"scripts/d1c/d1c.py": "fixture-science", "scripts/d1c/component_state.py": "fixture-storage"})
        upstream_arrays = {name: np.zeros((8, 400)) for name in ("z", "v", "s")}
        # The generator has three register covariates per item, unlike its
        # three scalar item latents. Match that actual archive contract.
        upstream_arrays["h"] = np.zeros((8, 400, 3))
        rng_state = np.random.default_rng(9).bit_generator.state
        self.upstream_metadata = dict(diagnostic=dict(mode="upstream", seed=1, good=True,
            contrast_good=True, rhat=1.001, ess=3000, divergences=0), rng_state=rng_state)
        self.arrays = {}
        self.addCleanup(patch.stopall)
        with contextlib.redirect_stdout(io.StringIO()):
            cloud = self.folder / "collected/cloud/checkpoints"
            with ComponentState(cloud, self.spec) as state:
                state.save("upstream", self.upstream_metadata, upstream_arrays)
                upstream_hash = state.records["upstream"]["archive_sha256"]
            self.canonical = collection.json_file(cloud / "manifest.json")
            patch.object(collection, "UPSTREAM_SHA", upstream_hash).start()
            for i, location in enumerate(assembly.LOCATIONS):
                directory = self.folder / "collected" / location
                if i:
                    with ComponentState(directory / "upstream", self.spec) as state:
                        state.save("upstream", self.upstream_metadata, upstream_arrays)
                    spec = dict(self.spec, component=i, upstream_archive_sha256=upstream_hash,
                        upstream_commit=collection.UPSTREAM_COMMIT,
                        upstream_specification_signature=digest(self.spec))
                else:
                    spec = self.spec
                # Separated modes expose an incorrect average-of-quantiles
                # summary and any omission of a failed component.
                arrays = {name: np.linspace(i-4., i-3., 16000) for name in collection.NAMES}
                self.arrays[i] = arrays
                diagnostic = dict(mode="downstream", seed=d1c.seed(4, 10, 0, i),
                    good=i != 6, contrast_good=True, draws=4000, tune=2000,
                    rhat=1.03 if i == 6 else 1.001, ess=500, divergences=0,
                    contrast_rhat=1.001, contrast_ess=1000)
                with ComponentState(directory / "checkpoints", spec) as state:
                    state.save(f"downstream-{i:03d}", dict(diagnostic=diagnostic,
                        rng_state=rng_state), arrays)
        patch.object(d1c, "generate", return_value=({}, self.truths, 123)).start()
        patch.object(d1c, "upstream_data", return_value={}).start()
        patch.object(d1c, "downstream_data", return_value={}).start()
        self.sampling = patch.object(d1c, "sample", side_effect=AssertionError("Assembly attempted sampling")).start()

    def test_replay_equal_weight_mixture_preserves_failed_component(self):
        cache, provenance = assembly.read_complete(self.folder, self.canonical)
        rows, status, stacked = assembly.replay(cache, self.job)
        self.sampling.assert_not_called()
        self.assertEqual(status["status"], "diagnostic_failure")
        self.assertEqual(len(status["diagnostics"]), 9)
        self.assertEqual([p["component"] for p in provenance], list(range(8)))
        expected = np.concatenate([self.arrays[i]["h2"] for i in range(8)])
        row = next(r for r in rows if r["estimand"] == "h2_prevalence_bridge")
        self.assertAlmostEqual(row["mean"], expected.mean())
        np.testing.assert_allclose([row[k] for k in ("lo90", "lo50", "median", "hi50", "hi90")],
                                  np.quantile(expected, [.05, .25, .5, .75, .95]))
        self.assertEqual(stacked["h2"].shape, (8, 16000))
        self.assertFalse(row["good"])
        self.assertNotIn("support", row)
        self.assertNotIn("threshold", row)

    def test_missing_component_stops_before_replay_and_output(self):
        (self.folder / "collected/hf-006/checkpoints/component-downstream-006.json").unlink()
        with self.assertRaisesRegex(assembly.IncompleteCut, r"\[6\]"):
            assembly.assemble(self.folder, self.output, "test", self.canonical, {})
        self.assertFalse(self.output.exists())
        self.sampling.assert_not_called()

    def test_cache_never_falls_back_to_fit(self):
        with self.assertRaises(assembly.IncompleteCut):
            assembly.ReadOnlyComponents({})
        cache, _ = assembly.read_complete(self.folder, self.canonical)
        with self.assertRaises(assembly.IncompleteCut):
            cache.load("downstream-008")
        with self.assertRaises(RuntimeError):
            cache.save("anything")
        self.sampling.assert_not_called()

    def test_damaged_archive_is_rejected(self):
        path = self.folder / "collected/hf-006/checkpoints/component-downstream-006.npz"
        path.write_bytes(b"damaged")
        with self.assertRaisesRegex(ValueError, "Damaged component archive"):
            assembly.read_complete(self.folder, self.canonical)

    def test_nonfinite_draws_are_not_silently_removed(self):
        original = collection.validate_assignment
        def damaged(*args):
            record, arrays = original(*args)
            if args[2] == 6:
                arrays["h2"][0] = np.nan
            return record, arrays
        with patch.object(collection, "validate_assignment", side_effect=damaged):
            with self.assertRaisesRegex(ValueError, "Nonfinite contrasts"):
                assembly.read_complete(self.folder, self.canonical)

    def test_register_covariate_axis_cannot_be_lost(self):
        original = collection.verify_component
        def malformed(folder, key):
            result = original(folder, key)
            if key == "upstream" and result is not None:
                manifest, record, arrays = result
                arrays["h"] = arrays["h"][:, :, 0]
                return manifest, record, arrays
            return result
        with patch.object(collection, "verify_component", side_effect=malformed):
            with self.assertRaisesRegex(ValueError, "Invalid selected upstream draws"):
                assembly.read_complete(self.folder, self.canonical)

    def test_publication_retains_failure_and_refuses_overwrite(self):
        result = assembly.assemble(self.folder, self.output, "test", self.canonical, {})
        self.assertEqual(result["independent_datasets"], 1)
        self.assertEqual(result["component_weights"], [1/8]*8)
        self.assertFalse(result["empirical_design_calibration"])
        self.assertEqual(json.loads((self.output / "assembly.json").read_text())["status"], "diagnostic_failure")
        with np.load(self.output / "contrasts.npz", allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved["h2"][6], self.arrays[6]["h2"])
        before = (self.output / "assembly.json").read_bytes()
        with self.assertRaises(FileExistsError):
            assembly.assemble(self.folder, self.output, "test", self.canonical, {})
        self.assertEqual((self.output / "assembly.json").read_bytes(), before)
        self.sampling.assert_not_called()

    def test_wrong_regenerated_data_seed_stops_publication(self):
        with patch.object(d1c, "generate", return_value=({}, self.truths, 999)):
            with self.assertRaisesRegex(ValueError, "dataset seed differs"):
                assembly.assemble(self.folder, self.output, "test", self.canonical, {})
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
