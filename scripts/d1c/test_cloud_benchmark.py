"""Check export boundaries and stop a worker after failed checkpoint export."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import cloud_benchmark as cloud
from component_state import ComponentState


class CloudTests(unittest.TestCase):
    def test_cleanup_permission_error_requires_confirming_group_has_no_live_members(self):
        from unittest.mock import Mock
        for listing, has_live in (("123 Z\n999 S\n", False), ("123 S\n", True)):
            process = Mock(pid=123)
            with patch.object(cloud.os, "killpg", side_effect=PermissionError), \
                 patch.object(cloud.subprocess, "run", return_value=SimpleNamespace(stdout=listing)):
                if has_live:
                    with self.assertRaises(PermissionError):
                        cloud.stop_group(process)
                else:
                    cloud.stop_group(process)
                    process.wait.assert_called_once()

    def test_supervisor_stops_a_descendant_that_ignores_interrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            heartbeat = Path(tmp) / "child-alive"
            child = "import pathlib,time,signal; signal.signal(signal.SIGINT,signal.SIG_IGN); p=pathlib.Path(" + repr(str(heartbeat)) + ");\nwhile True: p.write_text(str(time.time())); time.sleep(.02)"
            parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(60)"
            def interrupt(pid):
                deadline = time.monotonic() + 5
                while not heartbeat.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(heartbeat.exists())
                raise KeyboardInterrupt()
            with open(os.devnull, "w") as output:
                with self.assertRaises(KeyboardInterrupt):
                    cloud.supervise([sys.executable, "-c", parent], output, interrupt, interval=.01)
            last = heartbeat.read_text()
            time.sleep(.1)
            self.assertEqual(heartbeat.read_text(), last)

    def test_supervisor_stops_worker_when_export_callback_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            heartbeat = Path(tmp) / "alive"
            code = "import pathlib,time; p=pathlib.Path(" + repr(str(heartbeat)) + ");\nwhile True: p.write_text(str(time.time())); time.sleep(.02)"
            pids = []
            def fail(pid):
                pids.append(pid)
                time.sleep(.1)
                raise OSError("export failed")
            with open(os.devnull, "w") as output:
                with self.assertRaisesRegex(OSError, "export failed"):
                    cloud.supervise([sys.executable, "-c", code], output, fail, interval=.01)
            with self.assertRaises(ProcessLookupError):
                os.kill(pids[0], 0)
            last = heartbeat.read_text()
            time.sleep(.1)
            self.assertEqual(heartbeat.read_text(), last)

    def test_export_pushes_only_complete_archives_and_run_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "work"
            remote = Path(tmp) / "remote.git"
            root.mkdir()
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "claude/canary", str(root)], check=True)
            with patch.object(cloud, "ROOT", root):
                cloud.git("config", "user.email", "fixture@example.invalid")
                cloud.git("config", "user.name", "Test fixture")
                cloud.git("remote", "add", "origin", str(remote))
                directory = root / "results/d1c/cloud-canary-20261010"
                checkpoint = directory / "checkpoints"
                with ComponentState(checkpoint, {"job": {"cell": 10, "rep": 0}}) as state:
                    state.save("upstream", {}, {"z": np.arange(8.)})
                    (checkpoint / "component-downstream-000.npz").write_bytes(b"unfinished")
                    (directory / "runtime.json").write_text(json.dumps({"state": "running"}))
                    (directory / "private-unrelated.txt").write_text("exclude me")
                    cloud.export(directory, "claude/canary", "fixture checkpoint")
                files = cloud.git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
                self.assertIn(str((checkpoint / "component-upstream.npz").relative_to(root)), files)
                self.assertFalse(any("downstream" in p or "private" in p or "writer.lock" in p for p in files))
                self.assertEqual(cloud.git("ls-remote", "origin", "refs/heads/claude/canary").split()[0], cloud.git("rev-parse", "HEAD"))
                self.assertEqual(cloud.git("diff", "--cached", "--name-only"), "")
                with self.assertRaisesRegex(RuntimeError, "assigned benchmark branch"):
                    cloud.export(directory, "master", "forbidden")


if __name__ == "__main__":
    unittest.main()
