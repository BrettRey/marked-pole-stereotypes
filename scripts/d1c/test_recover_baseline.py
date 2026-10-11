"""Storage-failure regression and bounded recovery checks, without model fits."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import recover_baseline as recovery


class RecoveryTests(unittest.TestCase):
    def test_export_oserror_is_logged_without_interrupting_caller(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            base = Path(directory)
            export = Mock(side_effect=OSError(5, "Input/output error"))
            self.assertFalse(recovery.export_attempt(base, base / "remote", {}, export))
            self.assertIn("retry_export_without_restarting_worker", (base / "export-errors.jsonl").read_text())
            export.side_effect = None
            self.assertTrue(recovery.export_attempt(base, base / "remote", {}, export))
            self.assertEqual(export.call_count, 2)

    def test_non_io_integrity_error_is_not_swallowed(self):
        export = Mock(side_effect=ValueError("wrong checksum"))
        with self.assertRaisesRegex(ValueError, "checksum"):
            recovery.export_attempt(Path("."), Path("."), {}, export)

    def test_final_export_requires_validation_and_retries_only_io(self):
        attempt = Mock(side_effect=[False, True, True])
        validate = Mock(side_effect=[OSError(5, "read failure"), None])
        pause = Mock()
        recovery.finish_export(None, None, {}, validate, timeout=10, pause=pause,
            clock=Mock(side_effect=[0, 1, 2]), attempt=attempt)
        self.assertEqual(attempt.call_count, 3)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(pause.call_count, 2)

    def test_persistent_export_failure_is_bounded(self):
        with self.assertRaises(TimeoutError):
            recovery.finish_export(None, None, {}, Mock(), timeout=1, pause=Mock(),
                clock=Mock(side_effect=[0, 2]), attempt=Mock(return_value=False))

    def test_live_worker_survives_export_failure_and_is_never_relaunched(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            process = Mock(pid=123, returncode=0)
            process.poll.side_effect = [None, None, 0, 0]
            with patch.object(recovery, "verify"), \
                 patch.object(recovery.batch, "BATCH", Path(directory) / "batch"), \
                 patch.object(recovery.subprocess, "Popen", return_value=process) as launch, \
                 patch.object(recovery, "export_attempt", side_effect=[False, True]) as export, \
                 patch.object(recovery, "finish_export") as finish, \
                 patch.object(recovery.batch, "check_module", return_value=({"archive_sha256":"a"*64}, {})), \
                 patch.object(recovery.time, "sleep"), patch.object(recovery.paired, "stop_group") as stop:
                recovery.controller("b"*40, 0)
            self.assertEqual(launch.call_count, 1)
            self.assertEqual(export.call_count, 2)
            finish.assert_called_once()
            stop.assert_not_called()

    def test_only_two_missing_cells_single_attempt_and_budget(self):
        self.assertEqual(recovery.CELLS, (0, 12))
        for cell in recovery.CELLS:
            command = recovery.hf_command("a" * 40, cell)
            self.assertEqual(command[command.index("--attempts") + 1], "1")
            self.assertEqual(command[command.index("--timeout") + 1], "12h")
            self.assertEqual(command[-1], str(cell))
            self.assertNotIn("--secrets", command)
        with self.assertRaises(ValueError):
            recovery.hf_command("a" * 40, 4)
        self.assertAlmostEqual(recovery.TOTAL_RESERVED_USD, 13.80)
        self.assertLess(recovery.TOTAL_RESERVED_USD, 15)


if __name__ == "__main__":
    unittest.main()
