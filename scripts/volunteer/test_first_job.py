"""Software-only launch/termination checks; no generated observations or model fits."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import first_job as job


class FirstJobTests(unittest.TestCase):
    def run_fixture(self, code, **kwargs):
        directory = Path(self.tmp.name)
        result = job.bounded_run([sys.executable, "-c", code], directory, {},
                                 interval=.02, **kwargs)
        self.assertEqual(result, json.loads((directory / "receipt.json").read_text()))
        return result

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_success(self):
        result = self.run_fixture("print('fixture completed')", measure=lambda pid: 1024)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["worker_exit_code"], 0)
        self.assertIn("fixture completed", (Path(self.tmp.name) / "worker-stdout.txt").read_text())

    def test_worker_failure(self):
        result = self.run_fixture("raise SystemExit(7)", measure=lambda pid: 0)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["worker_exit_code"], 7)

    def test_timeout_terminates_worker(self):
        pids = []
        result = self.run_fixture("import time; time.sleep(10)", max_seconds=.05,
                                  measure=lambda pid: pids.append(pid) or 0)
        self.assertEqual(result["state"], "stopped")
        self.assertIn("TimeoutError", result["stop_reason"])
        with self.assertRaises(ProcessLookupError):
            os.kill(pids[0], 0)

    def test_memory_stop_terminates_worker(self):
        pids = []
        result = self.run_fixture("import time; time.sleep(10)", rss_limit=10,
                                  measure=lambda pid: pids.append(pid) or 11)
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(result["peak_sampled_group_rss_bytes"], 11)
        with self.assertRaises(ProcessLookupError):
            os.kill(pids[0], 0)

    def test_monitor_failure_stops_worker(self):
        pids = []
        def broken(pid):
            pids.append(pid)
            raise OSError("fixture monitor failure")
        result = self.run_fixture("import time; time.sleep(10)", measure=broken)
        self.assertEqual(result["state"], "failed")
        with self.assertRaises(ProcessLookupError):
            os.kill(pids[0], 0)

    def test_archived_science_and_assignment(self):
        spec = job.specification()
        self.assertEqual(spec["job"]["cell"], 12)
        self.assertEqual(spec["job"]["rep"], 0)
        self.assertEqual(spec["seeds"]["fit"], 284053181)
        self.assertFalse(spec["calibration_replicate"])
        self.assertEqual(spec["sampler"]["contrast_draws"], 16000)

    def test_existing_attempt_refused_before_preflight(self):
        from unittest.mock import patch
        with patch.object(job, "DIRECTORY", Path(self.tmp.name)), patch.object(sys, "argv", ["first_job.py"]):
            with self.assertRaises(FileExistsError):
                job.main()


if __name__ == "__main__":
    unittest.main()
