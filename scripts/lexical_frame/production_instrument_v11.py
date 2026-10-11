"""Model-facing presentation for lexical production v1.1.

This deliberately leaves the v1 preparation records, schema and validator alone.
The caller first applies the existing runner's model_packet filter; this module
does not read source strata, ratings or any other assessor's output.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path


VERSION = "lexical-production-20261011-v1.1"
PROMPT_PATH = Path(__file__).with_name("production-word-prompt-v1.1.txt")


def prompt_text():
    return PROMPT_PATH.read_text(encoding="utf-8")


def prompt_sha256():
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def _separator_normalized(text):
    # WordNet uses underscores for lexical spaces. Do not add Unicode folding,
    # punctuation stripping, hyphen changes or other new matching assumptions.
    return text.replace("_", " ")


def _lookup_relation(word, lemmas):
    requested = _separator_normalized(word)
    exact, case_only = [], []
    for lemma in lemmas:
        normalized = _separator_normalized(lemma)
        if normalized == requested:
            exact.append(lemma)
        elif normalized.lower() == requested.lower():
            # Match the inherited WordNet reader's lower(), not casefold().
            case_only.append(lemma)
    if exact and case_only:
        relation = "exact_case_and_case_only"
    elif exact:
        relation = "exact_case"
    elif case_only:
        relation = "case_only"
    else:
        # An inherited alias/separator route may have supplied this sense.
        # Preserve it without inventing an exact-case or case-only match.
        relation = "other_lookup_relation"
    return {"relation": relation, "input_form": word,
            "exact_case_lemmas": exact, "case_only_lemmas": case_only,
            "lexical_identity": "not_inferred"}


def transform_model_packet(base_packet):
    """Deep-copy an already-filtered envelope and correct its presentation.

    Omit premature review/requirement flags, preserve source-attempt facts and
    all source text, and annotate original WordNet lemmas' relation to the input.
    A lookup match is retrieval metadata, never a lexical-identity decision.
    """
    packet = deepcopy(base_packet)
    for item in packet["items"]:
        item["coverage"].pop("supplement_required", None)
        item["coverage"].pop("review_complete", None)
        for field in ("dictionary_senses", "alias_dictionary_senses"):
            for sense in item.get(field, []):
                if sense.get("sense_id", "").startswith("wn31:"):
                    sense["lookup_relation"] = _lookup_relation(item["word"], sense.get("lemmas", []))
    return packet
