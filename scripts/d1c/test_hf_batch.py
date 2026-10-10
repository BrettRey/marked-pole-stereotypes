"""Check assignment dispatch and real-process supervisor replacement."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from hf_batch import dispatch
from local_queue import process_info, retire_supervisor
from run_component import ASSIGNMENTS


class BatchTests(unittest.TestCase):
    def test_assignments_are_disjoint_and_cover_the_cut(self):
        self.assertFalse(ASSIGNMENTS["local"] & ASSIGNMENTS["hf"])
        self.assertEqual({0} | ASSIGNMENTS["local"] | ASSIGNMENTS["hf"], set(range(8)))

    def test_two_slots_and_no_repeat_after_completion(self):
        launched, snapshots, counts = [], [], {}
        def launch(component):
            launched.append(component)
            counts[component] = 0
            return component
        def poll(worker):
            counts[worker] += 1
            return 0 if counts[worker] >= (2 if worker == 4 else 3) else None
        result = dispatch((4, 5, 6), launch, poll, lambda c: True,
            lambda pending, active, done, failed: snapshots.append(tuple(active)), lambda: None)
        self.assertEqual(launched, [4, 5, 6])
        self.assertEqual(set(result), {4, 5, 6})
        self.assertLessEqual(max(map(len, snapshots)), 2)
        self.assertIn((5, 6), snapshots)

    def test_execution_failure_stops_dispatch_but_finishes_running_peer(self):
        launched, finished = [], []
        def launch(c):
            launched.append(c)
            return c
        def poll(c):
            finished.append(c)
            return 1 if c == 4 else 0
        with self.assertRaisesRegex(RuntimeError, "no retry"):
            dispatch((4, 5, 6), launch, poll, lambda c: True,
                     lambda *args: None, lambda: None)
        self.assertEqual(launched, [4, 5])
        self.assertEqual(finished, [4, 5])

    def test_supervisor_replacement_preserves_independent_heartbeat_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child_script = root / "heartbeat_worker.py"
            child_script.write_text("import pathlib, sys, time\np=pathlib.Path(sys.argv[1])\n"
                "while True:\n p.write_text(str(time.monotonic_ns()))\n time.sleep(.02)\n")
            parent_script = root / "fixture_supervisor.py"
            parent_script.write_text("import subprocess, sys, pathlib, time\n"
                "p=subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], start_new_session=True)\n"
                "pathlib.Path(sys.argv[3]).write_text(str(p.pid))\n"
                "while True: time.sleep(.05)\n")
            beat, pidfile = root / "beat", root / "pid"
            parent = subprocess.Popen([sys.executable, str(parent_script), str(child_script),
                                       str(beat), str(pidfile)], start_new_session=True)
            child = None
            try:
                deadline = time.monotonic() + 10
                while not beat.exists():
                    if time.monotonic() > deadline:
                        self.fail("Heartbeat fixture did not start")
                    time.sleep(.02)
                child = int(pidfile.read_text())
                with self.assertRaisesRegex(RuntimeError, "refusing handoff"):
                    retire_supervisor(parent.pid, child, "incorrect parent", str(child_script))
                first = beat.read_text()
                receipt = retire_supervisor(parent.pid, child, str(parent_script), str(child_script))
                parent.wait(timeout=5)
                time.sleep(.1)
                self.assertNotEqual(first, beat.read_text())
                self.assertEqual(receipt["adopted_worker_pid"], child)
                self.assertIsNotNone(process_info(child))
                self.assertIsNone(process_info(parent.pid))
            finally:
                if parent.poll() is None:
                    os.kill(parent.pid, signal.SIGKILL)
                    parent.wait()
                if child and process_info(child):
                    os.kill(child, signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
