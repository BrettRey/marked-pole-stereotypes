#!/usr/bin/env python3
"""Counts-only scoring of the already authorized pages 40–41 against the existing gold."""
import hashlib
import json
from datetime import datetime, timezone

import extract as ex


def main():
    gold_path = ex.RAW / "gold_pilot_claude.json"
    raw_gold = json.loads(gold_path.read_text())
    gold = {}
    for page_side, blocks in raw_gold.items():
        page, side = int(page_side[1:4]), page_side[-1]
        if page not in (40, 41):
            raise ValueError("gold contains a page outside the authorized pilot")
        gold.update({(page, side, *key): value[:3] for key, value in ex.rows_of(blocks).items()
                     if None not in value[:3]})
    inputs = {"gold": gold_path}
    engines = {}
    for name in ("A", "B", "X", "V"):
        path = ex.RAW / f"pass{name}.jsonl"
        inputs[name] = path
        rows = ex.load_jsonl(path)
        engines[name] = {}
        for (page, side), row in rows.items():
            if page not in (40, 41):
                continue
            blocks = row.get("blocks")
            if name == "A":
                x = ex.load_jsonl(ex.RAW / "passX.jsonl").get((page, side), {}).get("blocks")
                blocks = ex.align_blocks(blocks, x)
            engines[name].update({(page, side, *key): value[:3] for key, value in ex.rows_of(blocks).items()})
    result = dict(at=datetime.now(timezone.utc).isoformat(), pages=[40, 41],
                  gold_rows=len(gold), excluded_gold_rows=240-len(gold),
                  source_commit=ex.sh(["git", "rev-parse", "HEAD"], cwd=ex.ROOT).strip(),
                  engines={}, agreements={}, input_sha256={})
    for name, rows in engines.items():
        result["engines"][name] = dict(exact=sum(rows.get(key) == value for key, value in gold.items()),
                                       complete=sum(key in gold and None not in value for key, value in rows.items()),
                                       gold_denominator=len(gold))
    for first, second in (("V", "X"), ("V", "A"), ("X", "A"), ("B", "X")):
        left, right = engines[first], engines[second]
        keys = [key for key in gold if key in left and key in right and
                None not in left[key] and left[key] == right[key]]
        correct = sum(left[key] == gold[key] for key in keys)
        result["agreements"][first+"="+second] = dict(rows=len(keys), correct=correct, wrong=len(keys)-correct)
    for name, path in inputs.items():
        if path.exists():
            result["input_sha256"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = ex.ROOT / "logs" / "norman-pilot3-scores-20261011.json"
    target.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
