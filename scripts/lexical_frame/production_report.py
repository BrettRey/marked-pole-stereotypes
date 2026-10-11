"""Compile a private production inventory and public aggregate workload report.

Read-only until explicit CLI output. No retrieval, judge calls, retries or inferred
adjudication. Source reviews are supplied by the analyst, never generated here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from import_sources import published_source, sha
from production_runner import (MODELS, PUBLIC_ROOT, RUN_ROOT, atomic_json, digest,
                               job_id, read_json)
from production_schema import SCHEMA_VERSION, validate


FULL_COUNTS = {"wordnet_adjective": 3786, "category_gap": 10296}
ROUNDS = ("initial", "revised")
TERMINAL_FAILURES = {"failed", "interrupted", "needs_review"}
INSTRUMENT_FILES = {"v1": "frozen-instrument.json", "v1.1": "frozen-instrument-v1.1.json"}
STRATUM_DESCRIPTIONS = {
    "wordnet_adjective": "Original operational route: at least one adjective/adjective-satellite record from the case-insensitive WordNet lookup; not settled lexical identity or eligibility.",
    "category_gap": "Original operational route: no adjective/adjective-satellite record from that case-insensitive WordNet lookup; fixed supplementary lookup required.",
}


def numeric_summary(values):
    """Missing measurements remain unknown rather than becoming zero."""
    known = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)]
    return {"known_count": len(known), "unknown_count": len(values) - len(known),
            "observed_subtotal": sum(known) if known else None,
            "total": sum(known) if known and len(known) == len(values) else None,
            "observed_mean": sum(known) / len(known) if known else None}


def workload(jobs):
    """Summarize one instrument/stratum/family/round, never mixed versions."""
    versions = {job.get("instrument_version", "v1") for job in jobs}
    if len(versions) > 1:
        raise ValueError("Judge workload cannot pool instrument versions")
    dispatched = [job for job in jobs if job.get("dispatch_observed", True)]
    usage_keys = sorted({key for job in dispatched for key, value in (job.get("usage") or {}).items()
                         if isinstance(value, (int, float)) and not isinstance(value, bool)})
    return {"instrument_version": next(iter(versions), None),
            "recorded_job_slots": len(jobs), "dispatched_jobs": len(dispatched),
            "reserved_without_observed_dispatch": len(jobs) - len(dispatched),
            "forms_attempted": sum(job["form_count"] for job in dispatched),
            "forms_reserved_without_observed_dispatch": sum(job["form_count"] for job in jobs if not job.get("dispatch_observed", True)),
            "status_counts": dict(Counter(job["status"] for job in dispatched)),
            "slot_status_counts": dict(Counter(job["status"] for job in jobs)),
            "mechanically_valid_jobs": sum(job["status"] == "mechanically_valid" for job in dispatched),
            "elapsed_seconds": numeric_summary([job.get("elapsed_seconds") for job in dispatched]),
            "api_equivalent_usd": numeric_summary([job.get("api_equivalent_usd") for job in dispatched]),
            "usage": {key: numeric_summary([(job.get("usage") or {}).get(key) for job in dispatched]) for key in usage_keys},
            "jobs_with_any_aggregate_usage": sum(bool(job.get("usage")) for job in dispatched),
            "jobs_with_partial_usage_only": sum(not job.get("usage") and bool(job.get("partial_observed_usage")) for job in dispatched),
            "underlying_request_count": numeric_summary([job.get("underlying_request_count") for job in dispatched]),
            "observed_request_id_count_lower_bound": sum(len(set(job.get("request_ids") or [])) for job in dispatched),
            "observed_assistant_message_count_lower_bound": sum(len(set(job.get("assistant_message_ids") or [])) for job in dispatched),
            "observability_notes": sorted({job.get("internal_request_observability", "Unknown") for job in dispatched}),
            "hidden_retries_and_schema_repairs": "Unknown unless explicitly exposed in saved job metadata."}


def _registered_instruments(root):
    """Verify immutable population provenance before assigning any judge version."""
    root = Path(root)
    original_path = root / INSTRUMENT_FILES["v1"]
    original = read_json(original_path)
    if original is None:
        raise ValueError("A frozen instrument is required before inventory compilation")
    if original.get("instrument_version", "v1") != "v1":
        raise ValueError("The original frozen instrument must retain version v1")
    instruments = {"v1": original}
    successor_path = root / INSTRUMENT_FILES["v1.1"]
    successor = read_json(successor_path)
    if successor is not None:
        if (successor.get("instrument_version") != "v1.1"
                or successor.get("parent_instrument_version") != "v1"
                or successor.get("parent_instrument_sha256") != digest(original)
                or successor.get("parent_instrument_file_sha256") != sha(original_path)):
            raise ValueError("Successor instrument does not bind the unchanged original frozen record")
        if (successor.get("packet_order") != original.get("packet_order")
                or successor.get("packets") != original.get("packets")):
            raise ValueError("Successor instrument changed the canonical packet population or order")
        instruments["v1.1"] = successor
    for version, instrument in instruments.items():
        if not isinstance(instrument.get("source_commit"), str) or not instrument["source_commit"].strip():
            raise ValueError(f"Registered instrument lacks source commit: {version}")
    return instruments


def _read_job(root, packet, round_name, family, instruments=None):
    identifier = job_id(family, packet["packet_id"], round_name)
    directory = root / "jobs" / identifier
    if not directory.exists():
        return None
    instruments = instruments or _registered_instruments(root)
    records = {name: read_json(directory / name) for name in ("reserved.json", "started.json", "manifest.json")}
    bindings = ("job_id", "family", "packet_id", "round", "item_ids", "packet_sha256",
                "instrument_version", "instrument_sha256", "source_commit", "model_input_sha256")
    for key in bindings:
        declared = [record[key] for record in records.values() if record is not None and key in record]
        if declared and any(value != declared[0] for value in declared[1:]):
            raise ValueError(f"Job metadata provenance conflicts: {identifier}/{key}")
    meta = {}
    for record in records.values():
        if record is not None:
            meta.update(record)
    if records["manifest.json"] is None:
        meta["status"] = "running_or_interrupted" if records["started.json"] is not None else "reserved"
    meta["dispatch_observed"] = records["started.json"] is not None or records["manifest.json"] is not None
    for key, expected in (("job_id", identifier), ("family", family), ("packet_id", packet["packet_id"]), ("round", round_name)):
        if key in meta and meta[key] != expected:
            raise ValueError(f"Job metadata identity mismatch: {identifier}/{key}")
        meta[key] = expected
    version = meta["instrument_version"] if "instrument_version" in meta else "v1"
    if version not in instruments:
        raise ValueError(f"Job names an unregistered instrument: {identifier}/{version}")
    instrument = instruments[version]
    expected_instrument_hash = digest(instrument)
    if meta.get("instrument_sha256") is not None and meta["instrument_sha256"] != expected_instrument_hash:
        raise ValueError(f"Job instrument hash mismatch: {identifier}")
    if meta.get("source_commit") is not None and meta["source_commit"] != instrument["source_commit"]:
        raise ValueError(f"Job source commit mismatch: {identifier}")
    meta["instrument_version"] = version
    meta["instrument_version_attribution"] = next((name for name in reversed(records) if records[name] is not None and "instrument_version" in records[name]), "legacy_default_v1")
    meta["source_commit_recorded"] = "source_commit" in meta
    meta["source_commit"] = instrument["source_commit"]
    meta["instrument_sha256_recorded"] = "instrument_sha256" in meta
    meta["registered_instrument_sha256"] = expected_instrument_hash
    model_input_path = directory / "model-input.json"
    if model_input_path.exists():
        actual_model_input_hash = digest(read_json(model_input_path))
        if meta.get("model_input_sha256") is None or meta["model_input_sha256"] != actual_model_input_hash:
            raise ValueError(f"Job model input hash mismatch: {identifier}")
        meta["model_input_verification"] = "verified_against_saved_envelope"
    else:
        meta["model_input_verification"] = "artifact_not_available" if meta.get("model_input_sha256") else "legacy_not_recorded"
    if meta.get("packet_sha256") and meta["packet_sha256"] != digest(packet):
        raise ValueError(f"Job packet hash mismatch: {identifier}")
    expected_ids = [item["item_id"] for item in packet["items"]]
    if "item_ids" in meta and meta["item_ids"] != expected_ids:
        raise ValueError(f"Job input item accounting mismatch: {identifier}")
    meta["form_count"] = len(expected_ids)
    answer_path = directory / "answer.json"
    answer = None
    parse_error = None
    if answer_path.exists():
        try:
            answer = read_json(answer_path)
        except (ValueError, TypeError) as exc:
            parse_error = str(exc)
    errors = validate(answer, packet) if answer is not None else [parse_error or "No parseable answer"]
    if meta["status"] == "mechanically_valid" and errors:
        raise ValueError(f"Previously valid job no longer validates: {identifier}: {errors}")
    return {"meta": meta, "answer": answer, "packet": packet, "validation_errors": errors,
            "manifest_path": str(directory / "manifest.json"),
            "reservation_path": str(directory / "reserved.json") if records["reserved.json"] is not None else None,
            "model_input_path": str(model_input_path) if model_input_path.exists() else None,
            "answer_path": str(answer_path) if answer_path.exists() else None,
            "answer_sha256": sha(answer_path) if answer_path.exists() else None}


def _item_record(job, item_id):
    answer = job["answer"] if job else None
    rows = answer.get("items", []) if isinstance(answer, dict) else []
    matches = [row for row in rows if isinstance(row, dict) and row.get("item_id") == item_id] if isinstance(rows, list) else []
    return matches[0] if len(matches) == 1 else None


def _evidence(entries, job, item_id, required=False):
    if not isinstance(entries, list) or (required and not entries):
        raise ValueError("Review evidence must be a list, nonempty for supported claims/corrections")
    item = next(item for item in job["packet"]["items"] if item["item_id"] == item_id)
    senses = {sense["sense_id"]: sense for sense in item["dictionary_senses"]}
    for entry in entries:
        sid, quote = entry.get("sense_id"), entry.get("quote")
        if sid not in senses or not isinstance(quote, str) or not quote.strip() or quote not in senses[sid]["gloss"]:
            raise ValueError("Review contains an invalid item-specific evidence reference or quotation")


def _review(packet, jobs, path):
    review = read_json(path)
    if review is None:
        return {}, None, None
    if review.get("packet_id") != packet["packet_id"] or not review.get("reviewer", "").strip():
        raise ValueError("Source review needs the matching packet ID and reviewer")
    started = datetime.fromisoformat(review["started_at"].replace("Z", "+00:00"))
    completed_text = review.get("completed_at")
    seconds = None
    if completed_text:
        completed = datetime.fromisoformat(completed_text.replace("Z", "+00:00"))
        if started.tzinfo is None or completed.tzinfo is None or completed < started:
            raise ValueError("Review timing needs ordered timezone-aware timestamps")
        seconds = (completed - started).total_seconds()
    items = review.get("items", [])
    ids = [row["item_id"] for row in items]
    allowed = {row["item_id"] for row in packet["items"]}
    if len(ids) != len(set(ids)) or not set(ids).issubset(allowed):
        raise ValueError("Source-review item accounting mismatch")
    by_id = {}
    for row in items:
        item_id = row["item_id"]
        if row.get("status") not in ("complete", "pending") or not row.get("notes", "").strip():
            raise ValueError("Every source-review item needs complete/pending status and notes")
        reviewed = row.get("reviewed_job_ids", [])
        if len(reviewed) != len(set(reviewed)) or not set(reviewed).issubset(jobs):
            raise ValueError("Source review references an absent or duplicate judge job")
        if not isinstance(row.get("retains_model_alternatives"), bool):
            raise ValueError("Record whether model alternatives are retained")
        if not isinstance(row.get("unresolved_questions"), list) or any(not isinstance(q, str) or not q.strip() for q in row["unresolved_questions"]):
            raise ValueError("Source-review unresolved questions must be explicit strings")
        seen = set()
        for decision in row.get("interpretation_reviews", []):
            jid, iid = decision.get("job_id"), decision.get("interpretation_id")
            if jid not in reviewed:
                raise ValueError("Interpretation review references an unreviewed job")
            record = _item_record(jobs[jid], item_id)
            interpretations = record.get("interpretations", []) if record else []
            if iid not in {i.get("interpretation_id") for i in interpretations if isinstance(i, dict)}:
                raise ValueError("Interpretation review references an absent item interpretation")
            if (jid, iid) in seen:
                raise ValueError("Duplicate interpretation review")
            seen.add((jid, iid))
            if decision.get("disposition") not in ("supported", "qualified", "rejected") or not decision.get("reason", "").strip():
                raise ValueError("Interpretation review needs a disposition and reason")
            _evidence(decision.get("evidence"), jobs[jid], item_id, required=decision["disposition"] != "rejected")
            correction = decision.get("correction")
            if correction is not None:
                if not isinstance(correction, dict) or not correction.get("text", "").strip():
                    raise ValueError("Correction requires a separate explanatory text")
                _evidence(correction.get("evidence"), jobs[jid], item_id, required=True)
        if row["status"] == "complete":
            if seconds is None or row.get("source_decision_reviewed") is not True:
                raise ValueError("Complete review requires finished timing and explicit source-decision review")
            if not jobs or set(reviewed) != set(jobs):
                raise ValueError("Complete review must inspect every dispatched job, including technical failures")
            if any(job["meta"]["status"] in ("running", "running_or_interrupted", "reserved", "pending") for job in jobs.values()):
                raise ValueError("Cannot complete source review while a referenced job remains nonterminal")
            expected = {(jid, interp["interpretation_id"]) for jid, job in jobs.items()
                        if job["meta"]["status"] == "mechanically_valid"
                        for interp in _item_record(job, item_id)["interpretations"]}
            if not expected.issubset(seen):
                raise ValueError("Complete review does not cover every retained usable interpretation")
        compiled = dict(row)
        compiled["reviewed_instrument_versions"] = sorted({jobs[jid]["meta"]["instrument_version"] for jid in reviewed})
        compiled["reviewed_instruments_by_job_id"] = {jid: {
            "instrument_version": jobs[jid]["meta"]["instrument_version"],
            "source_commit": jobs[jid]["meta"]["source_commit"]} for jid in reviewed}
        compiled["interpretation_reviews"] = [dict(decision,
            instrument_version=jobs[decision["job_id"]]["meta"]["instrument_version"],
            source_commit=jobs[decision["job_id"]]["meta"]["source_commit"])
            for decision in row.get("interpretation_reviews", [])]
        by_id[item_id] = compiled
    return by_id, seconds, review


def _reviewed_usable(job, item_id, review):
    if not job or job["meta"]["status"] != "mechanically_valid" or not review or review["status"] != "complete":
        return False
    record = _item_record(job, item_id)
    decisions = [d for d in review["interpretation_reviews"] if d["job_id"] == job["meta"]["job_id"]]
    # A valid outside-category record has no adjective interpretations. A partially
    # supported record retains its supported content without erasing rejected parts.
    return not record["interpretations"] or any(d["disposition"] != "rejected" for d in decisions)


def _review_timing(review, jobs, overall_seconds):
    """Keep packet span distinct from the sum of reported reviewer intervals."""
    if review is None:
        return {"overall_packet_wall_seconds": None,
                "summed_reviewer_interval_seconds": None, "reviewer_intervals": []}
    explicit = "reviewer_intervals" in review
    intervals = review.get("reviewer_intervals") if explicit else [{
        "reviewer": review["reviewer"], "started_at": review["started_at"],
        "completed_at": review.get("completed_at"),
        "reviewed_job_ids": sorted({jid for row in review.get("items", [])
                                    for jid in row.get("reviewed_job_ids", [])})}]
    if not isinstance(intervals, list):
        raise ValueError("Reviewer intervals must be a list")
    compiled = []
    for interval in intervals:
        if not isinstance(interval, dict) or not isinstance(interval.get("reviewer"), str) or not interval["reviewer"].strip():
            raise ValueError("Each reviewer interval needs a reviewer")
        reviewed = interval.get("reviewed_job_ids")
        if (not isinstance(reviewed, list) or len(reviewed) != len(set(reviewed))
                or not set(reviewed).issubset(jobs)):
            raise ValueError("Reviewer interval references absent or duplicate judge jobs")
        started = datetime.fromisoformat(interval["started_at"].replace("Z", "+00:00"))
        completed_text = interval.get("completed_at")
        completed = datetime.fromisoformat(completed_text.replace("Z", "+00:00")) if completed_text else None
        if started.tzinfo is None or (completed is not None and (completed.tzinfo is None or completed < started)):
            raise ValueError("Reviewer intervals need ordered timezone-aware timestamps")
        versions = sorted({jobs[jid]["meta"]["instrument_version"] for jid in reviewed})
        compiled.append(dict(interval, instrument_versions=versions,
            instrument_version_set="+".join(versions) or "unattributed",
            elapsed_seconds=(completed - started).total_seconds() if completed else None,
            timing_origin="explicit_reviewer_interval" if explicit else "legacy_packet_start_end"))
    summary = numeric_summary([interval["elapsed_seconds"] for interval in compiled])
    return {"overall_packet_wall_seconds": overall_seconds,
            "summed_reviewer_interval_seconds": summary["total"], "reviewer_intervals": compiled}


def _review_timing_summary(records):
    groups = {}
    for record in records:
        for interval in record["reviewer_intervals"]:
            groups.setdefault(interval["instrument_version_set"], []).append(interval)
    return {"overall_packet_wall_seconds": numeric_summary([r["overall_packet_wall_seconds"] for r in records]),
            "summed_reviewer_interval_seconds": numeric_summary([r["summed_reviewer_interval_seconds"] for r in records]),
            "reviewer_intervals_by_instrument_version_set": {
                key: {"instrument_versions": intervals[0]["instrument_versions"],
                      "interval_count": len(intervals),
                      "elapsed_seconds": numeric_summary([i["elapsed_seconds"] for i in intervals])}
                for key, intervals in groups.items()}}


def assemble(root=RUN_ROOT):
    """Read frozen files; return (private_inventory, public_aggregate) without writes."""
    root = Path(root).resolve()
    instruments = _registered_instruments(root)
    frozen = instruments["v1"]
    active_version = next(reversed(instruments))
    provenance = {version: {"source_commit": instrument["source_commit"],
                           "instrument_sha256": digest(instrument),
                           "instrument_file_sha256": sha(root / INSTRUMENT_FILES[version])}
                  for version, instrument in instruments.items()}
    packets = [read_json(root / "packets" / (pid + ".json")) for pid in frozen["packet_order"]]
    if any(packet is None for packet in packets):
        raise ValueError("Missing frozen initial evidence packet")
    counts = Counter(packet["stratum"] for packet in packets)
    ids = [item["item_id"] for packet in packets for item in packet["items"]]
    if counts != Counter({"wordnet_adjective": 10, "category_gap": 10}) or any(len(p["items"]) != 10 for p in packets) or len(set(ids)) != 200:
        raise ValueError("The inventory must preserve twenty packets and all 200 unique selected forms")
    if frozen["packets"] != {packet["packet_id"]: digest(packet) for packet in packets}:
        raise ValueError("Frozen initial packet hashes no longer match")
    inventory, all_jobs, groups = [], {}, {}
    review_times = {stratum: [] for stratum in FULL_COUNTS}
    packet_review_times = {}
    for packet in packets:
        pid, stratum = packet["packet_id"], packet["stratum"]
        augmentation = read_json(root / "augmentation" / (pid + ".json"), {})
        latest = augmentation.get("packet", packet)
        if latest["packet_id"] != pid or [i["item_id"] for i in latest["items"]] != [i["item_id"] for i in packet["items"]]:
            raise ValueError("Augmented packet altered selected item identity or order")
        current_round = "revised" if augmentation.get("changed") else "initial"
        jobs = {}
        for family in MODELS:
            for round_name in ROUNDS:
                job = _read_job(root, latest if round_name == "revised" else packet, round_name, family, instruments)
                if job:
                    if round_name == "revised" and not augmentation.get("changed"):
                        raise ValueError("Revised job exists without an actual augmented-evidence round")
                    jid = job["meta"]["job_id"]
                    jobs[jid] = all_jobs[jid] = job
                    groups.setdefault(f"{job['meta']['instrument_version']}/{stratum}/{family}/{round_name}", []).append(job["meta"])
        review_path = root / "source-review" / (pid + ".json")
        reviews, review_seconds, raw_review = _review(packet, jobs, review_path)
        timing = _review_timing(raw_review, jobs, review_seconds)
        review_times[stratum].append(timing)
        if raw_review:
            packet_review_times[pid] = timing
        for original, source in zip(packet["items"], latest["items"]):
            item_id = source["item_id"]
            review = reviews.get(item_id)
            families = {}
            for family in MODELS:
                assessments = {}
                for round_name in ROUNDS:
                    job = jobs.get(job_id(family, pid, round_name))
                    assessments[round_name] = {"status": job["meta"]["status"] if job else "not_dispatched",
                        "job_id": job["meta"]["job_id"] if job else None,
                        "instrument_version": job["meta"]["instrument_version"] if job else None,
                        "source_commit": job["meta"]["source_commit"] if job else None,
                        "registered_instrument_sha256": job["meta"]["registered_instrument_sha256"] if job else None,
                        "instrument_version_attribution": job["meta"]["instrument_version_attribution"] if job else None,
                        "model_input_sha256": job["meta"].get("model_input_sha256") if job else None,
                        "model_input_verification": job["meta"]["model_input_verification"] if job else None,
                        "model_input_path": job["model_input_path"] if job else None,
                        "manifest_path": job["manifest_path"] if job else None,
                        "reservation_path": job["reservation_path"] if job else None,
                        "answer_path": job["answer_path"] if job else None,
                        "answer_sha256": job["answer_sha256"] if job else None,
                        "item_record": _item_record(job, item_id),
                        "source_reviewed_usable": _reviewed_usable(job, item_id, review)}
                usable = [round_name for round_name in ROUNDS if assessments[round_name]["status"] == "mechanically_valid"]
                retained = usable[-1] if usable else None
                current = assessments[current_round]
                families[family] = {"assessments": assessments, "current_evidence_round": current_round,
                    "retained_usable_job_id": assessments[retained]["job_id"] if retained else None,
                    "retained_usable_instrument_version": assessments[retained]["instrument_version"] if retained else None,
                    "current_evidence_instrument_version": current["instrument_version"],
                    "retained_assessment_uses_current_evidence": retained == current_round,
                    "missing_current_usable_assessment": current["status"] != "mechanically_valid",
                    "current_source_reviewed_usable": current["source_reviewed_usable"]}
            inventory.append({"item_id": item_id, "word": source["word"], "packet_id": pid, "stratum": stratum,
                "schema_version": SCHEMA_VERSION,
                "instrument_versions": sorted({job["meta"]["instrument_version"] for job in jobs.values()}),
                "population_source_commit": frozen["source_commit"],
                "initial_source_coverage": original["coverage"], "latest_source_coverage": source["coverage"],
                "latest_source_evidence": source, "augmentation_status": augmentation.get("status", "not_assessed"),
                "families": families, "both_current_assessments_usable": all(not f["missing_current_usable_assessment"] for f in families.values()),
                "source_review": review, "source_review_path": str(review_path) if raw_review else None,
                "source_review_complete": bool(review and review["status"] == "complete"),
                "adjudicated_disposition": None,
                "interpretation_note": "Saved assessments and analyst annotations are retained separately; agreement does not adjudicate."})
    actual_dirs = {p.name for p in (root / "jobs").iterdir() if p.is_dir()} if (root / "jobs").exists() else set()
    if actual_dirs != set(all_jobs):
        raise ValueError("Unexpected job directories outside the frozen packet/family/round inventory")
    aggregated = {key: workload(jobs) for key, jobs in groups.items()}
    continuation = {}
    for stratum, total in FULL_COUNTS.items():
        rows = [row for row in inventory if row["stratum"] == stratum]
        routes = {}
        for family in MODELS:
            complete = sum(row["families"][family]["current_source_reviewed_usable"] for row in rows)
            initial_attempted = sum(row["families"][family]["assessments"]["initial"]["status"] != "not_dispatched" for row in rows)
            initial_not_dispatched = len(rows) - initial_attempted
            terminal_without_current = sum(row["families"][family]["missing_current_usable_assessment"] and
                row["families"][family]["assessments"]["initial"]["status"] in TERMINAL_FAILURES for row in rows)
            unreviewed = sum(not row["source_review_complete"] for row in rows)
            remaining = total - complete
            new_initial_forms = total - len(rows) + initial_not_dispatched
            completed_by_version = Counter(row["families"][family]["current_evidence_instrument_version"]
                for row in rows if row["families"][family]["current_source_reviewed_usable"])
            projections = {}
            for version in instruments:
                observed = aggregated.get(f"{version}/{stratum}/{family}/initial", workload([]))
                projection = {"instrument_version": version, "source_commit": instruments[version]["source_commit"],
                    "scenario_role": "active_instrument_initial_only" if version == active_version else "historical_instrument_only_not_an_estimate_for_" + active_version,
                    "new_initial_forms": new_initial_forms, "per_form_divisor": 10,
                    "elapsed_seconds_scenario": None, "api_equivalent_usd_scenario": None,
                    "observed_initial_jobs": observed["dispatched_jobs"],
                    "observed_initial_forms_attempted": observed["forms_attempted"],
                    "observed_initial_status_counts": observed["status_counts"],
                    "observed_initial_elapsed_seconds": observed["elapsed_seconds"],
                    "observed_initial_api_equivalent_usd": observed["api_equivalent_usd"]}
                for metric, key in (("elapsed_seconds", "elapsed_seconds_scenario"), ("api_equivalent_usd", "api_equivalent_usd_scenario")):
                    summary = observed[metric]
                    # Failed dispatches stay in their own version's denominator;
                    # unknown costs never become zero or a full continuation quote.
                    if summary["unknown_count"] == 0 and summary["observed_mean"] is not None:
                        projection[key] = summary["observed_mean"] / 10 * new_initial_forms
                projections[version] = projection
            routes[family] = {"current_source_reviewed_usable_forms": complete,
                "current_source_reviewed_usable_forms_by_instrument": dict(completed_by_version),
                "remaining_without_current_source_reviewed_usable_assessment": remaining,
                "selected_initial_unattempted": initial_not_dispatched,
                "selected_initial_terminal_failures_without_current_usable": terminal_without_current,
                "selected_source_review_pending": unreviewed,
                "selected_missing_current_usable": sum(row["families"][family]["missing_current_usable_assessment"] for row in rows),
                "outside_current_batch": total - len(rows), "initial_component_scenarios_by_instrument": projections}
        continuation[stratum] = {"full_inventory_forms": total, "selected_forms": len(rows),
            "stratum_description": STRATUM_DESCRIPTIONS[stratum], "families": routes}
    stamp = datetime.now(timezone.utc).isoformat()
    shared = {"generated_at": stamp, "schema_version": SCHEMA_VERSION,
              "active_instrument_version": active_version, "registered_instruments": provenance,
              "observed_instrument_versions": sorted({job["meta"]["instrument_version"] for job in all_jobs.values()}),
              "population_source_commit": frozen["source_commit"], "population_instrument_sha256": digest(frozen),
              "stratum_descriptions": STRATUM_DESCRIPTIONS, "selected_forms": 200}
    private = {**shared, "items": inventory, "source_review_timing_by_packet": packet_review_times,
               "job_observations": {jid: job["meta"] for jid, job in all_jobs.items()}}
    public = {**shared, "source_review_complete_forms": sum(row["source_review_complete"] for row in inventory),
        "final_review_complete": all(row["source_review_complete"] for row in inventory),
        "both_current_assessments_usable_forms": sum(row["both_current_assessments_usable"] for row in inventory),
        "dispatched_scientific_jobs": sum(job["meta"]["dispatch_observed"] for job in all_jobs.values()),
        "recorded_scientific_job_slots": len(all_jobs), "scientific_job_limit": 80,
        "workload_by_instrument_stratum_family_round": aggregated,
        "source_review_timing_by_stratum": {s: _review_timing_summary(times) for s, times in review_times.items()},
        "continuation_by_stratum": continuation,
        "continuation_caveats": ["Initial-component figures are arithmetic scenarios, not a whole-project quote or allowance estimate.",
            "Workload and initial-component scenarios are separate by instrument version, operational stratum, model route and round. Historical v1 failures remain visible and are not estimates for corrected v1.1.",
            "New-initial scenarios include outside-batch forms and selected unattempted forms. Previously reserved slots, dispatched failures and missing revised assessments require separate decisions; no automatic retry is proposed.",
            "Remaining current-assessment counts exclude source-reviewed usable work on the current evidence across both registered versions, with completed counts shown by version; unresolved meanings can remain valid results.",
            "The old 40-form pilot is a different instrument and is not deducted as completed current-instrument coding.",
            "Revised-evidence coding, supplementary retrieval, further substantive review, independent pair discovery, rejected/unmatched audits, alignment, adjudication and weighting costs remain separately unestimated.",
            "Review timing separates overall packet start/end spans from summed reported reviewer intervals. Overlapping reviewers can make the sum exceed the span; each interval is attributed once to its exact set of instrument versions.",
            "Reported reviewer intervals are model-assisted review wall times, not separately metered model-token usage or human-only effort. Root integration overhead is unmetered unless explicitly logged."]}
    return private, public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=RUN_ROOT)
    parser.add_argument("--public-root", type=Path, default=PUBLIC_ROOT)
    parser.add_argument("--write", action="store_true", help="Write inventory.json and aggregate-report.json after the publication guard")
    args = parser.parse_args()
    if args.write:
        published_source()
    private, public = assemble(args.root)
    if args.write:
        atomic_json(args.root / "inventory.json", private)
        atomic_json(args.public_root / "aggregate-report.json", public)
    print(json.dumps(public, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
