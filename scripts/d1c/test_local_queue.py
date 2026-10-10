"""Queue policy: advance after failed diagnostics, never retry or duplicate."""
import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from local_queue import advance
import run_component


class QueueTests(unittest.TestCase):
    def test_source_freeze_allows_result_commits_but_rejects_source_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "work"
            root.mkdir()
            remote = Path(tmp) / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
            with patch.object(run_component.d1c, "ROOT", root):
                git = run_component.git
                git("config", "user.email", "fixture@example.invalid")
                git("config", "user.name", "Test fixture")
                git("remote", "add", "origin", str(remote))
                (root / "script.py").write_text("original source\n")
                git("add", "script.py")
                git("commit", "-m", "source")
                source = git("rev-parse", "HEAD")
                (root / "result.json").write_text("{}\n")
                git("add", "result.json")
                git("commit", "-m", "result only")
                git("push", "origin", "master")
                run_component.verify_published_source(source, ["script.py"])
                (root / "script.py").write_text("changed source\n")
                with self.assertRaisesRegex(RuntimeError, "Commit the exact source"):
                    run_component.verify_published_source(source, ["script.py"])
                git("add", "script.py")
                git("commit", "-m", "changed source")
                with self.assertRaises(subprocess.CalledProcessError):
                    run_component.verify_published_source(source, ["script.py"])

    def test_completed_failure_is_skipped_and_next_components_run_once(self):
        saved = {3: {"diagnostics_pass": False}}
        executed = []
        def execute(component):
            executed.append(component)
            saved[component] = {"diagnostics_pass": component != 4}
            return 0
        advance((3, 4, 5, 6, 7), lambda component: component in saved, execute)
        self.assertEqual(executed, [4, 5, 6, 7])
        advance((3, 4, 5, 6, 7), lambda component: component in saved, execute)
        self.assertEqual(executed, [4, 5, 6, 7])

    def test_execution_error_stops_without_retry_or_unrecorded_success(self):
        executed = []
        def failed(component):
            executed.append(component)
            return 1
        with self.assertRaisesRegex(RuntimeError, "no automatic retry"):
            advance((3, 4), lambda component: False, failed)
        self.assertEqual(executed, [3])
        with self.assertRaisesRegex(RuntimeError, "without a valid saved result"):
            advance((3, 4), lambda component: False, lambda component: 0)


if __name__ == "__main__":
    unittest.main()
