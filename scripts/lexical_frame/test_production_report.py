"""Temporary synthetic software fixtures; never production observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from production_report import assemble, numeric_summary
from production_runner import atomic_json, digest, job_id
from test_production_schema import fixture


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original, result = fixture()
        self.template = result["items"][0]
        self.packets = []
        for number in range(20):
            packet = copy.deepcopy(original)
            packet["packet_id"] = f"p{number:02}"
            packet["stratum"] = "wordnet_adjective" if number < 10 else "category_gap"
            packet["items"] = []
            for offset in range(10):
                item = copy.deepcopy(original["items"][0])
                item["item_id"] = f"item-{number:02}-{offset:02}"
                item["word"] = "private-fixture-word"
                packet["items"].append(item)
            self.packets.append(packet)
            atomic_json(self.root / "packets" / f"{packet['packet_id']}.json", packet)
        atomic_json(self.root / "frozen-instrument.json", {"source_commit": "synthetic-test-only",
            "packet_order": [p["packet_id"] for p in self.packets],
            "packets": {p["packet_id"]: digest(p) for p in self.packets}})

    def job(self, packet, family="codex", round_name="initial", status="mechanically_valid", cost=None):
        jid = job_id(family, packet["packet_id"], round_name)
        directory = self.root / "jobs" / jid
        atomic_json(directory / "manifest.json", {"job_id": jid, "family": family,
            "packet_id": packet["packet_id"], "round": round_name, "status": status,
            "packet_sha256": digest(packet), "item_ids": [i["item_id"] for i in packet["items"]],
            "elapsed_seconds": 40, "api_equivalent_usd": cost, "usage": {"reported_total_tokens": 1000}})
        if status == "mechanically_valid":
            answer = {"packet_id": packet["packet_id"], "items": []}
            for item in packet["items"]:
                row = copy.deepcopy(self.template)
                row.update(item_id=item["item_id"], word=item["word"])
                answer["items"].append(row)
            atomic_json(directory / "answer.json", answer)
        return jid

    def review(self, packet, jids):
        rows = []
        for item in packet["items"]:
            decisions = [{"job_id": jid, "interpretation_id": "i1", "disposition": "supported",
                "reason": "Synthetic source-support test.", "evidence": [{"sense_id": "fixture:a:1", "quote": "mental care"}],
                "correction": None} for jid in jids if (self.root / "jobs" / jid / "answer.json").exists()]
            rows.append({"item_id": item["item_id"], "reviewed_job_ids": jids, "status": "complete",
                "notes": "Synthetic review includes technical status and all source decisions.",
                "source_decision_reviewed": True, "interpretation_reviews": decisions,
                "unresolved_questions": [], "retains_model_alternatives": True})
        review = {"packet_id": packet["packet_id"], "reviewer": "Test fixture",
            "started_at": "2026-10-11T12:00:00+00:00", "completed_at": "2026-10-11T12:02:00+00:00", "items": rows}
        path = self.root / "source-review" / (packet["packet_id"] + ".json")
        atomic_json(path, review)
        return path, review

    def test_partial_inventory_covers_all_selected_without_public_vocabulary(self):
        private, public = assemble(self.root)
        self.assertEqual(len(private["items"]), 200)
        self.assertFalse(public["final_review_complete"])
        self.assertEqual(public["dispatched_scientific_jobs"], 0)
        self.assertNotIn("private-fixture-word", json.dumps(public))
        route = public["continuation_by_stratum"]["category_gap"]["families"]["codex"]
        self.assertEqual(route["outside_current_batch"], 10196)
        self.assertEqual(route["remaining_without_current_source_reviewed_usable_assessment"], 10296)

    def test_unknown_cost_is_not_zero(self):
        self.job(self.packets[0])
        _, public = assemble(self.root)
        cost = public["workload_by_stratum_family_round"]["wordnet_adjective/codex/initial"]["api_equivalent_usd"]
        self.assertIsNone(cost["total"])
        self.assertIsNone(cost["observed_subtotal"])
        self.assertEqual(cost["unknown_count"], 1)
        self.assertIsNone(numeric_summary([None, 0.0])["total"])

    def test_revision_failure_preserves_initial_record_and_marks_current_missing(self):
        packet = self.packets[0]
        initial = self.job(packet)
        augmented = copy.deepcopy(packet)
        for item in augmented["items"]:
            item["dictionary_senses"][0]["gloss"] += "; also another reading"
            item["coverage"]["supplement"] = "retrieved"
        atomic_json(self.root / "augmentation" / (packet["packet_id"] + ".json"),
                    {"packet_id": packet["packet_id"], "changed": True, "status": "frozen", "packet": augmented})
        revised = self.job(augmented, round_name="revised", status="failed")
        self.review(packet, [initial, revised])
        private, public = assemble(self.root)
        row = private["items"][0]
        family = row["families"]["codex"]
        self.assertEqual(family["retained_usable_job_id"], initial)
        self.assertTrue(family["missing_current_usable_assessment"])
        self.assertTrue(family["assessments"]["initial"]["item_record"]["eligibility_established"])
        self.assertEqual(row["latest_source_coverage"]["supplement"], "retrieved")
        self.assertFalse(public["final_review_complete"])

    def test_stratum_scenario_uses_route_denominator_and_excludes_reviewed_work(self):
        packet = self.packets[0]
        jid = self.job(packet, cost=1.0)
        self.review(packet, [jid])
        _, public = assemble(self.root)
        route = public["continuation_by_stratum"]["wordnet_adjective"]["families"]["codex"]
        self.assertEqual(route["current_source_reviewed_usable_forms"], 10)
        self.assertEqual(route["remaining_without_current_source_reviewed_usable_assessment"], 3776)
        self.assertEqual(route["initial_component_scenario"]["elapsed_seconds_scenario"], 40 / 10 * 3776)
        other = public["continuation_by_stratum"]["category_gap"]["families"]["codex"]
        self.assertIsNone(other["initial_component_scenario"]["elapsed_seconds_scenario"])

    def test_review_requires_real_job_interpretation_and_exact_evidence(self):
        packet = self.packets[0]
        jid = self.job(packet)
        path, review = self.review(packet, [jid])
        review["items"][0]["interpretation_reviews"][0]["evidence"][0]["quote"] = "fabricated source"
        atomic_json(path, review)
        with self.assertRaisesRegex(ValueError, "invalid item-specific evidence"):
            assemble(self.root)

    def test_complete_review_requires_every_usable_interpretation(self):
        packet = self.packets[0]
        jid = self.job(packet)
        path, review = self.review(packet, [jid])
        review["items"][0]["interpretation_reviews"] = []
        atomic_json(path, review)
        with self.assertRaisesRegex(ValueError, "every retained usable interpretation"):
            assemble(self.root)

    def test_full_review_coverage_distinct_from_both_family_completion(self):
        for packet in self.packets:
            jid = self.job(packet)
            self.review(packet, [jid])
        private, public = assemble(self.root)
        self.assertTrue(public["final_review_complete"])
        self.assertEqual(public["source_review_complete_forms"], 200)
        self.assertEqual(public["both_current_assessments_usable_forms"], 0)
        self.assertIsNone(private["items"][0]["adjudicated_disposition"])


if __name__ == "__main__":
    unittest.main()
