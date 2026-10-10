"""Exercise distribution and cached assembly with fixtures, never model fits."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import d1c
import paired_batch as batch
from component_state import ComponentState
from launch_paired_batch import hf_command
from run_state import atomic_json, digest


class PairedBatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.spec = batch.specification("a"*40, "hf")

    def save(self, base, name, *, bad_seed=False, bad_shape=False):
        info = self.spec["modules"][name]
        upstream = name == "upstream"
        arrays = ({n: np.zeros((8, 400)) for n in ("z", "v", "s")} if upstream else
                  {n: np.linspace(0, 1, 16000) for n in ("h2", "h1_fixed_usage", "b_z", "marking")})
        if upstream:
            arrays["h"] = np.zeros((8, 400) if bad_shape else (8, 400, 3))
        diagnostic = dict(mode=info["mode"],
            seed=(d1c.seed(2, 130, 0) if upstream else d1c.seed(4, 130, 0, info["component"])) + int(bad_seed),
            draws=8000 if upstream else 4000, tune=2000, good=name != "downstream-006",
            contrast_good=True, divergences=0)
        metadata = dict(diagnostic=diagnostic, rng_state=np.random.default_rng(9).bit_generator.state)
        with contextlib.redirect_stdout(io.StringIO()):
            with ComponentState(base / "modules" / name / "checkpoints", batch.module_spec(self.spec, name)) as state:
                state.save(name, metadata, arrays)
                return state.records[name]

    def test_exact_parallel_work_is_disjoint(self):
        groups = [batch.shard_modules(i) for i in range(4)]
        flat = sum(groups, [])
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(set(flat), {f"downstream-{i:03d}" for i in range(8)})
        self.assertEqual(list(batch.assignments("local")), ["joint-004"])
        self.assertEqual(list(batch.assignments("hf-joint")), ["joint-124"])
        self.assertEqual({x["job"]["cell"] for x in batch.assignments("hf").values()}, {130})

    def test_upstream_boundary_stops_actual_fit_before_downstream(self):
        store = unittest.mock.Mock()
        store.load.return_value = None
        latents = {n: np.arange(40*400).reshape(40, 400) for n in ("z", "v", "s")}
        latents["h"] = np.arange(40*400*3).reshape(40, 400, 3)
        with patch.object(d1c, "generate", return_value=({}, {}, 9)), \
             patch.object(d1c, "upstream_data", return_value={}), \
             patch.object(d1c, "downstream_data", return_value={}), \
             patch.object(d1c, "flattened", side_effect=lambda trace, name: latents[name]), \
             patch.object(d1c, "sample", return_value=(object(), {})) as sample:
            with self.assertRaises(batch.UpstreamReady):
                d1c.fit(self.spec["modules"]["upstream"]["job"], components=batch.UpstreamBoundary(store))
        self.assertEqual(sample.call_count, 1)
        self.assertEqual(sample.call_args.args[1], "upstream")
        self.assertEqual(store.save.call_args.args[0], "upstream")
        self.assertEqual(store.save.call_args.args[2]["h"].shape, (8, 400, 3))

    def test_shared_checkpoint_survives_export_and_host_environment_difference(self):
        source, shared, target = self.root / "producer", self.root / "shared", self.root / "receiver"
        record = self.save(source, "upstream")
        exported = shared / "hf-shard-0"
        batch.export_snapshot(source, exported, {})
        atomic_json(exported / "upstream-ready.json", dict(batch_signature=digest(batch.scientific_identity(self.spec)),
            archive_sha256=record["archive_sha256"]))
        spec = dict(self.spec, platform="different host kernel", python="same pinned packages on another host")
        batch.receive_upstream(target, spec, shared, lambda: self.fail("Unexpected wait"))
        received, _ = batch.check_module(target / "modules/upstream", spec, "upstream")
        self.assertEqual(record["archive_sha256"], received["archive_sha256"])

    def test_missing_and_failed_upstream_never_start_a_fit(self):
        shared = self.root / "shared"
        with self.assertRaises(TimeoutError):
            batch.receive_upstream(self.root / "receiver", self.spec, shared, lambda: None, timeout=0)
        (shared / "hf-shard-0").mkdir(parents=True)
        atomic_json(shared / "hf-shard-0/progress.json", dict(state="failed"))
        with self.assertRaisesRegex(RuntimeError, "Upstream host failed"):
            batch.receive_upstream(self.root / "receiver", self.spec, shared, lambda: None)

    def test_foreign_seed_and_lost_register_axis_are_rejected(self):
        for label, name, kwargs in (("seed", "downstream-000", dict(bad_seed=True)),
                                     ("shape", "upstream", dict(bad_shape=True))):
            base = self.root / label
            self.save(base, name, **kwargs)
            with self.assertRaises(ValueError):
                batch.check_module(base / "modules" / name, self.spec, name)

    def test_final_cut_is_cached_and_preserves_failed_diagnostic(self):
        base = self.root / "complete"
        for name in self.spec["modules"]:
            self.save(base, name)
        truths = dict(h2_prevalence_bridge=0., h1_fixed_usage=.1, b_z=-.2, marking=-.03)
        with patch.object(d1c, "generate", return_value=({}, truths, 9)), \
             patch.object(d1c, "upstream_data", return_value={}), \
             patch.object(d1c, "downstream_data", return_value={}), \
             patch.object(d1c, "sample", side_effect=AssertionError("Assembly must never fit")):
            batch.final_results(base, self.spec)
        result = json.loads((base / "results.json").read_text())["results"][0]
        self.assertEqual(result["status"]["status"], "diagnostic_failure")
        self.assertEqual(len(result["status"]["diagnostics"]), 9)
        self.assertEqual(len(result["components"]), 9)
        self.assertNotIn("support", result["rows"][0])
        with np.load(base / "cut-contrasts.npz") as arrays:
            self.assertEqual(arrays["h2"].shape, (8, 16000))
            self.assertAlmostEqual(arrays["h2"].mean(), result["rows"][0]["mean"])

    def test_provider_commands_have_fixed_caps_and_no_secrets_or_retries(self):
        for shard in range(5):
            cmd = hf_command("a"*40, shard, True)
            self.assertEqual(cmd[cmd.index("--timeout")+1], "8h")
            self.assertEqual(cmd[cmd.index("--attempts")+1], "1")
            self.assertNotIn("--secrets", cmd)
            self.assertEqual(cmd[-1], "hf-joint" if shard == 4 else "hf")
            self.assertNotIn("--dry-run", cmd)


if __name__ == "__main__":
    unittest.main()
