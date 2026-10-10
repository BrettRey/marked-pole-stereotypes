#!/usr/bin/env python3
"""Collect and verify the three assigned components; never launch model jobs."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import math
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from run_state import atomic_json, digest

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache/d1c/parallel-collection"
OUTPUT = ROOT / "results/d1c/parallel-components-20261010"
CLOUD_BRANCH = "claude/d1c-cloud-benchmark-qjwn7f"
CLOUD_PATH = "results/d1c/cloud-canary-20261010"
UPSTREAM_COMMIT = "942dfd8109232beaf7e5bf35c023409b09a18525"
UPSTREAM_SHA = "76dd842934bb2d0ab9c3b5db9fe1a1be2876183e8abb059e2891a751db3295f6"
HF_JOB = "BrettRey/6aca739c095c578089314dc3"
HF_PATH = "hf://buckets/BrettRey/marked-pole-d1c-compute/20261010/component-002"
NAMES = ("h2", "h1_fixed_usage", "marking", "b_z")
TERMINAL_HF = {"COMPLETED", "ERROR", "CANCELED", "DELETED"}


def command(*args):
    environment = os.environ.copy()
    environment.pop("HF_TOKEN", None)  # authorized cached OAuth; never log credentials
    return subprocess.run(args, cwd=ROOT, env=environment, check=True,
                          capture_output=True, timeout=60).stdout


def json_file(path):
    return json.loads(path.read_bytes())


def atomic_bytes(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".collecting")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def verify_component(folder, key):
    """Pure read: do not acquire a writer lock or rewrite sampler progress."""
    manifest = json_file(folder / "manifest.json")
    signature = digest(manifest["specification"])
    if manifest.get("schema") != 1 or manifest.get("signature") != signature:
        raise ValueError("Damaged manifest")
    marker = folder / f"component-{key}.json"
    if not marker.exists():
        return None
    envelope = json_file(marker)
    record = envelope["record"]
    if (digest(record) != envelope.get("sha256") or record.get("signature") != signature
            or record.get("key") != key or record.get("archive") != f"component-{key}.npz"):
        raise ValueError("Damaged or incompatible component marker")
    archive = folder / record["archive"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != record["archive_sha256"]:
        raise ValueError("Damaged component archive")
    with np.load(archive, allow_pickle=False) as loaded:
        arrays = {name: loaded[name].copy() for name in loaded.files}
    schema = {name: dict(shape=list(value.shape), dtype=str(value.dtype))
              for name, value in arrays.items()}
    if schema != record["arrays"]:
        raise ValueError("Component array schema differs")
    return manifest, record, arrays


def validate_assignment(directory, location, component, canonical):
    upstream = directory / ("checkpoints" if location == "cloud" else "upstream")
    verified = verify_component(upstream, "upstream")
    if verified is None:
        raise ValueError("Missing upstream completion marker")
    upstream_manifest, upstream_record, _ = verified
    if (upstream_record["archive_sha256"] != UPSTREAM_SHA
            or upstream_manifest["signature"] != canonical["signature"]):
        raise ValueError("Input differs from the agreed shared upstream checkpoint")
    checkpoint = directory / "checkpoints"
    manifest = json_file(checkpoint / "manifest.json")
    spec, expected = manifest["specification"], canonical["specification"]
    if digest(spec) != manifest["signature"]:
        raise ValueError("Damaged assignment manifest")
    if spec["job"] != expected["job"] or spec["sampler"] != expected["sampler"]:
        raise ValueError("Job or sampler differs from the assigned benchmark")
    if location != "cloud" and (spec["component"] != component
            or spec["upstream_archive_sha256"] != UPSTREAM_SHA
            or spec["upstream_commit"] != UPSTREAM_COMMIT
            or spec["upstream_specification_signature"] != canonical["signature"]):
        raise ValueError("Independent component assignment differs")
    key = f"downstream-{component:03d}"
    result = verify_component(checkpoint, key)
    if result is None:
        return None
    _, record, arrays = result
    if set(arrays) != set(NAMES) or any(values.shape != (16000,) for values in arrays.values()):
        raise ValueError("Expected 16,000 draws for each of the four scalar contrasts")
    diagnostic = record["metadata"]["diagnostic"]
    expected_seed = int(np.random.SeedSequence(expected["root_seed"],
                         spawn_key=(4, 10, 0, component)).generate_state(1)[0])
    if (diagnostic["seed"] != expected_seed or diagnostic["mode"] != "downstream"
            or diagnostic["draws"] != 4000 or diagnostic["tune"] != 2000):
        raise ValueError("Saved sampler diagnostic does not match the assignment")
    return record, arrays


def refresh_cloud():
    command("git", "fetch", "--quiet", "origin", CLOUD_BRANCH)
    revision = command("git", "rev-parse", f"origin/{CLOUD_BRANCH}").decode().strip()
    paths = command("git", "ls-tree", "-r", "--name-only", revision, "--", CLOUD_PATH).decode().splitlines()
    destination = CACHE / "cloud"
    for name in paths:
        relative = Path(name).relative_to(CLOUD_PATH)
        if (str(relative) in {"runtime.json", "benchmark.json", "worker-result.json", "worker-stdout.txt"}
                or (relative.parent == Path("checkpoints") and
                    (relative.name in {"manifest.json", "progress.json"}
                     or re.fullmatch(r"component-(upstream|downstream-000)\.(json|npz)", relative.name)))):
            atomic_bytes(destination / relative, command("git", "show", f"{revision}:{name}"))
    return dict(revision=revision)


def refresh_hf():
    response = json.loads(command("hf", "jobs", "inspect", HF_JOB, "--json"))[0]
    command("hf", "buckets", "sync", HF_PATH, str(CACHE / "hf"))
    stage = response["status"]["stage"]
    durations = response.get("durations", {})
    seconds = sum(durations.get(name, 0) for name in ("starting_secs", "running_secs"))
    return dict(job=HF_JOB, stage=stage, durations=durations,
                estimated_compute_usd=math.ceil(seconds/60)*.03/60,
                estimate_basis="Provider starting/running duration rounded up to a minute; not an invoice.")


def preserve(directory, location, component):
    """Only called after validation; archive precedes completion marker."""
    target = OUTPUT / "collected" / location
    relative = [Path("runtime.json"), Path("checkpoints/manifest.json")]
    upstream = Path("checkpoints" if location == "cloud" else "upstream")
    relative += [upstream / name for name in
                 ("manifest.json", "component-upstream.npz", "component-upstream.json")]
    key = f"component-downstream-{component:03d}"
    relative += [Path("checkpoints") / f"{key}.{suffix}" for suffix in ("npz", "json")]
    for name in relative:
        if (directory / name).exists():
            atomic_bytes(target / name, (directory / name).read_bytes())


def conditional_summary(arrays):
    return {name: dict(draws=len(values), finite_draws=int(np.isfinite(values).sum()),
                       mean=float(np.mean(values)), median=float(np.median(values)),
                       lo50=float(np.quantile(values, .25)), hi50=float(np.quantile(values, .75)),
                       lo90=float(np.quantile(values, .05)), hi90=float(np.quantile(values, .95)))
            for name, values in arrays.items()}


def collect():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    canonical = json.loads(command("git", "show", f"{UPSTREAM_COMMIT}:{CLOUD_PATH}/checkpoints/manifest.json"))
    report = dict(observed_at=datetime.now(timezone.utc).isoformat(), full_cut=False,
                  assigned_components=[0, 1, 2], unassigned_components=[3, 4, 5, 6, 7],
                  scope="Three conditional components of cell 10, replicate 0; no calibration claim.",
                  timing_limit="Different fixed latent draws, compile environments and local contention; not matched hardware trials.",
                  hf_budget=dict(total_authorized_usd=10, active_job_ceiling_usd=.72,
                                 conservative_reserved_usd=1.44, billed_total_usd=None),
                  components={}, refresh_errors={})
    sources = {"cloud": CACHE / "cloud", "local": ROOT / "results/d1c/local-component-001-20261010", "hf": CACHE / "hf"}
    refreshed = {}
    for location, refresh in (("cloud", refresh_cloud), ("hf", refresh_hf)):
        try:
            refreshed[location] = refresh()
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError) as exc:
            # Do not include subprocess stderr: account/network errors could
            # contain details unrelated to the scientific record.
            report["refresh_errors"][location] = type(exc).__name__
    for component, (location, directory) in enumerate(sources.items()):
        entry = dict(component=component, monitoring=refreshed.get(location, {}), state="pending", terminal=False)
        try:
            runtime = json_file(directory / "runtime.json")
            entry["runtime"] = runtime
            result = validate_assignment(directory, location, component, canonical)
            if result is not None:
                record, arrays = result
                preserve(directory, location, component)
                diagnostic = record["metadata"]["diagnostic"]
                entry.update(state="verified_component", archive_sha256=record["archive_sha256"],
                             diagnostic=diagnostic, diagnostics_pass=bool(diagnostic["good"] and diagnostic["contrast_good"]),
                             conditional_summaries=conditional_summary(arrays))
            if location == "hf":
                entry["terminal"] = refreshed.get(location, {}).get("stage") in TERMINAL_HF
            elif location == "cloud":
                entry["terminal"] = runtime["state"] in {"complete", "failed", "interrupted"}
            else:
                entry["terminal"] = runtime["state"] in {"component_complete", "interrupted"}
                log = ROOT / "logs/d1c-local-component-001-20261010-stdout.txt"
                matches = re.findall(r"sampling .*: draws (\[[0-9, ]+\]); steps", log.read_text()) if log.exists() else []
                if matches:
                    counts = json.loads(matches[-1])
                    entry["sampler_progress"] = dict(finished_draws_including_warmup=counts,
                        target_per_chain=6000, total_target=24000,
                        note="Sampler callback counts include warmup; not a completion checkpoint.")
                if not entry["terminal"]:
                    observed = subprocess.run(["ps", "-p", str(runtime["pid"]), "-o", "command="],
                                              capture_output=True, text=True, timeout=10).stdout
                    if "scripts/d1c/run_component.py" not in observed or "--component 1" not in observed:
                        entry.update(state="worker_stopped_without_final_record", terminal=True)
            if entry["terminal"] and result is None:
                entry["state"] = "stopped_without_component"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entry.update(state="verification_pending_or_failed", verification_error=type(exc).__name__ + ": " + str(exc))
        report["components"][location] = entry
    report["all_assigned_jobs_terminal"] = all(entry["terminal"] for entry in report["components"].values())
    report["verified_components"] = [entry["component"] for entry in report["components"].values()
                                      if entry["state"] == "verified_component"]
    atomic_json(OUTPUT / "status.json", report)
    rows = []
    for location, entry in report["components"].items():
        for name, summary in entry.get("conditional_summaries", {}).items():
            rows.append(dict(location=location, component=entry["component"], contrast=name,
                             diagnostics_pass=entry["diagnostics_pass"], **summary))
    stream = io.StringIO()
    fields = ["location", "component", "contrast", "diagnostics_pass", "draws", "finite_draws", "mean", "median", "lo50", "hi50", "lo90", "hi90"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(OUTPUT / "conditional-summaries.csv", stream.getvalue().encode())
    print(json.dumps(dict(observed_at=report["observed_at"], verified=report["verified_components"],
                          states={name: entry["state"] for name, entry in report["components"].items()},
                          refresh_errors=report["refresh_errors"])), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "collector.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            report = collect()
            if not args.watch or report["all_assigned_jobs_terminal"]:
                return
            time.sleep(60)


if __name__ == "__main__":
    main()
