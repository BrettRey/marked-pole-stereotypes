"""Synthetic software fixtures only; these never enter the research inventory."""
import copy
import unittest

from jsonschema import Draft202012Validator

from production_schema import (PRODUCTION_SCHEMA, prompt_sha256, prompt_text,
                               supplement_requests, validate)


def evidence(sid="fixture:a:1", quote="showing mental care"):
    return {"sense_id": sid, "quote": quote}


def target(status="supported", sid="fixture:a:1", quote="showing mental care"):
    return {"status": status, "respect": "care for people" if status == "supported" else "",
            "restrictions": [], "evidence": [evidence(sid, quote)] if status == "supported" else [],
            "reason": "The quoted sense supports a characteristic." if status == "supported" else "No such target is established."}


def interpretation(iid="i1", sid="fixture:a:1", quote="showing mental care"):
    return {"interpretation_id": iid, "label": "mental care", "sense_ids": [sid],
            "lexical_item_id": "l1", "identity_grouping_id": "", "disposition": "eligible",
            "exclusion_reason": "none", "domain": "personality", "evidence": [evidence(sid, quote)],
            "reason": "Attributes a psychological characteristic to people.",
            "merge_split_rationale": "One interpretation from one source sense.",
            "characteristic_capacity": target(sid=sid, quote=quote),
            "temporary_state": target("not_supported")}


def question(kind="coverage", ids=None):
    return {"question_id": "q1", "kind": kind, "question": "Does an additional relevant reading exist?",
            "needed_evidence": "Usable evidence from the fixed supplement.",
            "sense_ids": [], "interpretation_ids": ids or []}


def fixture():
    packet = {"packet_id": "p1", "stratum": "wordnet_adjective", "items": [{
        "item_id": "f1", "word": "fixture", "dictionary_senses": [
            {"sense_id": "fixture:a:1", "pos": "a", "gloss": "showing mental care"}],
        "coverage": {"wordnet": "present", "supplement": "not_supplied", "supplement_required": False,
                     "review_complete": True, "parser_issues": []}, "sources": []}]}
    result = {"packet_id": "p1", "items": [{
        "item_id": "f1", "word": "fixture", "eligibility_established": True,
        "overall_disposition": "eligible", "exclusion_reason": "none",
        "coverage_review": {"complete": True, "reason": "The required WordNet evidence has been reviewed."},
        "source_senses": [{"sense_id": "fixture:a:1", "disposition": "eligible", "evidence_quote": "showing mental care",
                           "interpretation_ids": ["i1"], "reason": "Supports a psychological interpretation."}],
        "lexical_items": [{"lexical_item_id": "l1", "category": "adjective", "sense_ids": ["fixture:a:1"],
                           "interpretation_ids": ["i1"], "rationale": "One attested adjective sense."}],
        "identity_alternatives": [], "interpretations": [interpretation()], "uncertainties": [],
        "supplement_request": {"requested": False, "reason": "No additional fixed-source evidence is needed."}}]}
    return packet, result


def exclude(row):
    row["eligibility_established"] = False
    row["overall_disposition"] = "outside_frame"
    row["exclusion_reason"] = "psychological_scope"
    row["source_senses"][0]["disposition"] = "excluded"
    interp = row["interpretations"][0]
    interp.update(disposition="excluded", exclusion_reason="physical_only", domain="physical")
    interp["characteristic_capacity"] = target("not_applicable")
    interp["temporary_state"] = target("not_applicable")


class ProductionContractTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.result = fixture()
        self.source = self.packet["items"][0]
        self.row = self.result["items"][0]

    def assert_valid(self):
        self.assertEqual(validate(self.result, self.packet), [])

    def assert_invalid(self, fragment):
        self.assertTrue(any(fragment in error for error in validate(self.result, self.packet)),
                        validate(self.result, self.packet))

    def test_schema_and_prompt(self):
        Draft202012Validator.check_schema(PRODUCTION_SCHEMA)
        self.assertEqual(len(prompt_sha256()), 64)
        self.assertIn("Retain every supported eligible interpretation", prompt_text())
        self.assert_valid()

    def test_eligibility_survives_failed_additional_lookup(self):
        self.source["coverage"].update(supplement="failed", supplement_required=True, review_complete=False)
        self.row["coverage_review"]["complete"] = False
        self.row["uncertainties"] = [question()]
        self.assert_valid()
        self.assertEqual(supplement_requests(self.result, self.packet), set())
        self.row["overall_disposition"] = "unresolved"
        self.assert_invalid("overall disposition")

    def test_eligible_and_excluded_split_is_resolved_eligible_sense(self):
        self.source["dictionary_senses"][0]["gloss"] += "; assigned a duty"
        other = interpretation("i2", quote="assigned a duty")
        other.update(disposition="excluded", exclusion_reason="institutional_status_only", domain="institutional_status")
        other["characteristic_capacity"] = target("not_applicable")
        other["temporary_state"] = target("not_applicable")
        self.row["interpretations"].append(other)
        self.row["source_senses"][0]["interpretation_ids"].append("i2")
        self.row["lexical_items"][0]["interpretation_ids"].append("i2")
        self.assert_valid()
        self.row["source_senses"][0]["disposition"] = "unresolved"
        self.assert_invalid("disposition inconsistent")

    def test_all_physical_is_scope_exclusion_only_after_supplement(self):
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        exclude(self.row)
        self.assert_valid()
        self.row["exclusion_reason"] = "no_adjective_attestation"
        self.assert_invalid("exclusion reason")

    def test_other_categories_only_is_distinct_exclusion(self):
        self.source["dictionary_senses"][0]["pos"] = "n"
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        self.row.update(eligibility_established=False, overall_disposition="outside_frame",
                        exclusion_reason="no_adjective_attestation", source_senses=[], lexical_items=[], interpretations=[])
        self.assert_valid()

    def test_missing_entries_are_not_other_category_attestation(self):
        self.source["dictionary_senses"] = []
        self.source["coverage"].update(wordnet="missing", supplement="missing", supplement_required=True, review_complete=False)
        self.row.update(eligibility_established=False, overall_disposition="unresolved", source_senses=[], lexical_items=[], interpretations=[])
        self.row["coverage_review"]["complete"] = False
        self.row["uncertainties"] = [question()]
        self.assert_valid()
        self.row["coverage_review"]["complete"] = True
        self.assert_invalid("gap cannot be complete")

    def test_no_senses_cannot_mean_outside_frame_even_if_retrieved(self):
        self.source["dictionary_senses"] = []
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        self.row.update(eligibility_established=False, overall_disposition="outside_frame",
                        exclusion_reason="no_adjective_attestation", source_senses=[], lexical_items=[], interpretations=[])
        self.assert_invalid("attested other categories")

    def test_initial_exclusion_requires_new_supplement_request(self):
        exclude(self.row)
        self.row.update(overall_disposition="unresolved", exclusion_reason="none", uncertainties=[question()])
        self.row["coverage_review"]["complete"] = False
        self.row["supplement_request"] = {"requested": True, "reason": "No supported eligible WordNet interpretation."}
        self.assert_valid()
        self.assertEqual(supplement_requests(self.result, self.packet), {"f1"})

    def test_already_supplied_insufficient_is_uncertainty_without_request(self):
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        self.row["interpretations"][0]["characteristic_capacity"] = target("unresolved")
        self.row["uncertainties"] = [question("temporal", ["i1"])]
        self.assert_valid()
        self.assertEqual(supplement_requests(self.result, self.packet), set())
        self.row["supplement_request"]["requested"] = True
        self.assert_invalid("already attempted/supplied")
        self.assertEqual(supplement_requests(self.result, self.packet), set())

    def test_repeated_failed_supplement_request_cannot_create_job(self):
        self.source["coverage"].update(supplement="failed", supplement_required=True)
        self.row["supplement_request"]["requested"] = True
        self.row["uncertainties"] = [question()]
        self.assertEqual(supplement_requests(self.result, self.packet), set())

    def test_parse_issues_leave_coverage_incomplete_but_eligibility_stands(self):
        self.source["coverage"].update(supplement="ambiguous", supplement_required=True,
                                        parser_issues=["Unexpanded template in another sense."])
        self.row["coverage_review"]["complete"] = False
        self.row["uncertainties"] = [question()]
        self.assert_valid()

    def test_each_item_exactly_once(self):
        self.result["items"].append(copy.deepcopy(self.row))
        self.assert_invalid("item accounting mismatch")
        self.assertEqual(supplement_requests(self.result, self.packet), set())
        self.result["items"] = []
        self.assert_invalid("item accounting mismatch")

    def test_every_adjective_sense_exactly_once(self):
        self.row["source_senses"].append(copy.deepcopy(self.row["source_senses"][0]))
        self.assert_invalid("adjective sense accounting mismatch")
        self.row["source_senses"] = []
        self.assert_invalid("adjective sense accounting mismatch")

    def test_each_quote_is_exact_nonempty_substring(self):
        self.row["source_senses"][0]["evidence_quote"] = "mental concern"
        self.assert_invalid("invalid source-sense")
        self.row["source_senses"][0]["evidence_quote"] = ""
        self.assert_invalid("invalid source-sense")

    def test_interpretation_and_target_quotes_also_checked(self):
        self.row["interpretations"][0]["evidence"][0]["quote"] = "invented quote"
        self.assert_invalid("invalid interpretation")
        self.row["interpretations"][0]["characteristic_capacity"]["evidence"][0]["quote"] = "invented target"
        self.assert_invalid("invalid characteristic_capacity")

    def test_cross_item_sense_leak_rejected(self):
        self.row["interpretations"][0]["sense_ids"] = ["other:a:1"]
        self.assert_invalid("invalid interpretation sense references")
        self.assert_invalid("invalid identity link")

    def test_unsupported_fields_rejected(self):
        self.row["commonness"] = 0.9
        self.assert_invalid("Additional properties")

    def test_malformed_typed_value_and_missing_field_rejected(self):
        self.row["eligibility_established"] = "true"
        self.assert_invalid("not of type 'boolean'")
        del self.row["coverage_review"]
        self.assert_invalid("required property")

    def test_unresolved_interpretation_requires_question_and_sense_aggregation(self):
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        self.row["interpretations"][0].update(disposition="unresolved", domain="unresolved")
        self.row["interpretations"][0]["characteristic_capacity"] = target("unresolved")
        self.row["source_senses"][0]["disposition"] = "unresolved"
        self.row.update(eligibility_established=False, overall_disposition="unresolved", uncertainties=[question("interpretation", ["i1"])])
        self.assert_valid()
        self.row["uncertainties"] = []
        self.assert_invalid("lacks an uncertainty")

    def test_identity_alternatives_are_partitions_not_additional_words(self):
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        sid2 = "fixture:a:2"
        self.source["dictionary_senses"].append({"sense_id": sid2, "pos": "s", "gloss": "showing mental care"})
        self.row["source_senses"].append({"sense_id": sid2, "disposition": "eligible", "evidence_quote": "mental care",
                                           "interpretation_ids": ["i2"], "reason": "Supports psychological reading."})
        self.row["interpretations"].append(interpretation("i2", sid2))
        self.row["lexical_items"] = []
        for interp in self.row["interpretations"]:
            interp.update(lexical_item_id="", identity_grouping_id="g1")
        senses = ["fixture:a:1", sid2]
        self.row["identity_alternatives"] = [{"grouping_id": "g1", "interpretation_ids": ["i1", "i2"], "sense_ids": senses,
            "reason": "The sources do not settle adjective-word identity.", "alternatives": [
                {"alternative_id": "a1", "groups": [["i1", "i2"]], "rationale": "One word with two interpretations."},
                {"alternative_id": "a2", "groups": [["i1"], ["i2"]], "rationale": "Two same-spelling words."}]}]
        self.row["uncertainties"] = [question("identity")]
        self.row["uncertainties"][0]["sense_ids"] = senses
        self.row["uncertainties"][0]["interpretation_ids"] = ["i1", "i2"]
        self.assert_valid()
        self.row["identity_alternatives"][0]["alternatives"][1]["groups"] = [["i1"]]
        self.assert_invalid("not a partition")

    def test_one_source_sense_may_support_distinct_lexical_items(self):
        other = interpretation("i2")
        other["lexical_item_id"] = "l2"
        self.row["interpretations"].append(other)
        self.row["source_senses"][0]["interpretation_ids"].append("i2")
        self.row["lexical_items"].append({"lexical_item_id": "l2", "category": "adjective",
            "interpretation_ids": ["i2"], "sense_ids": ["fixture:a:1"],
            "rationale": "Test structural permission for source-sense splitting; substantive support requires review."})
        self.assert_valid()

    def test_unresolved_identity_does_not_force_enumerated_partitions(self):
        self.source["coverage"].update(supplement="retrieved", supplement_required=True)
        self.row["lexical_items"] = []
        self.row["interpretations"][0].update(lexical_item_id="", identity_grouping_id="g1")
        self.row["identity_alternatives"] = [{"grouping_id": "g1", "interpretation_ids": ["i1"],
            "sense_ids": ["fixture:a:1"], "reason": "Identity evidence is insufficient to enumerate alternatives.", "alternatives": []}]
        self.row["uncertainties"] = [question("identity", ["i1"])]
        self.assert_valid()

    def test_characteristic_and_state_both_supported(self):
        self.row["interpretations"][0]["temporary_state"] = target()
        self.assert_valid()

    def test_unknown_item_and_bad_packet_id_do_not_request_supplement(self):
        self.row["supplement_request"]["requested"] = True
        self.row["uncertainties"] = [question()]
        self.row["item_id"] = "invented"
        self.assert_invalid("item accounting mismatch")
        self.assertEqual(supplement_requests(self.result, self.packet), set())
        self.row["item_id"] = "f1"
        self.result["packet_id"] = "different"
        self.assertEqual(supplement_requests(self.result, self.packet), set())

    def test_quote_from_alias_is_not_silent_form_attestation(self):
        self.source["alias_dictionary_senses"] = [{"sense_id": "alias:a:1", "pos": "a", "gloss": "showing mental care"}]
        self.row["interpretations"][0]["evidence"][0]["sense_id"] = "alias:a:1"
        self.assert_invalid("invalid interpretation")


if __name__ == "__main__":
    unittest.main()
