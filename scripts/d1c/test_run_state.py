"""Interruption and provenance tests; these never sample a model."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_state import RunState, atomic_json


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "run"
        self.jobs = [dict(cell=0, rep=rep, design="test") for rep in range(4)]
        self.specification = dict(jobs=self.jobs, source_sha256="original", draws=2000)

    def record(self, store, rep, status):
        job = self.jobs[rep]
        rows = [] if status == "exception" else [dict(
            **job, good=status == "converged", mean=.1, estimand="test")]
        store.save(job, rows, dict(**job, status=status, diagnostics=[dict(rhat=1.0)]))

    def test_restart_skips_successes_failures_and_exceptions(self):
        with RunState(self.path, self.specification) as store:
            self.record(store, 2, "exception")
            self.record(store, 1, "diagnostic_failure")
            self.record(store, 0, "converged")
            before = store.results()
        # A half-written temporary file is not a published completion record.
        (self.path / ".cell-0000-rep-000003.json.partial").write_text("{")
        with RunState(self.path, self.specification, resume=True) as store:
            self.assertEqual(store.pending(), [self.jobs[3]])
            self.assertEqual(store.results(), before)
            self.assertEqual([status["rep"] for status in store.results()[1]], [0, 1, 2])
            with self.assertRaises(FileExistsError):
                self.record(store, 1, "converged")

    def test_new_sampler_source_or_job_specification_cannot_resume(self):
        with RunState(self.path, self.specification):
            pass
        for changed in (dict(draws=4000), dict(source_sha256="changed"),
                        dict(jobs=self.jobs[:-1])):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "changed"):
                RunState(self.path, dict(self.specification, **changed), resume=True)
        with RunState(self.path, self.specification, resume=True):
            pass

    def test_second_writer_is_rejected_without_releasing_first_lock(self):
        with RunState(self.path, self.specification):
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError, "Another process"):
                    RunState(self.path, self.specification, resume=True)
        with RunState(self.path, self.specification, resume=True):
            pass

    def test_interrupted_publish_leaves_prior_file_intact(self):
        self.path.mkdir()
        path = self.path / "aggregate.json"
        atomic_json(path, {"completed": 1})
        with patch("run_state.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                atomic_json(path, {"completed": 2})
        self.assertEqual(json.loads(path.read_text()), {"completed": 1})
        self.assertEqual(list(self.path.iterdir()), [path])

    def test_corrupt_completed_record_is_not_silently_repeated(self):
        with RunState(self.path, self.specification) as store:
            self.record(store, 0, "converged")
        path = next(self.path.glob("cell-*.json"))
        damaged = json.loads(path.read_text())
        damaged["record"]["rows"][0]["mean"] = 9
        path.write_text(json.dumps(damaged))
        with self.assertRaisesRegex(ValueError, "Damaged"):
            RunState(self.path, self.specification, resume=True)

    def test_wrong_job_or_status_is_rejected_before_publishing(self):
        with RunState(self.path, self.specification) as store:
            job = self.jobs[0]
            with self.assertRaisesRegex(ValueError, "identifiers"):
                store.save(job, [dict(**self.jobs[1], good=True)],
                           dict(**job, status="converged"))
            with self.assertRaisesRegex(ValueError, "disagree"):
                store.save(job, [dict(**job, good=False)],
                           dict(**job, status="converged"))
            self.assertEqual(store.pending(), self.jobs)
            self.assertFalse(list(self.path.glob("cell-*.json")))


if __name__ == "__main__":
    unittest.main()
