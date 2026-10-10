"""Recover interrupted cuts without changing draws, seeds or failed diagnostics."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import xarray as xr

import d1c
from component_state import ComponentLimitReached, ComponentState


class InterruptedFixture(BaseException):
    pass


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "components"
        self.job = dict(next(cell for cell in d1c.cells() if cell["cell"] == 10), rep=0)
        self.spec = dict(job=self.job, sources={"model": "fixed"}, draws=4000)
        self.calls = []
        self.interrupt_at = None
        self.bad_seed = d1c.seed(4, 10, 0, 0)
        self.truths = {name: -.1 for name in d1c.BENCHMARKS}
        self.addCleanup(patch.stopall)
        patch("d1c.generate", return_value=({}, self.truths, 987)).start()
        patch("d1c.upstream_data", return_value={}).start()
        patch("d1c.downstream_data", return_value={}).start()
        patch("d1c.sample", side_effect=self.sample).start()
        patch("d1c.posterior_contrasts", side_effect=self.contrasts).start()

    def sample(self, job, mode, data, sampling_seed):
        if sampling_seed == self.interrupt_at:
            raise InterruptedFixture()
        self.calls.append((mode, sampling_seed))
        if mode == "upstream":
            rng = np.random.default_rng(sampling_seed)
            posterior = xr.Dataset({name: (("chain", "draw", "item"), rng.normal(size=(4, 32, 5)))
                                    for name in ("z", "v", "s", "h")})
        else:
            posterior = None
        trace = SimpleNamespace(posterior=posterior, data=data, seed=sampling_seed)
        return trace, dict(good=sampling_seed != self.bad_seed, rhat=1.02 if sampling_seed == self.bad_seed else 1.,
                           ess=500., divergences=0, seed=sampling_seed, mode=mode)

    @staticmethod
    def contrasts(trace, observed, fixed, rng):
        # Changes in upstream selection or RNG restoration affect every row.
        offset = sum(float(np.asarray(value).sum()) for value in (fixed or {}).values())
        picks = rng.choice(50, size=16, replace=False)
        values = [dict(h2=offset + pick/1000, h1_fixed_usage=-pick/1000,
                       b_z=(trace.seed % 101)/100, marking=pick/10000) for pick in picks]
        return values, True, 1., 500.

    @staticmethod
    def scientific(result):
        rows, status = result
        return ([{k: v for k, v in row.items() if k != "seconds"} for row in rows],
                {k: v for k, v in status.items() if k != "seconds"})

    def test_cut_restart_preserves_exact_mixture_and_does_not_retry_failed_component(self):
        reference = self.scientific(d1c.fit(self.job))
        self.calls.clear()
        self.interrupt_at = d1c.seed(4, 10, 0, 2)
        with ComponentState(self.path, self.spec) as state:
            with self.assertRaises(InterruptedFixture):
                d1c.fit(self.job, components=state)
            self.assertEqual(list(state.records), ["upstream", "downstream-000", "downstream-001"])
            self.assertFalse(state.records["downstream-000"]["metadata"]["diagnostic"]["good"])
        completed_calls = self.calls.copy()
        self.calls.clear()
        self.interrupt_at = None
        with ComponentState(self.path, self.spec) as state:
            recovered = self.scientific(d1c.fit(self.job, components=state))
        self.assertEqual(recovered, reference)
        self.assertFalse(recovered[1]["status"] == "converged")
        self.assertEqual(len(self.calls), 6)
        self.assertFalse(set(completed_calls) & set(self.calls))
        self.calls.clear()
        with ComponentState(self.path, self.spec) as state:
            self.assertEqual(self.scientific(d1c.fit(self.job, components=state)), reference)
        self.assertEqual(self.calls, [])

    def test_joint_restart_reuses_completed_contrasts(self):
        job = dict(self.job, feedback="joint")
        spec = dict(self.spec, job=job)
        reference = self.scientific(d1c.fit(job))
        with ComponentState(self.path, spec) as state:
            self.assertEqual(self.scientific(d1c.fit(job, components=state)), reference)
        self.calls.clear()
        with ComponentState(self.path, spec) as state:
            self.assertEqual(self.scientific(d1c.fit(job, components=state)), reference)
        self.assertEqual(self.calls, [])

    def test_bounded_benchmark_stops_after_one_component_and_never_reports_full_cut(self):
        for _ in range(2):
            with ComponentState(self.path, self.spec) as state:
                with self.assertRaises(ComponentLimitReached):
                    d1c.fit(self.job, components=state, max_downstream_components=1)
                self.assertEqual(set(state.records), {"upstream", "downstream-000"})
        self.assertEqual(len(self.calls), 2)
        progress = json.loads((self.path / "progress.json").read_text())
        self.assertIn("not a full cut", progress["note"])
        self.assertEqual(progress["components"]["downstream-000"]["summaries"]["h2"]["draws"], 16)

    def test_changed_specification_and_corrupt_archive_are_rejected(self):
        with ComponentState(self.path, self.spec) as state:
            state.save("upstream", {"diagnostic": {"good": True}}, {"z": np.arange(8.)})
        with self.assertRaisesRegex(ValueError, "specification changed"):
            ComponentState(self.path, dict(self.spec, draws=8000))
        archive = self.path / "component-upstream.npz"
        archive.write_bytes(archive.read_bytes() + b"damage")
        with ComponentState(self.path, self.spec) as state:
            with self.assertRaisesRegex(ValueError, "Damaged component archive"):
                state.load("upstream")

    def test_interrupted_commit_marker_is_not_a_completed_component(self):
        with ComponentState(self.path, self.spec) as state:
            state.save("upstream", {}, {"z": np.arange(8.)})
            with patch("component_state.atomic_json", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    state.save("downstream-000", {}, {"h2": np.arange(16.)})
        with ComponentState(self.path, self.spec) as state:
            self.assertIsNone(state.load("downstream-000"))
            self.assertIsNotNone(state.load("upstream"))
            state.save("downstream-000", {}, {"h2": np.arange(16.)})
            with self.assertRaises(FileExistsError):
                state.save("downstream-000", {}, {"h2": np.arange(16.)})

    def test_second_writer_and_modified_record_are_rejected(self):
        with ComponentState(self.path, self.spec) as state:
            with self.assertRaisesRegex(RuntimeError, "Another process"):
                ComponentState(self.path, self.spec)
            state.save("upstream", {"diagnostic": {"good": False}}, {"z": np.arange(8.)})
        path = self.path / "component-upstream.json"
        record = json.loads(path.read_text())
        record["record"]["metadata"]["diagnostic"]["good"] = True
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "Damaged or incompatible"):
            ComponentState(self.path, self.spec)


if __name__ == "__main__":
    unittest.main()
