"""Temporary synthetic software fixtures; never production observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from import_sources import sha
from production_report import assemble, numeric_summary, workload
from production_runner import atomic_json, digest, job_id, read_json
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

    def successor(self):
        original_path = self.root / "frozen-instrument.json"
        original = read_json(original_path)
        successor = dict(original, instrument_version="v1.1", source_commit="successor-test-only",
            parent_instrument_version="v1", parent_instrument_sha256=digest(original),
            parent_instrument_file_sha256=sha(original_path))
        atomic_json(self.root / "frozen-instrument-v1.1.json", successor)
        return successor

    def job(self, packet, family="codex", round_name="initial", status="mechanically_valid", cost=None,
            version=None, elapsed=40):
        jid = job_id(family, packet["packet_id"], round_name)
        directory = self.root / "jobs" / jid
        meta = {"job_id": jid, "family": family,
            "packet_id": packet["packet_id"], "round": round_name, "status": status,
            "packet_sha256": digest(packet), "item_ids": [i["item_id"] for i in packet["items"]],
            "elapsed_seconds": elapsed, "api_equivalent_usd": cost, "usage": {"reported_total_tokens": 1000}}
        if version is not None:
            frozen = read_json(self.root / ("frozen-instrument.json" if version == "v1" else "frozen-instrument-v1.1.json"))
            meta.update(instrument_version=version, instrument_sha256=digest(frozen),
                source_commit=frozen["source_commit"], model_input_sha256=digest(packet))
            atomic_json(directory / "model-input.json", packet)
        atomic_json(directory / "manifest.json", meta)
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
        cost = public["workload_by_instrument_stratum_family_round"]["v1/wordnet_adjective/codex/initial"]["api_equivalent_usd"]
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
        self.assertEqual(route["initial_component_scenarios_by_instrument"]["v1"]["elapsed_seconds_scenario"], 40 / 10 * 3776)
        other = public["continuation_by_stratum"]["category_gap"]["families"]["codex"]
        self.assertIsNone(other["initial_component_scenarios_by_instrument"]["v1"]["elapsed_seconds_scenario"])

    def test_mixed_versions_keep_historical_failures_and_active_initial_costs_separate(self):
        self.successor()
        failed = self.job(self.packets[0], status="failed", cost=9.0, elapsed=90)
        current = self.job(self.packets[1], version="v1.1", cost=1.0, elapsed=10)
        self.review(self.packets[1], [current])
        augmented = copy.deepcopy(self.packets[0])
        augmented["items"][0]["dictionary_senses"][0]["gloss"] += "; augmented"
        atomic_json(self.root / "augmentation" / (augmented["packet_id"] + ".json"),
            {"changed": True, "status": "frozen", "packet": augmented})
        revised = self.job(augmented, round_name="revised", version="v1.1", cost=20.0, elapsed=500)
        self.review(self.packets[0], [failed, revised])
        private, public = assemble(self.root)
        groups = public["workload_by_instrument_stratum_family_round"]
        self.assertEqual(groups["v1/wordnet_adjective/codex/initial"]["api_equivalent_usd"]["observed_mean"], 9)
        self.assertEqual(groups["v1.1/wordnet_adjective/codex/revised"]["api_equivalent_usd"]["observed_mean"], 20)
        route = public["continuation_by_stratum"]["wordnet_adjective"]["families"]["codex"]
        scenarios = route["initial_component_scenarios_by_instrument"]
        self.assertEqual(scenarios["v1.1"]["observed_initial_jobs"], 1)
        self.assertEqual(scenarios["v1.1"]["observed_initial_api_equivalent_usd"]["observed_mean"], 1)
        self.assertEqual(scenarios["v1.1"]["api_equivalent_usd_scenario"], 376.6)
        self.assertEqual(scenarios["v1"]["observed_initial_status_counts"], {"failed": 1})
        self.assertIn("not_an_estimate_for_v1.1", scenarios["v1"]["scenario_role"])
        self.assertEqual(route["current_source_reviewed_usable_forms_by_instrument"], {"v1.1": 20})
        self.assertEqual(route["remaining_without_current_source_reviewed_usable_assessment"], 3766)
        row = private["items"][0]
        self.assertEqual(row["instrument_versions"], ["v1", "v1.1"])
        self.assertEqual(row["source_review"]["reviewed_instrument_versions"], ["v1", "v1.1"])
        self.assertEqual(row["source_review"]["interpretation_reviews"][0]["instrument_version"], "v1.1")
        self.assertEqual(private["job_observations"][failed]["instrument_version_attribution"], "legacy_default_v1")
        self.assertEqual(private["job_observations"][failed]["source_commit"], "synthetic-test-only")
        self.assertFalse(private["job_observations"][failed]["source_commit_recorded"])
        self.assertNotIn("workload_by_stratum_family_round", public)
        self.assertNotIn("private-fixture-word", json.dumps(public))

    def test_mixed_version_workload_cannot_be_averaged(self):
        with self.assertRaisesRegex(ValueError, "cannot pool"):
            workload([{"instrument_version": "v1"}, {"instrument_version": "v1.1"}])

    def test_partial_unknown_measurements_do_not_create_full_scenario(self):
        self.successor()
        self.job(self.packets[0], version="v1.1", cost=1.0)
        self.job(self.packets[1], version="v1.1", cost=None, elapsed=None)
        _, public = assemble(self.root)
        scenario = public["continuation_by_stratum"]["wordnet_adjective"]["families"]["codex"]["initial_component_scenarios_by_instrument"]["v1.1"]
        self.assertIsNone(scenario["api_equivalent_usd_scenario"])
        self.assertIsNone(scenario["elapsed_seconds_scenario"])
        cost = scenario["observed_initial_api_equivalent_usd"]
        self.assertEqual((cost["known_count"], cost["unknown_count"], cost["observed_subtotal"]), (1, 1, 1.0))
        self.assertIsNone(numeric_summary([float("nan"), float("inf")])["observed_subtotal"])

    def test_successor_must_bind_unchanged_parent_and_canonical_population(self):
        successor = self.successor()
        successor["packets"]["p00"] = "changed"
        atomic_json(self.root / "frozen-instrument-v1.1.json", successor)
        with self.assertRaisesRegex(ValueError, "canonical packet population"):
            assemble(self.root)
        self.successor()
        original_path = self.root / "frozen-instrument.json"
        original_path.write_text(original_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "unchanged original frozen record"):
            assemble(self.root)

    def test_reservation_preserves_version_before_manifest_and_is_not_costed_as_dispatch(self):
        self.successor()
        jid = self.job(self.packets[0], version="v1.1", status="failed")
        directory = self.root / "jobs" / jid
        (directory / "manifest.json").rename(directory / "reserved.json")
        private, public = assemble(self.root)
        meta = private["job_observations"][jid]
        self.assertEqual(meta["instrument_version"], "v1.1")
        self.assertEqual(meta["instrument_version_attribution"], "reserved.json")
        self.assertEqual(meta["status"], "reserved")
        self.assertEqual(meta["model_input_verification"], "verified_against_saved_envelope")
        self.assertEqual(public["dispatched_scientific_jobs"], 0)
        route = public["continuation_by_stratum"]["wordnet_adjective"]["families"]["codex"]
        self.assertEqual(route["selected_initial_unattempted"], 90)
        self.assertEqual(route["initial_component_scenarios_by_instrument"]["v1.1"]["observed_initial_jobs"], 0)
        atomic_json(directory / "started.json", {"started_at": "2026-10-11T12:00:00+00:00"})
        private, public = assemble(self.root)
        self.assertEqual(private["job_observations"][jid]["status"], "running_or_interrupted")
        self.assertEqual(public["dispatched_scientific_jobs"], 1)

    def test_job_provenance_conflicts_and_tampered_model_input_are_rejected(self):
        self.successor()
        jid = self.job(self.packets[0], version="v1.1")
        directory = self.root / "jobs" / jid
        atomic_json(directory / "reserved.json", {"instrument_version": "v1"})
        with self.assertRaisesRegex(ValueError, "provenance conflicts"):
            assemble(self.root)
        (directory / "reserved.json").unlink()
        atomic_json(directory / "model-input.json", {"tampered": True})
        with self.assertRaisesRegex(ValueError, "model input hash mismatch"):
            assemble(self.root)

    def test_job_cannot_claim_unregistered_version_or_wrong_source_commit(self):
        jid = self.job(self.packets[0])
        path = self.root / "jobs" / jid / "manifest.json"
        meta = read_json(path)
        meta["instrument_version"] = "v1.1"
        atomic_json(path, meta)
        with self.assertRaisesRegex(ValueError, "unregistered instrument"):
            assemble(self.root)
        self.successor()
        meta["source_commit"] = "wrong-test-commit"
        atomic_json(path, meta)
        with self.assertRaisesRegex(ValueError, "source commit mismatch"):
            assemble(self.root)

    def test_overlapping_reviewer_intervals_are_summed_once_by_exact_version_set(self):
        self.successor()
        packet = self.packets[0]
        v1 = self.job(packet)
        v11 = self.job(packet, family="claude", version="v1.1")
        path, review = self.review(packet, [v1, v11])
        review["reviewer_intervals"] = [
            {"reviewer": "A", "started_at": review["started_at"], "completed_at": review["completed_at"],
             "reviewed_job_ids": [v1, v11]},
            {"reviewer": "B", "started_at": review["started_at"], "completed_at": review["completed_at"],
             "reviewed_job_ids": [v11]}]
        atomic_json(path, review)
        private, public = assemble(self.root)
        timing = public["source_review_timing_by_stratum"]["wordnet_adjective"]
        self.assertEqual(timing["overall_packet_wall_seconds"]["observed_subtotal"], 120)
        self.assertEqual(timing["summed_reviewer_interval_seconds"]["observed_subtotal"], 240)
        groups = timing["reviewer_intervals_by_instrument_version_set"]
        self.assertEqual(set(groups), {"v1+v1.1", "v1.1"})
        self.assertEqual(groups["v1+v1.1"]["elapsed_seconds"]["observed_subtotal"], 120)
        self.assertEqual(private["source_review_timing_by_packet"][packet["packet_id"]]["summed_reviewer_interval_seconds"], 240)

    def test_review_interval_must_reference_real_jobs(self):
        packet = self.packets[0]
        jid = self.job(packet)
        path, review = self.review(packet, [jid])
        review["reviewer_intervals"] = [{"reviewer": "A", "started_at": review["started_at"],
            "completed_at": review["completed_at"], "reviewed_job_ids": ["absent"]}]
        atomic_json(path, review)
        with self.assertRaisesRegex(ValueError, "interval references absent"):
            assemble(self.root)

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
