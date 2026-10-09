#!/usr/bin/env python3
"""Transcribe Norman (1967), ERIC ED014738, Appendices 1-14 (spec: scripts/norman/README.md).

Transcription only. Outside `pilot`, values are never printed: summaries report counts.

    python3 scripts/norman/extract.py pages                 # list table pages and separators
    python3 scripts/norman/extract.py pilot --pages 40,41   # all passes on pages free of negated terms
    python3 scripts/norman/extract.py run --workers 6       # render, pass A, pass B on all table pages
    python3 scripts/norman/extract.py passC                 # local model on pages with disagreements
    python3 scripts/norman/extract.py reconcile             # merge, range checks, summary counts
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "norman1967"
PDF = RAW / "norman_1967_2800_personality_trait_descriptors_ERIC_ED014738.pdf"
IMG = RAW / "img"
TASKS = ("10-WR", "DP-S", "DP-A", "DP-B", "DP-C")
DPI = 300
NEG = re.compile(r"^(UN|IN|IM|IL|IR|DIS|NON)|LESS$")
MODEL_B = "z-ai/glm-5.3-flash"
MODEL_C = "gemma3:12b"

PROMPT = (
    "This image is half of a scanned page of statistical tables from a 1967 report. It contains several "
    "blocks. Each block begins with a line 'ITEM NO. <five-digit number> , <TERM>'. Below it is a table "
    "whose rows are labelled 10-WR, DP-S, DP-A, DP-B, DP-C (the scan may misprint these labels). Each row "
    "ends with three numbers under the column headings N, MEAN, S.D. Transcribe, for every block on the "
    "image, the item number, the term exactly as printed, and for each of the five rows its final three "
    "numbers N, MEAN, S.D. exactly as printed. MEAN and S.D. are printed with two decimals, often without "
    "a leading zero (for example .56); copy them as printed. Ignore the correlation coefficients, the "
    "upper-triangle counts, and any handwritten underlining. Output only JSON, no commentary: a list of "
    'objects {"item_no": "...", "term": "...", "rows": {"10-WR": ["N","MEAN","SD"], "DP-S": [...], '
    '"DP-A": [...], "DP-B": [...], "DP-C": [...]}}, using strings exactly as printed and null for '
    "anything you cannot read."
)
PROMPT_SHA = hashlib.sha256(PROMPT.encode()).hexdigest()


def sh(cmd: list[str], **kw) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


# ------------------------------------------------------------------ pages and rendering

def table_pages() -> list[int]:
    out = []
    for p in range(35, 286):
        t = sh(["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(PDF), "-"])
        if len(re.findall(r"ITEM\s*N", t)) >= 1:
            out.append(p)
    return out


def page_size_px(p: int) -> tuple[int, int]:
    info = sh(["pdfinfo", "-f", str(p), "-l", str(p), str(PDF)])
    m = re.search(r"Page\s+%d size:\s+([\d.]+) x ([\d.]+) pts" % p, info) or re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    w, h = float(m.group(1)), float(m.group(2))
    return int(w * DPI / 72), int(h * DPI / 72)


def render(p: int) -> dict:
    IMG.mkdir(parents=True, exist_ok=True)
    w, h = page_size_px(p)
    halves = {"M": (0, int(w * 0.53)), "F": (int(w * 0.47), w - int(w * 0.47))}
    paths = {}
    for side, (x, W) in halves.items():
        stem = IMG / f"p{p:03d}_{side}"
        png = stem.with_suffix(".png")
        if not png.exists():
            sh(["pdftoppm", "-f", str(p), "-l", str(p), "-r", str(DPI), "-gray", "-png", "-singlefile",
                "-x", str(x), "-y", "0", "-W", str(W), "-H", str(h), str(PDF), str(stem)])
        paths[side] = png
    return paths


# ------------------------------------------------------------------ pass A: Tesseract

NUM = re.compile(r"-?\d*\.\d+|-?\d+")


def parse_tesseract(text: str) -> list[dict]:
    """Blocks start at an ITEM NO. line; the next five lines with at least three numbers are the task
    rows in order, and the last three numbers of each are N, MEAN, S.D."""
    blocks, cur = [], None
    for line in text.splitlines():
        if re.search(r"ITEM\W{0,3}N[O0U]", line, re.I):
            m = re.search(r"(\d{5})\W*([A-Z][A-Z' \-]+)", line.upper())
            cur = dict(item_no=m.group(1) if m else None, term=(m.group(2).strip() if m else None), rows=[])
            blocks.append(cur)
            continue
        if cur is None or re.search(r"TASK|MEAN|S\.?D", line, re.I) and len(NUM.findall(line)) < 3:
            continue
        nums = NUM.findall(line)
        if len(nums) >= 3 and len(cur["rows"]) < 5:
            cur["rows"].append(nums[-3:])
    out = []
    for b in blocks:
        rows = {t: (b["rows"][i] if i < len(b["rows"]) else None) for i, t in enumerate(TASKS)}
        out.append(dict(item_no=b["item_no"], term=b["term"], rows=rows))
    return out


def pass_a(p: int, side: str, png: Path) -> list[dict]:
    text = sh(["tesseract", str(png), "-", "--psm", "6", "-c", "preserve_interword_spaces=1"])
    return parse_tesseract(text)


# ------------------------------------------------------------------ passes B and C: vision models

def _key() -> str:
    try:
        return subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                               "-s", "ox-alpha", "-w"], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _json_list(reply: str):
    reply = reply.strip()
    reply = re.sub(r"^```(?:json)?|```$", "", reply, flags=re.M).strip()
    i, j = reply.find("["), reply.rfind("]")
    return json.loads(reply[i:j + 1]) if i >= 0 and j > i else None


def pass_b(png: Path, key: str, retries: int = 2) -> tuple[list | None, dict]:
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = dict(model=MODEL_B, temperature=0, max_tokens=6000,
                messages=[dict(role="user", content=[dict(type="text", text=PROMPT),
                                                     dict(type="image_url", image_url=dict(url=f"data:image/png;base64,{b64}"))])])
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            reply = d["choices"][0]["message"]["content"]
            return _json_list(reply), dict(model=d.get("model"), usage=d.get("usage"))
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as e:  # noqa: PERF203
            err = repr(e)[:300]
            time.sleep(5 * (attempt + 1))
    return None, dict(error=err)


def pass_c(png: Path) -> tuple[list | None, dict]:
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = dict(model=MODEL_C, stream=False, options=dict(temperature=0, num_ctx=8192),
                messages=[dict(role="user", content=PROMPT, images=[b64])])
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.loads(r.read())
        return _json_list(d["message"]["content"]), dict(model=MODEL_C)
    except Exception as e:  # noqa: BLE001
        return None, dict(error=repr(e)[:300])


# ------------------------------------------------------------------ normalizing and reconciling

def norm(v, kind):
    if v is None:
        return None
    s = str(v).strip().replace(",", ".").replace("O", "0").replace("o", "0")
    if kind == "N":
        return int(s) if re.fullmatch(r"\d{1,3}", s) else None
    m = re.fullmatch(r"(-?)(\d*)\.(\d{1,2})", s)
    return float(f"{m.group(1)}{m.group(2) or 0}.{m.group(3)}") if m else None


def rows_of(blocks) -> dict:
    out = {}
    for b in blocks or []:
        item = str(b.get("item_no") or "").strip()
        if not re.fullmatch(r"\d{5}", item):
            continue
        for t in TASKS:
            r = (b.get("rows") or {}).get(t)
            if r and len(r) == 3:
                out[(item, t)] = (norm(r[0], "N"), norm(r[1], "M"), norm(r[2], "M"), b.get("term"))
    return out


def in_range(task, n, mean, sd) -> bool:
    if n is None or mean is None or sd is None or not (0 <= n <= 50):
        return False
    if task == "10-WR":
        return 1 <= mean <= 9 and 0 <= sd <= 4
    return 0 <= mean <= 2 and 0 <= sd <= 1.5


def reconcile_page(p, side, A, B, C=None) -> list[dict]:
    a, b, c = rows_of(A), rows_of(B), rows_of(C) if C else {}
    keys = sorted(set(a) | set(b) | set(c))
    out = []
    for k in keys:
        va, vb, vc = a.get(k), b.get(k), c.get(k)
        rec = dict(page=p, side=side, item_no=k[0], task=k[1],
                   term_a=va[3] if va else None, term_b=vb[3] if vb else None)
        chosen, source = None, "flagged"
        if va and vb and va[:3] == vb[:3]:
            chosen, source = va[:3], "A=B"
        elif vc:
            for x, lab in ((va, "A"), (vb, "B")):
                if x and x[:3] == vc[:3]:
                    chosen, source = vc[:3], f"{lab}=C"
                    break
        if chosen:
            rec.update(N=chosen[0], MEAN=chosen[1], SD=chosen[2], source=source,
                       range_ok=in_range(k[1], *chosen))
        else:
            rec.update(N=None, MEAN=None, SD=None, source="flagged", range_ok=False)
        out.append(rec)
    return out


# ------------------------------------------------------------------ driver

def load_jsonl(path: Path) -> dict:
    d = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            d[(r["page"], r["side"])] = r
    return d


def append_jsonl(path: Path, rec: dict):
    with path.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def run_passes(pages: list[int], workers: int, do_c: bool = False):
    RAW.mkdir(parents=True, exist_ok=True)
    A_path, B_path, C_path = RAW / "passA.jsonl", RAW / "passB.jsonl", RAW / "passC.jsonl"
    doneA, doneB, doneC = load_jsonl(A_path), load_jsonl(B_path), load_jsonl(C_path)
    key = _key()
    jobs = []
    for p in pages:
        for side, png in render(p).items():
            if (p, side) not in doneA:
                append_jsonl(A_path, dict(page=p, side=side, blocks=pass_a(p, side, png)))
            jobs.append((p, side, png))
    todo_b = [j for j in jobs if (j[0], j[1]) not in doneB]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(pass_b, png, key): (p, side) for p, side, png in todo_b}
        for i, f in enumerate(as_completed(futs), 1):
            p, side = futs[f]
            blocks, meta = f.result()
            append_jsonl(B_path, dict(page=p, side=side, blocks=blocks, meta=meta))
            print(f"[B {i}/{len(todo_b)}] page {p}{side}: {'ok' if blocks is not None else 'FAILED'}", flush=True)
    if do_c:
        for p, side, png in jobs:
            if (p, side) not in doneC:
                blocks, meta = pass_c(png)
                append_jsonl(C_path, dict(page=p, side=side, blocks=blocks, meta=meta))
                print(f"[C] page {p}{side}: {'ok' if blocks is not None else 'FAILED'}", flush=True)


def reconcile_all() -> list[dict]:
    A, B, C = load_jsonl(RAW / "passA.jsonl"), load_jsonl(RAW / "passB.jsonl"), load_jsonl(RAW / "passC.jsonl")
    rows = []
    for k in sorted(set(A) | set(B)):
        rows += reconcile_page(k[0], k[1], A.get(k, {}).get("blocks"), B.get(k, {}).get("blocks"),
                               C.get(k, {}).get("blocks"))
    cols = ["page", "side", "item_no", "task", "term_a", "term_b", "N", "MEAN", "SD", "source", "range_ok"]
    with (RAW / "reconciled.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return rows


def summary(rows: list[dict]) -> dict:
    from collections import Counter
    src = Counter(r["source"] for r in rows)
    items = {(r["item_no"]) for r in rows}
    return dict(rows=len(rows), items=len(items), by_source=dict(src),
                range_failures=sum(1 for r in rows if r["source"] != "flagged" and not r["range_ok"]),
                pages=len({(r["page"]) for r in rows}))


def write_log(cmd: str, extra: dict):
    log = dict(timestamp=datetime.now().isoformat(timespec="seconds"), script="scripts/norman/extract.py",
               command=cmd, argv=sys.argv, pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),
               tesseract=sh(["tesseract", "--version"]).splitlines()[0], model_b=MODEL_B, model_c=MODEL_C,
               prompt_sha256=PROMPT_SHA, dpi=DPI, **extra)
    path = ROOT / "logs" / f"norman-extract-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(log, indent=2, default=str))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pages")
    p1 = sub.add_parser("pilot")
    p1.add_argument("--pages", required=True)
    p2 = sub.add_parser("run")
    p2.add_argument("--workers", type=int, default=6)
    sub.add_parser("passC")
    sub.add_parser("reconcile")
    args = ap.parse_args()
    t0 = time.time()
    if args.cmd == "pages":
        tp = table_pages()
        print(len(tp), "table pages:", tp[0], "to", tp[-1], "| separators:", [p for p in range(tp[0], tp[-1] + 1) if p not in tp])
        return
    if args.cmd == "pilot":
        pages = [int(x) for x in args.pages.split(",")]
        for p in pages:  # refuse pages with negated terms (firewall)
            terms = [b["term"] or "" for side, png in render(p).items() for b in pass_a(p, side, png)]
            bad = [t for t in terms if NEG.search(re.sub(r"[^A-Z]", "", t.upper()))]
            if bad:
                sys.exit(f"page {p} has terms with a negator; choose another pilot page")
        run_passes(pages, workers=2, do_c=True)
        rows = [r for r in reconcile_all() if r["page"] in pages]
        A, B, C = (rows_of_page(n, pages) for n in ("passA", "passB", "passC"))
        for k in sorted(set(A) | set(B) | set(C)):
            print(k, "A", A.get(k), "| B", B.get(k), "| C", C.get(k))
        print(json.dumps(summary(rows), indent=1))
        print("log:", write_log("pilot", dict(pages=pages, elapsed=round(time.time() - t0, 1))).relative_to(ROOT))
        return
    if args.cmd == "run":
        tp = table_pages()
        run_passes(tp, workers=args.workers)
        print("log:", write_log("run", dict(pages=len(tp), elapsed=round(time.time() - t0, 1))).relative_to(ROOT))
        return
    if args.cmd == "passC":
        rows = reconcile_all()
        need = sorted({r["page"] for r in rows if r["source"] == "flagged"})
        print(len(need), "pages with disagreements get pass C", flush=True)
        run_passes(need, workers=1, do_c=True)
        print("log:", write_log("passC", dict(pages=need, elapsed=round(time.time() - t0, 1))).relative_to(ROOT))
        return
    if args.cmd == "reconcile":
        s = summary(reconcile_all())
        print(json.dumps(s, indent=1))
        print("log:", write_log("reconcile", dict(summary=s)).relative_to(ROOT))


def rows_of_page(name: str, pages: list[int]) -> dict:
    d = load_jsonl(RAW / f"{name}.jsonl")
    out = {}
    for (p, side), r in d.items():
        if p in pages:
            for k, v in rows_of(r.get("blocks")).items():
                out[(p, side) + k] = v[:3]
    return out


if __name__ == "__main__":
    main()
