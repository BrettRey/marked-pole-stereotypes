#!/usr/bin/env python3
"""Run one assigned cut component from a verified, published upstream draw set."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import d1c
import numpy as np
from component_state import ComponentState, contrast_arrays, contrast_summaries
from run_state import atomic_json, digest

UPSTREAM_COMMIT = "942dfd8109232beaf7e5bf35c023409b09a18525"
UPSTREAM_PATH = "results/d1c/cloud-canary-20261010/checkpoints"


def git(*args, binary=False):
    result = subprocess.run(["git", *args], cwd=d1c.ROOT, capture_output=True,
                            check=True, timeout=60)
    return result.stdout if binary else result.stdout.decode().strip()


def component_rng(state, component, *, chains, draws, contrast_draws):
    """Replay only prior random selections, without redoing prior model fits."""
    if component < 0 or contrast_draws % chains or contrast_draws > chains*draws:
        raise ValueError("Invalid component or balanced contrast budget")
    rng = np.random.default_rng()
    rng.bit_generator.state = state
    # posterior_contrasts makes exactly one choice per chain and no other
    # RNG calls. An integration test checks this against that actual function.
    for _ in range(component):
        for _ in range(chains):
            rng.choice(draws, contrast_draws//chains, replace=False)
    return rng


def imported_upstream(directory):
    destination = directory / "upstream"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "component-upstream.json", "component-upstream.npz"):
        payload = git("show", f"{UPSTREAM_COMMIT}:{UPSTREAM_PATH}/{name}", binary=True)
        path = destination / name
        if path.exists() and path.read_bytes() != payload:
            raise ValueError("The local upstream input differs from the published checkpoint")
        path.write_bytes(payload)
    manifest = json.loads((destination / "manifest.json").read_text())
    with ComponentState(destination, manifest["specification"]) as source:
        metadata, selected = source.load("upstream")
        archive_hash = source.records["upstream"]["archive_sha256"]
    return manifest["specification"], metadata, selected, archive_hash


def run_one(job, component, metadata, selected, store):
    key = f"downstream-{component:03d}"
    saved = store.load(key)
    if saved is not None:
        return saved[0]
    observed, _, data_seed = d1c.generate(job)
    fixed = {f"{name}_fixed": values[component] for name, values in selected.items()}
    rng = component_rng(metadata["rng_state"], component, chains=d1c.CHAINS,
                        draws=d1c.DRAWS, contrast_draws=d1c.POST_DRAWS)
    sampling_seed = d1c.seed(4, job["cell"], job["rep"], component)
    trace, diagnostic = d1c.sample(job, "downstream",
                                 dict(d1c.downstream_data(observed), **fixed), sampling_seed)
    rows, good, rhat, ess = d1c.posterior_contrasts(trace, observed, fixed, rng)
    diagnostic.update(contrast_good=good, contrast_rhat=rhat, contrast_ess=ess)
    arrays = contrast_arrays(rows)
    result = dict(diagnostic=diagnostic, data_seed=data_seed,
                  rng_state=rng.bit_generator.state, summaries=contrast_summaries(arrays),
                  interpretation=f"conditional cut component {component}; not the full cut")
    store.save(key, result, arrays)
    return result


def export_files(directory, destination):
    """Copy completed outputs to a persistent mount; copy markers last."""
    destination.mkdir(parents=True, exist_ok=True)
    paths = [directory / "runtime.json"]
    for folder in ("upstream", "checkpoints"):
        parent = directory / folder
        paths.extend(parent / name for name in ("manifest.json", "progress.json"))
        for marker in parent.glob("component-*.json"):
            envelope = json.loads(marker.read_text())
            record = envelope["record"]
            archive = parent / record["archive"]
            if (archive.parent != parent or digest(record) != envelope["sha256"]
                    or hashlib.sha256(archive.read_bytes()).hexdigest() != record["archive_sha256"]):
                raise ValueError("Refusing to export a damaged component")
            paths.extend((archive, marker))
    for source in paths:
        if not source.exists():
            continue
        target = destination / source.relative_to(directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise OSError(f"Export readback differs: {target.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--component", type=int, choices=[1, 2], required=True)
    parser.add_argument("--location", choices=["local", "hf"], required=True)
    parser.add_argument("--export-directory", type=Path)
    args = parser.parse_args()
    if (args.location, args.component) not in (("local", 1), ("hf", 2)):
        parser.error("Assignments are fixed: local component 1, HF component 2")
    if args.location == "hf" and args.export_directory is None:
        parser.error("HF requires a persistent export directory")
    paths = ["scripts/d1c/d1c.py", "scripts/d1c/run_component.py", "scripts/d1c/component_state.py",
             "scripts/d1c/run_state.py", "scripts/d1c/diagnostic_chunks.py", "scripts/d1c/README.md"]
    if git("rev-parse", "HEAD") != args.source or git("status", "--porcelain", "--", *paths):
        raise RuntimeError("Commit the exact source and specification before this fit")
    git("fetch", "--quiet", "origin", "master")
    git("merge-base", "--is-ancestor", args.source, "origin/master")
    directory = d1c.ROOT / "results/d1c" / f"{args.location}-component-{args.component:03d}-20261010"
    directory.mkdir(parents=True, exist_ok=True)
    spec, metadata, selected, archive_hash = imported_upstream(directory)
    for path, expected in spec["sources"].items():
        if hashlib.sha256((d1c.ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Scientific/checkpoint source differs from cloud input: {path}")
    for name, expected in spec["packages"].items():
        if version(name) != expected:
            raise ValueError(f"Local package version differs from cloud: {name}")
    sampler = spec["sampler"]
    d1c.CHAINS, d1c.DRAWS, d1c.TUNE = sampler["chains"], sampler["draws"], sampler["tune"]
    d1c.POST_DRAWS = sampler["contrast_draws"]
    if d1c.POST_DRAWS != d1c.CHAINS*d1c.DRAWS:
        raise ValueError("This assignment requires every production contrast")
    job = spec["job"]
    local_spec = dict(job=job, component=args.component, sampler=sampler,
                      upstream_commit=UPSTREAM_COMMIT, upstream_archive_sha256=archive_hash,
                      upstream_specification_signature=digest(spec), packages=spec["packages"],
                      sources={p: hashlib.sha256((d1c.ROOT / p).read_bytes()).hexdigest() for p in paths},
                      python=sys.version, platform=platform.platform())
    runtime = dict(state="running", source_commit=args.source, pid=os.getpid(), location=args.location,
                   started_at=datetime.now(timezone.utc).isoformat(), specification=local_spec,
                   nice_level=os.getpriority(os.PRIO_PROCESS, 0),
                   note="One assigned component; cloud owns component 0. No full-cut claim.")
    for name in ("memory.max", "memory.peak"):
        path = Path("/sys/fs/cgroup") / name
        runtime["container_" + name.replace(".", "_")] = path.read_text().strip() if path.exists() else None
    def interrupted(signum, frame):
        raise InterruptedError(f"Received signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    started = time.monotonic()
    with ComponentState(directory / "checkpoints", local_spec) as store:
        atomic_json(directory / "runtime.json", runtime)
        if args.export_directory:
            export_files(directory, args.export_directory)
        try:
            result = run_one(job, args.component, metadata, selected, store)
            runtime.update(state="component_complete", diagnostic=result["diagnostic"])
        except BaseException as exc:
            runtime.update(state="interrupted", error=repr(exc))
            raise
        finally:
            runtime.update(ended_at=datetime.now(timezone.utc).isoformat(),
                           elapsed_seconds=time.monotonic()-started,
                           peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                           (1 if sys.platform == "darwin" else 1024))
            atomic_json(directory / "runtime.json", runtime)
            if args.export_directory:
                export_files(directory, args.export_directory)


if __name__ == "__main__":
    main()
