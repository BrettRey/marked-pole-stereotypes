"""Exercise grid scheduling and reporting with worker fixtures, never fits."""
import json
import os
import tempfile
import time
import unittest
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from unittest.mock import patch

import d1c
import numpy as np
from grid import completed_jobs, publish, specification
from run_state import RunState


def worker_fixture(job):
    if job["rep"] == 1:
        raise ValueError("intentional worker fixture failure")
    return ([dict(**job, good=True, draws=d1c.DRAWS, tune=d1c.TUNE,
                  upstream_draws=d1c.UPSTREAM_DRAWS, contrast_draws=d1c.POST_DRAWS)],
            dict(**job, status="converged", diagnostics=[]))


def crashed_worker_fixture(job):
    os._exit(23)


def slow_worker_fixture(job):
    if job["rep"]:
        time.sleep(20)
    return worker_fixture(job)


class GridTests(unittest.TestCase):
    def test_early_close_terminates_unfinished_workers(self):
        jobs = [dict(cell=0, rep=rep) for rep in range(2)]
        completed = completed_jobs(jobs, 2, 2000, 1000, fit=slow_worker_fixture)
        self.assertEqual(next(completed)[0], jobs[0])
        started = time.perf_counter()
        completed.close()
        self.assertLess(time.perf_counter()-started, 5)

    def test_worker_budgets_and_exception_survive_restart(self):
        jobs = [dict(cell=0, rep=rep) for rep in range(3)]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run"
            spec = dict(jobs=jobs, draws=4000, tune=2000, upstream_draws=8000)
            with RunState(path, spec) as store:
                for job, rows, status in completed_jobs(jobs, 2, 4000, 2000,
                                                        upstream_draws=8000,
                                                        fit=worker_fixture):
                    store.save(job, rows, status)
            with RunState(path, spec, resume=True) as store:
                self.assertEqual(store.pending(), [])
                rows, statuses = store.results()
                self.assertEqual([row["draws"] for row in rows], [4000, 4000])
                self.assertEqual([row["tune"] for row in rows], [2000, 2000])
                self.assertEqual([row["upstream_draws"] for row in rows], [8000, 8000])
                self.assertEqual([row["contrast_draws"] for row in rows], [16000, 16000])
                self.assertEqual([status["status"] for status in statuses],
                                 ["converged", "exception", "converged"])
                self.assertEqual(statuses[1]["fit_seed"], d1c.seed(2, 0, 1))

    def test_dead_worker_does_not_turn_unstarted_jobs_into_exceptions(self):
        jobs = [dict(cell=0, rep=rep) for rep in range(5)]
        completed = []
        with self.assertRaises(BrokenProcessPool):
            for result in completed_jobs(jobs, 1, 2000, 1000,
                                         fit=crashed_worker_fixture):
                completed.append(result)
        self.assertEqual(completed, [])

    def test_grid_covers_original_cells_and_seeds_in_replicate_order(self):
        spec = specification(2, 4000, 2000, 8000)
        original = list(d1c.cells())
        self.assertEqual(spec["jobs"], [dict(cell, rep=rep)
                                       for rep in range(2) for cell in original])
        self.assertEqual(len(spec["jobs"]), 480)
        self.assertEqual(spec["sampler"]["cut_draws"], 8)
        self.assertEqual(spec["sampler"]["upstream_draws"], 8000)
        self.assertEqual(spec["sampler"]["contrast_draws"], 16000)
        self.assertEqual(spec["sampler"]["contrast_diagnostic_draws"], 16000)

    def test_partial_progress_rebuilds_from_completion_record(self):
        spec = specification(1, 2000, 1000)
        job = spec["jobs"][0]
        row = dict(**job, good=True, estimand="test", truth=0., mean=.02,
                   coverage50=True, coverage90=True, width50=.1, width90=.2,
                   error=.02, selected=False, meaningful_truth=False, support=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "logs").mkdir()
            with RunState(root / ".cache/run", spec) as store:
                store.save(job, [row], dict(**job, status="converged",
                                           diagnostics=[dict(rhat=1.0, good=True)]))
                with patch("d1c.ROOT", root):
                    publish(store, "test", [], state="running")
                    # An interrupted aggregate write is repaired from the
                    # saved job; it neither duplicates nor drops the fit.
                    fits = root / "results/d1c/run-test-fits.csv"
                    fits.write_text("interrupted aggregate")
                    publish(store, "test", [], state="running")
                log = json.loads((root / "logs/d1c-grid-test.json").read_text())
                self.assertEqual(log["completed"], 1)
                self.assertEqual(log["pending"], 239)
                self.assertEqual(log["statuses"][0]["diagnostics"][0]["rhat"], 1.0)
                self.assertEqual(len(fits.read_text().splitlines()), 2)

    def test_numpy_scalars_and_nonfinite_failed_diagnostics_are_durable(self):
        job = dict(cell=0, rep=0)
        with tempfile.TemporaryDirectory() as temporary:
            with RunState(Path(temporary) / "run", dict(jobs=[job])) as store:
                store.save(job, [dict(**job, good=np.bool_(False), mean=np.float64(.2))],
                           dict(**job, status="diagnostic_failure",
                                diagnostics=[dict(rhat=np.float64(np.inf))]))
            with RunState(Path(temporary) / "run", dict(jobs=[job]), resume=True) as store:
                rows, statuses = store.results()
                self.assertIs(rows[0]["good"], False)
                self.assertEqual(rows[0]["mean"], .2)
                self.assertIsNone(statuses[0]["diagnostics"][0]["rhat"])
                self.assertEqual(store.pending(), [])


if __name__ == "__main__":
    unittest.main()
