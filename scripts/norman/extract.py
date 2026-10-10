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
DPI_VISION = 200  # after pilot 1: 300 dpi images broke the upload; JPEG at 200 dpi works
NEG = re.compile(r"^(UN|IN|IM|IL|IR|DIS|NON)|LESS$")
MODEL_B = "z-ai/glm-5.3-flash"
MODEL_C = "claude subagent (adjudication of disputes; see README)"

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


def render_vision(p: int) -> dict:
    """JPEG halves at DPI_VISION for the vision passes (same crop fractions as render())."""
    IMG.mkdir(parents=True, exist_ok=True)
    w, h = page_size_px(p)
    k = DPI_VISION / DPI
    w, h = int(w * k), int(h * k)
    halves = {"M": (0, int(w * 0.53)), "F": (int(w * 0.47), w - int(w * 0.47))}
    paths = {}
    for side, (x, W) in halves.items():
        stem = IMG / f"p{p:03d}_{side}_v"
        jpg = stem.with_suffix(".jpg")
        if not jpg.exists():
            sh(["pdftoppm", "-f", str(p), "-l", str(p), "-r", str(DPI_VISION), "-gray", "-jpeg", "-jpegopt", "quality=85",
                "-singlefile", "-x", str(x), "-y", "0", "-W", str(W), "-H", str(h), str(PDF), str(stem)])
        paths[side] = jpg
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


def _tsv(png: Path, digits: bool) -> list[dict]:
    cmd = ["tesseract", str(png), "-", "--psm", "6"]
    if digits:
        cmd += ["-c", "tessedit_char_whitelist=0123456789.-"]
    out = sh(cmd + ["tsv"])
    rows = list(csv.DictReader(out.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE))
    toks = []
    for r in rows:
        t = (r.get("text") or "").strip()
        if t:
            toks.append(dict(text=t, left=int(r["left"]), top=int(r["top"]), w=int(r["width"]), h=int(r["height"])))
    return toks


def _ocr_digits(img) -> list[dict]:
    """Digits-only Tesseract on a PIL image, via stdin; returns tokens with positions."""
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "-c", "tessedit_char_whitelist=0123456789.-",
                          "tsv"], input=buf.getvalue(), capture_output=True, check=True).stdout.decode()
    toks = []
    for r in csv.DictReader(out.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE):
        t = (r.get("text") or "").strip()
        if t:
            toks.append(dict(text=t, left=int(r["left"]), top=int(r["top"]), w=int(r["width"]), h=int(r["height"])))
    return toks


def _fix_decimal(t: str | None, col: str) -> str | None:
    if t is None or col == "N":
        return t
    t = t.strip(".-") if t.count(".") > 1 else t
    if "." not in t and re.fullmatch(r"\d{2,3}", t):  # a dropped decimal point: 56 -> .56, 306 -> 3.06
        t = ("." + t) if len(t) == 2 else (t[0] + "." + t[1:])
    return t


def _dp_fix(t: str | None, task: str, cap: float) -> str | None:
    """On the 0-2 applicability scales a leading decimal point is often read as '2.' or '-': '2.68' or '-68'
    can only be .68 there (MEAN at most 2, S.D. at most 1.5). Not applied to 10-WR (1-9)."""
    if t is None or task == "10-WR":
        return t
    m = re.fullmatch(r"[2-]\.?(\d{2})", t)
    if m and (t.startswith("-") or float("0." + m.group(1)) < cap and not re.fullmatch(r"2\.00", t)):
        try:
            if t.startswith("-") or float(t) > cap:
                return "." + m.group(1)
        except ValueError:
            return "." + m.group(1)
    return t


def pass_a(p: int, side: str, png: Path) -> list[dict]:
    """Revised after pilot 1 (geometric, column by column). Blocks are located from ITEM lines and MEAN
    headings; for each of the N, MEAN and S.D. columns, the five-row band under every heading is cropped,
    stacked, and read by one digits-only Tesseract run; tokens map back to blocks and rows by position."""
    from PIL import Image
    words = _tsv(png, False)
    means = [t for t in words if re.match(r"^[MHN]E[AE]?[NM]", t["text"].upper())]
    items = [t for t in words if re.match(r"^IT[EF]M", t["text"].upper())]
    if not means:
        return []
    xm = sorted(t["left"] for t in means)[len(means) // 2]
    tops = sorted([t["top"] for t in means] + [t["top"] + 62 for t in items])
    heads = []
    for y in tops:
        if not heads or y - heads[-1] > 120:
            heads.append(y)
    im = Image.open(png).convert("L")
    bands = {"N": (xm - 110, xm - 12), "M": (xm - 14, xm + 96), "S": (xm + 94, xm + 196)}
    band_h, gap = 245, 40
    cols = {}
    for c, (x0, x1) in bands.items():
        stack = Image.new("L", (x1 - x0, len(heads) * (band_h + gap)), 255)
        for i, y in enumerate(heads):
            stack.paste(im.crop((x0, y + 28, x1, y + 28 + band_h)), (0, i * (band_h + gap)))
        cols[c] = _ocr_digits(stack)
    blocks = []
    for i, y in enumerate(heads):
        lo, hi = i * (band_h + gap), i * (band_h + gap) + band_h
        vals = {}
        for c in bands:
            toks = sorted((t for t in cols[c] if lo <= t["top"] + t["h"] / 2 <= hi), key=lambda t: t["top"])
            vals[c] = [_fix_decimal(t["text"], c) for t in toks]
        line = sorted([t for t in words if y - 110 <= t["top"] <= y - 25 and t["left"] < xm - 100], key=lambda t: t["left"])
        item = next((re.sub(r"\D", "", t["text"]) for t in line if len(re.sub(r"\D", "", t["text"])) == 5), None)
        term = " ".join(t["text"] for t in line if re.fullmatch(r"[A-Za-z'\-]{2,}", t["text"])
                        and t["text"].upper() not in ("ITEM", "NO", "NU")) or None
        ok = all(len(vals[c]) == 5 for c in bands)
        rws = {t: ([vals["N"][k], _dp_fix(vals["M"][k], t, 2.0), _dp_fix(vals["S"][k], t, 1.5)] if ok else None)
               for k, t in enumerate(TASKS)}
        blocks.append(dict(item_no=item, term=term, rows=rws, complete=ok))
    return blocks


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
    body = dict(model=MODEL_B, temperature=0, max_tokens=8000, reasoning=dict(effort="low"),
                messages=[dict(role="user", content=[dict(type="text", text=PROMPT),
                                                     dict(type="image_url", image_url=dict(url=f"data:image/jpeg;base64,{b64}"))])])
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            reply = d["choices"][0]["message"].get("content")
            if not reply:
                raise KeyError("empty content (finish: %s)" % d["choices"][0].get("finish_reason"))
            return _json_list(reply), dict(model=d.get("model"), usage=d.get("usage"))
        except Exception as e:  # noqa: BLE001  (after wave 1: an ssl.SSLError escaped the narrower list and stopped the run)
            err = repr(e)[:300]
            time.sleep(5 * (attempt + 1))
    return None, dict(error=err)


def pass_x(png: Path, prompt_file: Path) -> tuple[list | None, dict]:
    """Codex vision (read-only wrapper with -i), added after pilot 2; the answer follows the last 'codex' line."""
    out = subprocess.run([str(ROOT / "scripts" / "codex-ro-images.sh"), str(ROOT), str(prompt_file), str(png)],
                         capture_output=True, text=True, timeout=900).stdout
    lines = out.splitlines()
    starts = [i for i, l in enumerate(lines) if l.strip() == "codex"]
    if not starts:
        return None, dict(error="no answer")
    body = "\n".join(lines[starts[-1] + 1:]).split("tokens used")[0]
    tok = next((lines[i + 1].strip() for i, l in enumerate(lines) if l.startswith("tokens used") and i + 1 < len(lines)), None)
    try:
        return _json_list(body), dict(model="codex", tokens=tok)
    except json.JSONDecodeError as e:
        return None, dict(error=repr(e)[:200], tokens=tok)


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


def align_blocks(A, B):
    """Revised after pilot 1: Tesseract misreads item numbers, so A's blocks take B's item numbers by
    position: by index when the counts match, otherwise by digit agreement (at least 4 of 5) in order."""
    A, B = list(A or []), list(B or [])
    if not A or not B:
        return A
    def sim(x, y):
        x, y = str(x or ""), str(y or "")
        return sum(1 for u, v in zip(x, y) if u == v) if len(x) == len(y) == 5 else 0
    out = []
    if len(A) == len(B):
        for a, b in zip(A, B):
            out.append(dict(a, item_no=b.get("item_no") if sim(a.get("item_no"), b.get("item_no")) >= 3 or not a.get("item_no") else a.get("item_no")))
        return out
    j = 0
    for a in A:
        best = max(range(j, len(B)), key=lambda k: sim(a.get("item_no"), B[k].get("item_no")), default=None)
        if best is not None and sim(a.get("item_no"), B[best].get("item_no")) >= 4:
            out.append(dict(a, item_no=B[best].get("item_no")))
            j = best + 1
        else:
            out.append(a)
    return out


def reconcile_page(p, side, A, B, C=None, X=None, X2=None) -> list[dict]:
    """After pilot 2: accept a value when two different model families agree (Codex X with GLM B or with
    Tesseract A; or A with B). Unresolved rows take a second, zoomed Codex read X2, accepted if it matches
    any of A, B or X."""
    A = align_blocks(A, X or B)
    a, b, c = rows_of(A), rows_of(B), rows_of(C) if C else {}
    x, x2 = rows_of(X) if X else {}, rows_of(X2) if X2 else {}
    if x:
        out = []
        for k in sorted(set(a) | set(b) | set(x)):
            va, vb, vx, v2 = (d.get(k) for d in (a, b, x, x2))
            rec = dict(page=p, side=side, item_no=k[0], task=k[1], term_a=va[3] if va else None,
                       term_b=(vx or vb or (None,) * 4)[3])
            chosen, source = None, "flagged"
            for u, w, lab in ((vx, vb, "X=B"), (vx, va, "X=A"), (va, vb, "A=B")):
                if u and w and u[:3] == w[:3]:
                    chosen, source = u[:3], lab
                    break
            if chosen is None and v2:
                for u, lab in ((vx, "X2=X"), (vb, "X2=B"), (va, "X2=A")):
                    if u and u[:3] == v2[:3]:
                        chosen, source = v2[:3], lab
                        break
            if chosen:
                rec.update(N=chosen[0], MEAN=chosen[1], SD=chosen[2], source=source, range_ok=in_range(k[1], *chosen))
            else:
                rec.update(N=None, MEAN=None, SD=None, source="flagged", range_ok=False)
            out.append(rec)
        return out
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
        vis = render_vision(p)
        for side, png in render(p).items():
            if (p, side) not in doneA:
                append_jsonl(A_path, dict(page=p, side=side, blocks=pass_a(p, side, png)))
            jobs.append((p, side, vis[side]))
    todo_b = [j for j in jobs if (j[0], j[1]) not in doneB]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(pass_b, png, key): (p, side) for p, side, png in todo_b}
        for i, f in enumerate(as_completed(futs), 1):
            p, side = futs[f]
            blocks, meta = f.result()
            append_jsonl(B_path, dict(page=p, side=side, blocks=blocks, meta=meta))
            print(f"[B {i}/{len(todo_b)}] page {p}{side}: {'ok' if blocks is not None else 'FAILED'}", flush=True)
    X_path = RAW / "passX.jsonl"
    doneX = load_jsonl(X_path)
    prompt_file = RAW / "prompt_x.md"
    prompt_file.write_text(PROMPT + " Do not run any commands; read the attached image directly.")
    todo_x = [(p, side) for p, side, _ in jobs if (p, side) not in doneX]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(pass_x, IMG / f"p{p:03d}_{side}.png", prompt_file): (p, side) for p, side in todo_x}
        for i, f in enumerate(as_completed(futs), 1):
            p, side = futs[f]
            blocks, meta = f.result()
            append_jsonl(X_path, dict(page=p, side=side, blocks=blocks, meta=meta))
            print(f"[X {i}/{len(todo_x)}] page {p}{side}: {'ok' if blocks is not None else 'FAILED'} {meta.get('tokens')}", flush=True)
    if do_c:
        for p, side, png in jobs:
            if (p, side) not in doneC:
                blocks, meta = pass_c(png)
                append_jsonl(C_path, dict(page=p, side=side, blocks=blocks, meta=meta))
                print(f"[C] page {p}{side}: {'ok' if blocks is not None else 'FAILED'}", flush=True)


def reconcile_all() -> list[dict]:
    A, B, C = load_jsonl(RAW / "passA.jsonl"), load_jsonl(RAW / "passB.jsonl"), load_jsonl(RAW / "passC.jsonl")
    Xp, X2 = load_jsonl(RAW / "passX.jsonl"), load_jsonl(RAW / "passX2.jsonl")
    rows = []
    for k in sorted(set(A) | set(B) | set(Xp)):
        rows += reconcile_page(k[0], k[1], A.get(k, {}).get("blocks"), B.get(k, {}).get("blocks"),
                               C.get(k, {}).get("blocks"), Xp.get(k, {}).get("blocks"), X2.get(k, {}).get("blocks"))
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
    p2.add_argument("--first", type=int, default=0, help="index of the first table page in this wave")
    p2.add_argument("--count", type=int, default=10_000, help="number of table pages in this wave")
    sub.add_parser("passC")
    sub.add_parser("disputes")
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
        tp = table_pages()[args.first: args.first + args.count]
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
    if args.cmd == "disputes":
        rows = reconcile_all()
        d = {}
        for r in rows:
            if r["source"] == "flagged":
                d.setdefault((r["page"], r["side"]), []).append(dict(item_no=r["item_no"], task=r["task"]))
        with (RAW / "disputes.jsonl").open("w") as fh:
            for (p, side), lst in sorted(d.items()):
                fh.write(json.dumps(dict(page=p, side=side, image=str(IMG / f"p{p:03d}_{side}.png"), disputes=lst)) + "\n")
        print(len(d), "half-pages,", sum(len(v) for v in d.values()), "disputed rows ->", (RAW / "disputes.jsonl").relative_to(ROOT))
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
