#!/usr/bin/env python3
"""Transcribe Norman (1967), ERIC ED014738, Appendices 1-14 (spec: scripts/norman/README.md).

Transcription only. Outside `pilot`, values are never printed: summaries report counts.

    python3 scripts/norman/extract.py pages                 # list table pages and separators
    python3 scripts/norman/extract.py pilot --pages 40,41   # bounded X,V check
    python3 scripts/norman/extract.py run --workers 4 --first 0 --count 60  # X,V wave 1 after acceptance
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
import signal
import subprocess
import sys
import time
import traceback
import uuid
import platform
import importlib.metadata
import importlib.util
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
    return pass_columns(png, _tsv(png, False), _ocr_digits, repair_digits=True)


def pass_columns(png: Path, words: list[dict], ocr, *, repair_digits: bool) -> list[dict]:
    """Shared crop geometry; each engine independently locates headings and reads digits."""
    from PIL import Image
    words = [dict(token, **{key: int(round(token[key])) for key in ("left", "top", "w", "h")})
             for token in words]
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
        cols[c] = ocr(stack)
    blocks = []
    for i, y in enumerate(heads):
        lo, hi = i * (band_h + gap), i * (band_h + gap) + band_h
        vals = {}
        for c in bands:
            toks = sorted((t for t in cols[c] if lo <= t["top"] + t["h"] / 2 <= hi), key=lambda t: t["top"])
            vals[c] = [(_fix_decimal(t["text"], c) if repair_digits else t["text"]) for t in toks]
        line = sorted([t for t in words if y - 110 <= t["top"] <= y - 25 and t["left"] < xm - 100], key=lambda t: t["left"])
        item = next((re.sub(r"\D", "", t["text"]) for t in line if len(re.sub(r"\D", "", t["text"])) == 5), None)
        term = " ".join(t["text"] for t in line if re.fullmatch(r"[A-Za-z'\-]{2,}", t["text"])
                        and t["text"].upper() not in ("ITEM", "NO", "NU")) or None
        ok = all(len(vals[c]) == 5 for c in bands)
        rws = {t: ([vals["N"][k],
                    _dp_fix(vals["M"][k], t, 2.0) if repair_digits else vals["M"][k],
                    _dp_fix(vals["S"][k], t, 1.5) if repair_digits else vals["S"][k]] if ok else None)
               for k, t in enumerate(TASKS)}
        blocks.append(dict(item_no=item, term=term, rows=rws, complete=ok))
    return blocks


def _vision_tokens(img) -> list[dict]:
    """Local Apple Vision, accurate level, no language correction; top-left pixel coordinates."""
    import io
    import objc
    import Vision
    from Foundation import NSData, NSMakeRange
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    payload = buf.getvalue()
    with objc.autorelease_pool():
        req = Vision.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(False)
        req.setRecognitionLanguages_(["en-US"])
        data = NSData.dataWithBytes_length_(payload, len(payload))
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, {})
        ok, error = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError("Apple Vision request failed")
        tokens = []
        for obs in req.results() or []:
            candidates = obs.topCandidates_(1)
            if not candidates:
                continue
            candidate = candidates[0]
            line = str(candidate.string())
            for match in re.finditer(r"\S+", line):
                # Vision uses UTF-16 offsets, even when Python indexes code points.
                start = len(line[:match.start()].encode("utf-16-le")) // 2
                length = len(match.group().encode("utf-16-le")) // 2
                box, error = candidate.boundingBoxForRange_error_(NSMakeRange(start, length), None)
                if box is None:
                    continue
                rect = box.boundingBox()
                tokens.append(dict(text=match.group(), left=rect.origin.x * img.width,
                                   top=(1 - rect.origin.y - rect.size.height) * img.height,
                                   w=rect.size.width * img.width, h=rect.size.height * img.height))
        return tokens


def pass_v(png: Path) -> tuple[list | None, dict]:
    from PIL import Image
    t0 = time.monotonic()
    meta = dict(engine="Apple Vision", recognition_level="accurate", language_correction=False,
                pyobjc_vision=importlib.metadata.version("pyobjc-framework-Vision"),
                macos=platform.mac_ver()[0], geometric_parser="column-v1", digit_repairs=False)
    try:
        with Image.open(png) as image:
            words = _vision_tokens(image.convert("L"))
        blocks = pass_columns(png, words, _vision_tokens, repair_digits=False)
        if not blocks:
            meta["error"] = "no blocks detected"
        return blocks or None, dict(meta, elapsed_seconds=time.monotonic() - t0)
    except Exception as error:
        # Error details are saved privately; public summaries retain only failure counts.
        error_path = RAW / "passV-errors" / (png.stem + "-" + uuid.uuid4().hex + ".txt")
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text(traceback.format_exc())
        return None, dict(meta, error=type(error).__name__, error_path=str(error_path.relative_to(ROOT)),
                          elapsed_seconds=time.monotonic() - t0)


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


def validate_blocks(blocks) -> list:
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("answer must be a nonempty block list")
    seen = set()
    for block in blocks:
        if not isinstance(block, dict) or not {"item_no", "term", "rows"} <= block.keys():
            raise ValueError("block fields missing")
        item = block["item_no"]
        if item is not None and (not isinstance(item, str) or not re.fullmatch(r"\d{5}", item) or item in seen):
            raise ValueError("invalid or duplicate item number")
        if item is not None:
            seen.add(item)
        if block["term"] is not None and not isinstance(block["term"], str):
            raise ValueError("term must be string or null")
        rows = block["rows"]
        if not isinstance(rows, dict) or set(rows) != set(TASKS):
            raise ValueError("five task rows required")
        for row in rows.values():
            if row is not None and (not isinstance(row, list) or len(row) != 3 or
                                    any(v is not None and not isinstance(v, str) for v in row)):
                raise ValueError("row must have three strings/nulls or be null")
    return blocks


def parse_x_answer(answer: str, stdout: str, stderr: str, returncode: int) -> tuple[list | None, dict]:
    tokens = re.findall(r"tokens used\s*\n\s*([\d,]+)", stderr + "\n" + stdout)
    model = re.search(r"(?m)^model:\s*(\S+)", stderr)
    effort = re.search(r"(?m)^reasoning effort:\s*(\S+)", stderr)
    meta = dict(model=model.group(1) if model else None, effort=effort.group(1) if effort else None,
                requested_effort=None, effort_note="historical wrapper omission; header is not a resolved provider setting",
                tokens=int(tokens[-1].replace(",", "")) if tokens else None, returncode=returncode)
    if returncode:
        return None, dict(meta, error="process failed")
    if meta["model"] != "gpt-6.1-sol" or meta["effort"] != "none":
        return None, dict(meta, error="instrument header mismatch")
    try:
        return validate_blocks(_json_list(answer or stdout)), meta
    except (ValueError, TypeError):
        return None, dict(meta, error="invalid or empty JSON answer")


def pass_x(png: Path, prompt_file: Path) -> tuple[list | None, dict]:
    """One attempt; retain separate streams and use Codex's final-message file."""
    dest = RAW / "passX-attempts" / (png.stem + "-" + uuid.uuid4().hex)
    dest.mkdir(parents=True)
    answer_path = dest / "answer.txt"
    env = dict(os.environ, NORMAN_CODEX_LAST_MESSAGE=str(answer_path))
    t0 = time.monotonic()
    with (dest / "stdout.txt").open("w") as stdout, (dest / "stderr.txt").open("w") as stderr:
        proc = subprocess.Popen([str(ROOT / "scripts" / "codex-ro-images.sh"), str(ROOT),
                                 str(prompt_file), str(png)], stdout=stdout, stderr=stderr,
                                env=env, start_new_session=True)
        try:
            returncode = proc.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            returncode = proc.wait()
    blocks, meta = parse_x_answer(answer_path.read_text() if answer_path.exists() else "",
                                 (dest / "stdout.txt").read_text(), (dest / "stderr.txt").read_text(), returncode)
    meta.update(attempt_path=str(dest.relative_to(ROOT)), elapsed_seconds=time.monotonic() - t0,
                prompt_sha256=hashlib.sha256(prompt_file.read_bytes()).hexdigest(),
                image_sha256=hashlib.sha256(png.read_bytes()).hexdigest())
    return blocks, meta


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


def reconcile_page(p, side, A, B, C=None, X=None, X2=None, V=None) -> list[dict]:
    """Cross-engine agreement; historical B remains usable alongside its replacement V."""
    A = align_blocks(A, X or B or V)
    engines = {name: rows_of(blocks) for name, blocks in
               (("A", A), ("B", B), ("C", C), ("X", X), ("X2", X2), ("V", V))}
    keys = sorted(set().union(*(set(rows) for rows in engines.values())))
    pairs = (("X", "V"), ("X", "B"), ("X", "A"), ("A", "V"), ("A", "B"),
             ("B", "V"), ("A", "C"), ("B", "C"))
    out = []
    for key in keys:
        values = {name: rows.get(key) for name, rows in engines.items()}
        term = next((values[name][3] for name in ("X", "B", "V", "C", "A") if values[name]), None)
        rec = dict(page=p, side=side, item_no=key[0], task=key[1],
                   term_a=values["A"][3] if values["A"] else None, term_b=term)
        chosen, source = None, "flagged"
        for first, second in pairs:
            u, v = values[first], values[second]
            if u and v and None not in u[:3] and u[:3] == v[:3]:
                chosen, source = u[:3], first + "=" + second
                break
        if chosen is None and values["X2"]:
            for name in ("X", "B", "V", "A"):
                u, v = values[name], values["X2"]
                if u and None not in u[:3] and u[:3] == v[:3]:
                    chosen, source = v[:3], "X2=" + name
                    break
        if chosen is None:
            rec.update(N=None, MEAN=None, SD=None, source="flagged", range_ok=False)
        else:
            rec.update(N=chosen[0], MEAN=chosen[1], SD=chosen[2], source=source,
                       range_ok=in_range(key[1], *chosen))
        out.append(rec)
    return out


# ------------------------------------------------------------------ driver

def load_jsonl(path: Path) -> dict:
    d = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            key = (r["page"], r["side"])
            if r.get("blocks") is not None or key not in d or d[key].get("blocks") is None:
                d[key] = r
    return d


def append_jsonl(path: Path, rec: dict):
    with path.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def run_passes(pages: list[int], workers: int, passes=("X", "V")):
    """Each invocation makes at most one attempt per missing/failed half-page and selected engine."""
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    if not set(passes) <= {"A", "B", "C", "X", "V"}:
        raise ValueError("unknown pass")
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [(p, side, png) for p in pages for side, png in render(p).items()]
    prompt_file = RAW / "prompt_x.md"
    prompt_file.write_text(PROMPT + " Do not run any commands; read the attached image directly.")
    counts = {}
    for name in passes:
        path = RAW / f"pass{name}.jsonl"
        done = load_jsonl(path)
        todo = [job for job in jobs if done.get(job[:2], {}).get("blocks") is None]
        key = _key() if name == "B" else None
        def run_one(job):
            p, side, png = job
            if name == "A":
                return pass_a(p, side, png), {"engine": "Tesseract"}
            if name == "B":
                return pass_b(render_vision(p)[side], key)
            if name == "C":
                return pass_c(render_vision(p)[side])
            if name == "V":
                return pass_v(png)
            return pass_x(png, prompt_file)
        counts[name] = {"attempted": len(todo), "failed": 0, "reused": len(jobs) - len(todo)}
        # Vision has local native state; run it sequentially. X uses the requested bound.
        with ThreadPoolExecutor(max_workers=1 if name == "V" else workers) as executor:
            futures = {executor.submit(run_one, job): job[:2] for job in todo}
            for i, future in enumerate(as_completed(futures), 1):
                p, side = futures[future]
                try:
                    blocks, meta = future.result()
                except Exception as error:
                    blocks, meta = None, {"error": type(error).__name__}
                append_jsonl(path, dict(page=p, side=side, blocks=blocks, meta=meta,
                                       attempted_at=datetime.now().isoformat(timespec="seconds")))
                counts[name]["failed"] += blocks is None
                print(f"[{name} {i}/{len(todo)}] page {p}{side}: {'ok' if blocks is not None else 'FAILED'}", flush=True)
    return counts


def reconcile_all() -> list[dict]:
    A, B, C = load_jsonl(RAW / "passA.jsonl"), load_jsonl(RAW / "passB.jsonl"), load_jsonl(RAW / "passC.jsonl")
    Xp, X2 = load_jsonl(RAW / "passX.jsonl"), load_jsonl(RAW / "passX2.jsonl")
    V = load_jsonl(RAW / "passV.jsonl")
    rows = []
    for k in sorted(set(A) | set(B) | set(Xp) | set(V)):
        rows += reconcile_page(k[0], k[1], A.get(k, {}).get("blocks"), B.get(k, {}).get("blocks"),
                               C.get(k, {}).get("blocks"), Xp.get(k, {}).get("blocks"), X2.get(k, {}).get("blocks"), V.get(k, {}).get("blocks"))
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
               prompt_sha256=PROMPT_SHA, dpi=DPI, python=sys.version,
               code_commit=sh(["git", "rev-parse", "HEAD"], cwd=ROOT).strip(),
               codex=sh(["/opt/homebrew/bin/codex", "--version"]).strip(),
               model_x="gpt-6.1-sol", requested_effort_x=None, expected_header_effort_x="none", macos=platform.mac_ver()[0],
               packages={name: importlib.metadata.version(name) for name in
                         ("Pillow", "pyobjc-framework-Vision") if importlib.util.find_spec("Vision")}, **extra)
    path = ROOT / "logs" / f"norman-extract-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(log, indent=2, default=str))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pages")
    p1 = sub.add_parser("pilot")
    p1.add_argument("--pages", required=True)
    p1.add_argument("--passes", default="X,V")
    p2 = sub.add_parser("run")
    p2.add_argument("--workers", type=int, default=4)
    p2.add_argument("--passes", default="X,V")
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
        if sorted(pages) != [40, 41]:
            sys.exit("Only approved pilot pages 40 and 41 may be inspected")
        counts = run_passes(pages, workers=2, passes=tuple(args.passes.split(",")))
        print("log:", write_log("pilot", dict(pages=pages, counts=counts,
                                              elapsed=round(time.time() - t0, 1))).relative_to(ROOT))
        return
    if args.cmd == "run":
        tp = table_pages()[args.first: args.first + args.count]
        counts = run_passes(tp, workers=args.workers, passes=tuple(args.passes.split(",")))
        print("log:", write_log("run", dict(pages=len(tp), counts=counts, elapsed=round(time.time() - t0, 1))).relative_to(ROOT))
        return
    if args.cmd == "passC":
        rows = reconcile_all()
        need = sorted({r["page"] for r in rows if r["source"] == "flagged"})
        print(len(need), "pages with disagreements get pass C", flush=True)
        run_passes(need, workers=1, passes=("C",))
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
