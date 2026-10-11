"""Presentation-only synthetic fixtures; no judge calls or research data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from production_instrument_v11 import (PROMPT_PATH, VERSION, prompt_sha256,
                                       prompt_text, transform_model_packet)
from production_runner import model_packet


def packet(word="alpine"):
    return {"packet_id": "presentation-fixture", "items": [{
        "item_id": "test-item", "word": word,
        "dictionary_senses": [], "alias_dictionary_senses": [],
        "coverage": {"wordnet": "present", "supplement": "not_supplied",
                     "supplement_required": False, "review_complete": True, "parser_issues": []},
        "sources": [{"id": "wordnet-test", "licence": "Test source fact"}],
        "lookup_mappings": {"original_spellings": [word], "alias_is_same_lexical_identity": "not_assessed"},
        "category_evidence": []}]}


def sense(sid, lemmas, gloss="Synthetic dictionary definition.", pos="a"):
    return {"sense_id": sid, "lemmas": lemmas, "gloss": gloss, "pos": pos}


class InstrumentV11Tests(unittest.TestCase):
    def test_removes_only_premature_coverage_flags_and_does_not_mutate_input(self):
        original = packet()
        original["items"][0]["coverage"].update(supplement="ambiguous", parser_issues=["unexpanded source template"])
        original["items"][0]["dictionary_senses"] = [sense("wn31:a:1", ["alpine"])]
        snapshot = deepcopy(original)
        transformed = transform_model_packet(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(transformed["items"][0]["coverage"], {"wordnet": "present", "supplement": "ambiguous",
                                                             "parser_issues": ["unexpanded source template"]})
        transformed["items"][0]["sources"][0]["licence"] = "changed output only"
        transformed["items"][0]["dictionary_senses"][0]["lemmas"].append("changed output only")
        self.assertEqual(original, snapshot)

    def test_mixed_alpine_evidence_preserves_each_relation_and_original_spelling(self):
        original = packet()
        original["items"][0]["dictionary_senses"] = [
            sense("wn31:a:1", ["Alpine", "European"], "Relating to the Alps."),
            sense("wn31:a:2", ["alpine", "mountainous"], "Relating to high mountains."),
            sense("wn31:a:3", ["Alpine", "alpine"], "Fixture with both lemma spellings.")]
        result = transform_model_packet(original)["items"][0]["dictionary_senses"]
        self.assertEqual([s["lookup_relation"]["relation"] for s in result],
                         ["case_only", "exact_case", "exact_case_and_case_only"])
        self.assertEqual(result[0]["lookup_relation"]["case_only_lemmas"], ["Alpine"])
        self.assertEqual(result[1]["lookup_relation"]["exact_case_lemmas"], ["alpine"])
        self.assertEqual(result[2]["lookup_relation"]["exact_case_lemmas"], ["alpine"])
        self.assertEqual(result[2]["lookup_relation"]["case_only_lemmas"], ["Alpine"])
        for before, after in zip(original["items"][0]["dictionary_senses"], result):
            self.assertEqual({k: v for k, v in after.items() if k != "lookup_relation"}, before)
            self.assertEqual(after["lookup_relation"]["lexical_identity"], "not_inferred")

    def test_mosaic_only_adjective_remains_contextual_not_deleted_or_merged(self):
        original = packet("mosaic")
        original["items"][0]["dictionary_senses"] = [
            sense("wn31:a:1", ["Mosaic"], "Of or relating to Moses."),
            sense("wn31:n:2", ["mosaic"], "A patterned picture.", "n")]
        result = transform_model_packet(original)["items"][0]
        self.assertEqual(len(result["dictionary_senses"]), 2)
        self.assertEqual(result["dictionary_senses"][0]["lookup_relation"]["relation"], "case_only")
        self.assertEqual(result["dictionary_senses"][0]["lookup_relation"]["exact_case_lemmas"], [])
        self.assertEqual(result["dictionary_senses"][1]["lookup_relation"]["relation"], "exact_case")
        self.assertEqual(result["word"], "mosaic")
        self.assertEqual(result["lookup_mappings"], original["items"][0]["lookup_mappings"])

    def test_underscore_space_normalization_without_new_casefold_or_hyphen_rules(self):
        original = packet("warm hearted")
        original["items"][0]["dictionary_senses"] = [sense("wn31:a:1", ["warm_hearted", "Warm_hearted"])]
        lookup = transform_model_packet(original)["items"][0]["dictionary_senses"][0]["lookup_relation"]
        self.assertEqual(lookup["relation"], "exact_case_and_case_only")
        self.assertEqual(lookup["exact_case_lemmas"], ["warm_hearted"])
        self.assertEqual(lookup["case_only_lemmas"], ["Warm_hearted"])
        for word, lemma in [("strasse", "Straße"), ("clear-headed", "clear_headed")]:
            original = packet(word)
            original["items"][0]["dictionary_senses"] = [sense("wn31:a:1", [lemma])]
            lookup = transform_model_packet(original)["items"][0]["dictionary_senses"][0]["lookup_relation"]
            self.assertEqual(lookup["relation"], "other_lookup_relation")

    def test_wiktionary_and_other_factual_records_unchanged(self):
        original = packet()
        original["items"][0]["dictionary_senses"] = [sense("enwiktionary:123:1", ["Alpine"], "frequency is part of this exact gloss")]
        original["items"][0]["category_evidence"] = [{"heading": "Adjective", "source_line": 5}]
        original["items"][0]["coverage"]["supplement"] = "retrieved"
        result = transform_model_packet(original)
        for field in ("dictionary_senses", "sources", "category_evidence", "lookup_mappings"):
            self.assertEqual(result["items"][0][field], original["items"][0][field])
        self.assertEqual(result["items"][0]["coverage"]["supplement"], "retrieved")

    def test_inherited_filter_still_hides_strata_ratings_and_other_model_outputs(self):
        original = packet()
        original.update(stratum="hidden-stratum", other_model_outputs={"answer": "hidden-family-answer"})
        original["items"][0].update(stratum="hidden-stratum", ratings=[123], other_model_outputs={"answer": "hidden-family-answer"})
        original["items"][0]["dictionary_senses"] = [sense("wn31:a:1", ["alpine"], "Preserve this source sentence.")]
        original["items"][0]["dictionary_senses"][0]["frequency"] = "hidden-nested-rating"
        result = transform_model_packet(model_packet(original))
        serialized = json.dumps(result)
        for secret in ("hidden-stratum", "hidden-family-answer", "hidden-nested-rating"):
            self.assertNotIn(secret, serialized)
        self.assertIn("Preserve this source sentence.", serialized)

    def test_ids_order_glosses_and_lemma_arrays_preserved_and_idempotent(self):
        original = packet()
        original["items"][0]["dictionary_senses"] = [sense("wn31:a:1", ["Alpine"], "First exact gloss.")]
        second = deepcopy(original["items"][0])
        second.update(item_id="second-test-item", word="Mosaic")
        second["dictionary_senses"] = [sense("wn31:a:2", ["Mosaic"], "Second exact gloss.")]
        original["items"].append(second)
        result = transform_model_packet(original)
        self.assertEqual(result["packet_id"], original["packet_id"])
        self.assertEqual([i["item_id"] for i in result["items"]], [i["item_id"] for i in original["items"]])
        for before, after in zip(original["items"], result["items"]):
            self.assertEqual([(s["sense_id"], s["gloss"], s["lemmas"]) for s in before["dictionary_senses"]],
                             [(s["sense_id"], s["gloss"], s["lemmas"]) for s in after["dictionary_senses"]])
        self.assertEqual(transform_model_packet(result), result)

    def test_prompt_preserves_original_substance_and_adds_required_order_patterns(self):
        original = Path(__file__).with_name("production-word-prompt.txt").read_text()
        successor = prompt_text()
        for paragraph in original.split("\n\n"):
            self.assertIn(paragraph, successor)
        for phrase in ("Decision order: first assess", "Second determine", "Third record",
                       "even when every supplied adjective interpretation is clearly excluded",
                       "retain eligibility_established=true and overall_disposition=eligible",
                       "do not request it again", "not proof that its adjective word is identical"):
            self.assertIn(phrase, successor)
        self.assertEqual(prompt_sha256(), hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest())
        self.assertEqual(VERSION, "lexical-production-20261011-v1.1")


if __name__ == "__main__":
    unittest.main()
