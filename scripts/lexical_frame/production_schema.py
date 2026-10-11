"""Frozen production record contract and deterministic evidence checks.

Passing these checks establishes structural consistency and source-addressable
quotations. It does not establish substantive source support; analyst review of
every scope, identity, grouping and applicability judgment is still required.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_VERSION = "lexical-production-20261011-v1"
PROMPT_PATH = Path(__file__).with_name("production-word-prompt.txt")
VALIDATION_SCOPE = "deterministic structure and evidence references; substantive review required"


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


def enum(*values):
    return {"type": "string", "enum": list(values)}


STR = {"type": "string"}
BOOL = {"type": "boolean"}
PSYCHOLOGICAL_DOMAINS = {"personality", "interpersonal_behaviour", "psychological_state",
                         "psychological_capacity", "psychological_disposition"}
EXCLUSION_REASONS = ("physical_only", "object_only", "membership_only",
                     "institutional_status_only", "record_only", "other_outside_scope")
EVIDENCE = obj({"sense_id": STR, "quote": STR})
APPLICABILITY = obj({
    "status": enum("supported", "not_supported", "unresolved", "not_applicable"),
    "respect": STR, "restrictions": arr(STR), "evidence": arr(EVIDENCE), "reason": STR,
})
INTERPRETATION = obj({
    "interpretation_id": STR, "label": STR, "sense_ids": arr(STR),
    "lexical_item_id": STR, "identity_grouping_id": STR,
    "disposition": enum("eligible", "excluded", "unresolved"),
    "exclusion_reason": enum("none", *EXCLUSION_REASONS),
    "domain": enum("personality", "interpersonal_behaviour", "psychological_state",
                   "psychological_capacity", "psychological_disposition", "physical",
                   "object", "membership", "institutional_status", "record", "other", "unresolved"),
    "evidence": arr(EVIDENCE), "reason": STR, "merge_split_rationale": STR,
    "characteristic_capacity": APPLICABILITY, "temporary_state": APPLICABILITY,
})
SOURCE_SENSE = obj({
    "sense_id": STR, "disposition": enum("eligible", "excluded", "unresolved"),
    "evidence_quote": STR, "interpretation_ids": arr(STR), "reason": STR,
})
LEXICAL_ITEM = obj({
    "lexical_item_id": STR, "category": enum("adjective"),
    "interpretation_ids": arr(STR), "sense_ids": arr(STR), "rationale": STR,
})
IDENTITY_ALTERNATIVE = obj({
    "grouping_id": STR, "interpretation_ids": arr(STR), "sense_ids": arr(STR), "reason": STR,
    "alternatives": arr(obj({"alternative_id": STR, "groups": arr(arr(STR)), "rationale": STR})),
})
UNCERTAINTY = obj({
    "question_id": STR, "kind": enum("category", "interpretation", "identity", "coverage", "temporal", "applicability"),
    "question": STR, "needed_evidence": STR,
    "sense_ids": arr(STR), "interpretation_ids": arr(STR),
})
ITEM = obj({
    "item_id": STR, "word": STR,
    "eligibility_established": BOOL,
    "overall_disposition": enum("eligible", "outside_frame", "unresolved"),
    "exclusion_reason": enum("none", "psychological_scope", "no_adjective_attestation"),
    "coverage_review": obj({"complete": BOOL, "reason": STR}),
    "source_senses": arr(SOURCE_SENSE), "lexical_items": arr(LEXICAL_ITEM),
    "identity_alternatives": arr(IDENTITY_ALTERNATIVE),
    "interpretations": arr(INTERPRETATION), "uncertainties": arr(UNCERTAINTY),
    "supplement_request": obj({"requested": BOOL, "reason": STR}),
})
PRODUCTION_SCHEMA = obj({"packet_id": STR, "items": arr(ITEM)})
_VALIDATOR = Draft202012Validator(PRODUCTION_SCHEMA)


def prompt_text():
    return PROMPT_PATH.read_text(encoding="utf-8")


def prompt_sha256():
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def _adjective(sense):
    return sense.get("pos") in ("a", "s", "adjective", "adjective_satellite")


def validate(result, packet):
    """Return deterministic defects; an empty list is not substantive approval."""
    errors = []
    schema_errors = sorted(_VALIDATOR.iter_errors(result), key=lambda e: str(list(e.absolute_path)))
    for error in schema_errors:
        path = ".".join(map(str, error.absolute_path)) or "result"
        errors.append(f"schema {path}: {error.message}")
    if errors:
        return errors  # Do not interpret malformed records or coerce missing fields.

    if result["packet_id"] != packet["packet_id"]:
        errors.append("packet_id mismatch")
    expected_ids = [item["item_id"] for item in packet["items"]]
    actual_ids = [item["item_id"] for item in result["items"]]
    if len(set(expected_ids)) != len(expected_ids):
        errors.append("input packet has duplicate item IDs")
    if Counter(actual_ids) != Counter(expected_ids):
        errors.append("item accounting mismatch (missing, duplicate or unknown item IDs)")
    inputs = {item["item_id"]: item for item in packet["items"]}

    for row in result["items"]:
        item_id = row["item_id"]
        if item_id not in inputs:
            continue
        source = inputs[item_id]

        def fail(message):
            errors.append(f"{item_id}: {message}")

        def unique_ids(values, label):
            if any(not value.strip() for value in values) or len(values) != len(set(values)):
                fail(f"empty or duplicate {label}")

        def refs(values, allowed, label, nonempty=False):
            unique_ids(values, label)
            if nonempty and not values:
                fail(f"empty {label}")
            if not set(values).issubset(allowed):
                fail(f"unknown or invalid {label}")

        def substantive_text(value, label):
            if not value.strip():
                fail(f"empty {label}")

        if row["word"] != source["word"]:
            fail("word does not match input item ID")
        source_senses = source["dictionary_senses"]
        all_senses = {sense["sense_id"]: sense for sense in source_senses}
        if len(all_senses) != len(source_senses):
            fail("input item has duplicate source sense IDs")
        adjectives = {sid for sid, sense in all_senses.items() if _adjective(sense)}
        sense_ids = [sense["sense_id"] for sense in row["source_senses"]]
        if Counter(sense_ids) != Counter(adjectives):
            fail("adjective sense accounting mismatch")

        def check_evidence(evidence, allowed, label, required=False):
            if required and not evidence:
                fail(f"missing {label} evidence")
            for entry in evidence:
                sid, quote = entry["sense_id"], entry["quote"]
                if sid not in allowed or not quote.strip() or quote not in all_senses.get(sid, {}).get("gloss", ""):
                    fail(f"invalid {label} source reference or exact quote: {sid}")

        for sense in row["source_senses"]:
            check_evidence([{"sense_id": sense["sense_id"], "quote": sense["evidence_quote"]}],
                           adjectives, "source-sense", required=True)
            substantive_text(sense["reason"], "source-sense reason")

        interpretation_ids = [r["interpretation_id"] for r in row["interpretations"]]
        lexical_ids = [r["lexical_item_id"] for r in row["lexical_items"]]
        grouping_ids = [r["grouping_id"] for r in row["identity_alternatives"]]
        unique_ids(interpretation_ids, "interpretation IDs")
        unique_ids(lexical_ids, "lexical item IDs")
        unique_ids(grouping_ids, "identity grouping IDs")
        unique_ids([r["question_id"] for r in row["uncertainties"]], "uncertainty IDs")
        interpretations = {r["interpretation_id"]: r for r in row["interpretations"]}
        lexical_items = {r["lexical_item_id"]: r for r in row["lexical_items"]}
        groupings = {r["grouping_id"]: r for r in row["identity_alternatives"]}

        ownership = []
        for lexical in row["lexical_items"]:
            refs(lexical["sense_ids"], adjectives, "lexical item sense references", nonempty=True)
            refs(lexical["interpretation_ids"], set(interpretation_ids), "lexical item interpretation references", nonempty=True)
            substantive_text(lexical["rationale"], "lexical identity rationale")
            ownership.extend(lexical["interpretation_ids"])
            implied_senses = {sid for iid in lexical["interpretation_ids"] if iid in interpretations
                              for sid in interpretations[iid]["sense_ids"]}
            if set(lexical["sense_ids"]) != implied_senses:
                fail("lexical item sense references differ from its interpretations' supporting senses")
        for grouping in row["identity_alternatives"]:
            refs(grouping["sense_ids"], adjectives, "identity grouping sense references", nonempty=True)
            refs(grouping["interpretation_ids"], set(interpretation_ids), "identity grouping interpretation references", nonempty=True)
            substantive_text(grouping["reason"], "identity grouping reason")
            ownership.extend(grouping["interpretation_ids"])
            implied_senses = {sid for iid in grouping["interpretation_ids"] if iid in interpretations
                              for sid in interpretations[iid]["sense_ids"]}
            if set(grouping["sense_ids"]) != implied_senses:
                fail("identity grouping sense references differ from its interpretations' supporting senses")
            alternatives = grouping["alternatives"]
            unique_ids([r["alternative_id"] for r in alternatives], "alternative IDs within grouping")
            signatures = []
            for alternative in alternatives:
                partition = alternative["groups"]
                flattened = [iid for group in partition for iid in group]
                if not partition or any(not group for group in partition) or Counter(flattened) != Counter(grouping["interpretation_ids"]):
                    fail("identity alternative is not a partition of its grouping's interpretation IDs")
                signatures.append(tuple(sorted(tuple(sorted(group)) for group in partition)))
                substantive_text(alternative["rationale"], "identity alternative rationale")
            if len(set(signatures)) != len(signatures):
                fail("duplicate identity alternative partitions")
        if Counter(ownership) != Counter(interpretation_ids):
            fail("each interpretation must belong to exactly one lexical item or unresolved identity grouping")

        for interpretation in row["interpretations"]:
            iid = interpretation["interpretation_id"]
            ids = interpretation["sense_ids"]
            refs(ids, adjectives, "interpretation sense references", nonempty=True)
            substantive_text(interpretation["label"], "interpretation label")
            substantive_text(interpretation["reason"], "interpretation reason")
            substantive_text(interpretation["merge_split_rationale"], "merge/split rationale")
            check_evidence(interpretation["evidence"], set(ids), "interpretation", required=True)
            if set(ids) != {e["sense_id"] for e in interpretation["evidence"]}:
                fail(f"interpretation {iid} must quote each supporting sense")
            lexical_id = interpretation["lexical_item_id"]
            grouping_id = interpretation["identity_grouping_id"]
            if bool(lexical_id) == bool(grouping_id):
                fail(f"interpretation {iid} needs exactly one lexical item or identity grouping reference")
            owner = lexical_items.get(lexical_id) if lexical_id else groupings.get(grouping_id)
            if owner is None or iid not in owner["interpretation_ids"] or not set(ids).issubset(owner["sense_ids"]):
                fail(f"interpretation {iid} has invalid identity link")
            disposition = interpretation["disposition"]
            if disposition == "eligible" and interpretation["domain"] not in PSYCHOLOGICAL_DOMAINS:
                fail(f"eligible interpretation {iid} lacks a psychological domain")
            if (disposition == "excluded") != (interpretation["exclusion_reason"] != "none"):
                fail(f"interpretation {iid} has inconsistent exclusion reason")
            for target in ("characteristic_capacity", "temporary_state"):
                applicability = interpretation[target]
                status = applicability["status"]
                substantive_text(applicability["reason"], f"{target} reason")
                check_evidence(applicability["evidence"], set(ids), target, required=status == "supported")
                if status == "supported":
                    substantive_text(applicability["respect"], f"{target} respect")
                if disposition == "excluded" and status != "not_applicable":
                    fail(f"excluded interpretation {iid} must have not_applicable temporal targets")
                if disposition != "eligible" and status == "supported":
                    fail(f"noneligible interpretation {iid} cannot have a supported judgment target")
            if disposition == "eligible" and not any(interpretation[t]["status"] in ("supported", "unresolved")
                                                       for t in ("characteristic_capacity", "temporary_state")):
                fail(f"eligible interpretation {iid} has neither a supported nor unresolved temporal target")

        for sense in row["source_senses"]:
            sid = sense["sense_id"]
            ids = sense["interpretation_ids"]
            refs(ids, set(interpretation_ids), "source-sense interpretation references", nonempty=True)
            expected_links = {iid for iid, interpretation in interpretations.items() if sid in interpretation["sense_ids"]}
            if set(ids) != expected_links:
                fail(f"source sense {sid} interpretation links are not reciprocal")
            statuses = {interpretations[iid]["disposition"] for iid in ids if iid in interpretations}
            implied = "eligible" if "eligible" in statuses else ("unresolved" if "unresolved" in statuses else "excluded")
            if sense["disposition"] != implied:
                fail(f"source sense {sid} disposition inconsistent with linked interpretations")

        for uncertainty in row["uncertainties"]:
            refs(uncertainty["sense_ids"], set(all_senses), "uncertainty sense references")
            refs(uncertainty["interpretation_ids"], set(interpretation_ids), "uncertainty interpretation references")
            substantive_text(uncertainty["question"], "unresolved question")
            substantive_text(uncertainty["needed_evidence"], "needed evidence")
        for interpretation in row["interpretations"]:
            needs_question = interpretation["disposition"] == "unresolved" or any(
                interpretation[t]["status"] == "unresolved" for t in ("characteristic_capacity", "temporary_state"))
            if needs_question and not any(interpretation["interpretation_id"] in q["interpretation_ids"] for q in row["uncertainties"]):
                fail(f"unresolved interpretation/target {interpretation['interpretation_id']} lacks an uncertainty record")
        for grouping in row["identity_alternatives"]:
            if not any(q["kind"] == "identity" and set(grouping["interpretation_ids"]).issubset(q["interpretation_ids"])
                       for q in row["uncertainties"]):
                fail("unresolved identity grouping lacks a linked identity uncertainty")

        eligible = any(r["disposition"] == "eligible" for r in row["interpretations"])
        if row["eligibility_established"] != eligible:
            fail("established eligibility inconsistent with supported eligible interpretations")
        complete = row["coverage_review"]["complete"]
        substantive_text(row["coverage_review"]["reason"], "coverage review reason")
        coverage = source["coverage"]
        supplement_status = coverage["supplement"]
        triggered = coverage["supplement_required"] or not eligible or bool(row["uncertainties"])
        supplement_required = coverage["supplement_required"] or triggered
        coverage_gap = ((supplement_required and supplement_status != "retrieved")
                        or bool(coverage.get("parser_issues")))
        if coverage_gap and complete:
            fail("required evidence gap cannot be complete coverage")
        if not complete and not any(q["kind"] == "coverage" for q in row["uncertainties"]):
            fail("incomplete coverage lacks a coverage uncertainty")
        implied = "eligible" if eligible else ("unresolved" if not complete or row["uncertainties"] else "outside_frame")
        if row["overall_disposition"] != implied:
            fail("overall disposition inconsistent with separate eligibility, coverage and uncertainty records")
        expected_exclusion = ("psychological_scope" if adjectives else "no_adjective_attestation") if implied == "outside_frame" else "none"
        if row["exclusion_reason"] != expected_exclusion:
            fail("outside-frame exclusion reason inconsistent with adjective evidence")
        if implied == "outside_frame" and not adjectives and not all_senses:
            fail("no-adjective exclusion needs attested other categories; absent entries leave coverage unresolved")
        if implied == "outside_frame" and not adjectives and any(s.get("pos") in (None, "unknown", "") for s in source_senses):
            fail("unknown category evidence cannot establish no adjective attestation")

        requested = row["supplement_request"]["requested"]
        request_due = triggered and supplement_status == "not_supplied"
        if requested != request_due:
            fail("supplement request inconsistent with trigger or fixed evidence already attempted/supplied")
        if requested:
            substantive_text(row["supplement_request"]["reason"], "supplement request reason")
    return errors


def supplement_requests(result, packet):
    """Return new fixed-source requests only; repeated requests never create jobs.

    The runner must validate the assessment first. This helper is defensive
    against malformed IDs and flags even when called on an invalid assessment.
    Actual evidence change and synchronized two-family dispatch are runner duties.
    """
    if not isinstance(result, dict) or result.get("packet_id") != packet.get("packet_id"):
        return set()
    rows = result.get("items")
    if not isinstance(rows, list):
        return set()
    inputs = {item["item_id"]: item for item in packet["items"]}
    counts = Counter(row.get("item_id") for row in rows if isinstance(row, dict) and isinstance(row.get("item_id"), str))
    requests = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or item_id not in inputs or counts[item_id] != 1:
            continue
        source = inputs[item_id]
        if row.get("word") != source["word"] or source["coverage"]["supplement"] != "not_supplied":
            continue
        request = row.get("supplement_request")
        if not isinstance(request, dict) or request.get("requested") is not True:
            continue
        interpretations = row.get("interpretations")
        uncertainties = row.get("uncertainties")
        if not isinstance(interpretations, list) or not isinstance(uncertainties, list):
            continue
        eligible = any(isinstance(r, dict) and r.get("disposition") == "eligible" for r in interpretations)
        if source["coverage"]["supplement_required"] or not eligible or uncertainties:
            requests.add(item_id)
    return requests
