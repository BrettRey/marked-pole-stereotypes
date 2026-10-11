"""Software regression fixtures only; these are not substitute Norman observations."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import extract as ex


def block():
    return {"item_no": "12345", "term": "FIXTURE", "rows": {t: ["20", ".50", ".60"] for t in ex.TASKS}}


HEADER = "model: gpt-6.1-sol\nreasoning effort: none\ntokens used\n1,234\n"


class ExtractionTests(unittest.TestCase):
    def test_final_stdout_without_transcript_marker(self):
        rows, meta = ex.parse_x_answer("", json.dumps([block()]), HEADER, 0)
        self.assertEqual(rows, [block()])
        self.assertEqual(meta["tokens"], 1234)

    def test_final_message_file_takes_priority(self):
        rows, _ = ex.parse_x_answer(json.dumps([block()]), "progress only", HEADER, 0)
        self.assertEqual(rows, [block()])

    def test_failed_process_cannot_become_success(self):
        self.assertIsNone(ex.parse_x_answer(json.dumps([block()]), "", HEADER, 1)[0])

    def test_instrument_drift_is_failure(self):
        self.assertIsNone(ex.parse_x_answer(json.dumps([block()]), "", HEADER.replace("none", "high"), 0)[0])

    def test_empty_malformed_and_wrong_shape_fail(self):
        for payload in ("", "[]", "[{}]", "[{", json.dumps([dict(block(), rows={})])):
            with self.subTest(payload=payload):
                self.assertIsNone(ex.parse_x_answer(payload, "", HEADER, 0)[0])

    def test_duplicate_id_fails(self):
        with self.assertRaises(ValueError):
            ex.validate_blocks([block(), block()])

    def test_unreadable_values_remain_null(self):
        b = block()
        b["rows"]["10-WR"] = [None, None, None]
        self.assertEqual(ex.validate_blocks([b]), [b])

    def test_last_success_survives_later_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "attempts.jsonl"
            records = [dict(page=40, side="M", blocks=x) for x in (None, [block()], None)]
            p.write_text("\n".join(json.dumps(r) for r in records))
            self.assertEqual(ex.load_jsonl(p)[(40, "M")]["blocks"], [block()])

    def test_failed_rows_retry_without_repeating_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            ex.append_jsonl(raw / "passX.jsonl", dict(page=40, side="M", blocks=None))
            ex.append_jsonl(raw / "passX.jsonl", dict(page=40, side="F", blocks=[block()]))
            with patch.object(ex, "RAW", raw), patch.object(ex, "render", return_value={"M": raw / "m.png", "F": raw / "f.png"}), \
                    patch.object(ex, "pass_x", return_value=([block()], {})) as call, \
                    patch.object(ex, "_key", side_effect=AssertionError("must not request API key")):
                counts = ex.run_passes([40], 1, passes=("X",))
            self.assertEqual(call.call_count, 1)
            self.assertEqual(counts["X"]["reused"], 1)
            self.assertEqual(len((raw / "passX.jsonl").read_text().splitlines()), 3)

    def test_vision_codex_agreement_is_retained(self):
        rows = ex.reconcile_page(40, "M", None, None, X=[block()], V=[block()])
        self.assertTrue(all(r["source"] == "X=V" for r in rows))

    def test_missing_numbers_never_count_as_agreement(self):
        b = block()
        b["rows"] = {t: [None, None, None] for t in ex.TASKS}
        rows = ex.reconcile_page(40, "M", None, None, X=[b], V=[copy.deepcopy(b)])
        self.assertTrue(all(r["source"] == "flagged" for r in rows))


if __name__ == "__main__":
    unittest.main()
