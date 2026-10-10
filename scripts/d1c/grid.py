#!/usr/bin/env python3
"""Run or resume the unchanged D1c design with durable completed-job records.

Sampler budgets are fixed at launch and retained on resumption. No diagnostic
failure or ordinary worker exception is retried automatically. No data from
the research sources are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import platform
import re
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import d1c
import pandas as pd

from run_state import RunState, atomic_json


def git(*arguments):
    return subprocess.run(["git", *arguments], cwd=d1c.ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def configure_sampler(draws, tune, upstream_draws=None):
    # The worker calls d1c.fit directly. Use every contrast already computed
    # for diagnostics, rather than discarding most for summary statistics.
    d1c.DRAWS, d1c.TUNE = draws, tune
    d1c.UPSTREAM_DRAWS = draws if upstream_draws is None else upstream_draws
    d1c.POST_DRAWS = d1c.CHAINS * draws


def specification(reps, draws, tune, upstream_draws=None):
    cells = list(d1c.cells())
    # Spread the first replicate across the whole multiverse before starting
    # the next. Scheduling changes neither data nor fit seeds.
    jobs = [dict(cell, rep=rep) for rep in range(reps) for cell in cells]
    paths = ("scripts/d1c/d1c.py", "scripts/d1c/grid.py", "scripts/d1c/run_state.py",
             "scripts/d1c/diagnostic_chunks.py",
             "scripts/d1/bin/clang++")
    packages = ("numpy", "pandas", "scipy", "pymc", "pytensor", "nutpie", "arviz",
                "numba", "llvmlite", "xarray")
    return dict(
        jobs=jobs, cells=cells, replicates_per_cell=reps, root_seed=d1c.SEED,
        sampler=dict(draws=draws, tune=tune, chains=d1c.CHAINS, cores=1,
                     upstream_draws=draws if upstream_draws is None else upstream_draws,
                     target_accept=.95, cut_draws=d1c.CUT_DRAWS,
                     contrast_draws=d1c.CHAINS*draws,
                     contrast_diagnostic_draws=d1c.CHAINS*draws),
        sources={path: hashlib.sha256((d1c.ROOT / path).read_bytes()).hexdigest()
                 for path in paths},
        packages={package: version(package) for package in packages},
        python=sys.version, platform=platform.platform(),
        order="replicate, then original cell order", retries="none")


def completed_jobs(jobs, workers, draws, tune, *, upstream_draws=None, fit=d1c.fit):
    """Bound queued work; a broken pool leaves uncompleted jobs pending.

    Ordinary exceptions returned by a live worker become terminal records.
    An abruptly lost worker is an interrupted computation, not evidence that
    every queued job failed. Resumption preserves already returned records.
    """
    remaining = iter(jobs)
    pool = ProcessPoolExecutor(max_workers=workers,
                               mp_context=multiprocessing.get_context("spawn"),
                               initializer=configure_sampler,
                               initargs=(draws, tune, upstream_draws))
    try:
        pending = {}

        def submit():
            job = next(remaining, None)
            if job is not None:
                pending[pool.submit(fit, job)] = job

        for _ in range(workers):
            submit()
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            interrupted = None
            for future in done:
                job = pending.pop(future)
                try:
                    rows, status = future.result()
                except BrokenProcessPool as exc:
                    interrupted = exc
                    continue
                except Exception as exc:
                    rows = []
                    status = dict(**job, status="exception", error=repr(exc),
                                  fit_seed=d1c.seed(2, job["cell"], job["rep"]))
                yield job, rows, status
            if interrupted is not None:
                raise interrupted
            # Save every completed result before submitting further work.
            for _ in range(len(done)):
                submit()
    except BaseException:
        # Python 3.14's public API; do not leave expensive workers running
        # after a write failure, interruption or early generator close.
        pool.terminate_workers()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


def atomic_csv(path, frame):
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        with temporary.open("w") as stream:
            frame.to_csv(stream, index=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish(store, stamp, sessions, *, state, error=None):
    """Rebuild inspectable outputs from the authoritative completion records."""
    rows, statuses = store.results()
    output = d1c.ROOT / "results/d1c"
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    if rows:
        frame = pd.DataFrame(rows)
        summary, failures = d1c.summarize(frame, statuses)
        for name, table in (("fits", frame), ("summary", summary)):
            path = output / f"run-{stamp}-{name}.csv"
            atomic_csv(path, table)
            paths.append(str(path.relative_to(d1c.ROOT)))
    else:
        failures = pd.DataFrame(statuses)
    if statuses:
        path = output / f"run-{stamp}-failures.csv"
        atomic_csv(path, failures.drop(columns=["diagnostics"], errors="ignore"))
        paths.append(str(path.relative_to(d1c.ROOT)))
    counts = {name: sum(status["status"] == name for status in statuses)
              for name in ("converged", "diagnostic_failure", "exception")}
    spec = store.specification
    log = dict(
        timestamp=stamp, script="scripts/d1c/grid.py", state=state, error=error,
        updated_at=datetime.now(timezone.utc).isoformat(),
        signature=store.signature, created_at=store.manifest["created_at"],
        sources=spec["sources"], packages=spec["packages"], python=spec["python"],
        platform=spec["platform"], sampler=spec["sampler"], root_seed=spec["root_seed"],
        cells=spec["cells"], replicates_per_cell=spec["replicates_per_cell"],
        job_order=spec["order"], retries=spec["retries"], sessions=sessions,
        completed=len(statuses), total=len(store.jobs),
        pending=len(store.jobs)-len(statuses), counts=counts,
        statuses=statuses, outputs=paths,
        recovery=str(store.path.relative_to(d1c.ROOT)),
        note="Artificial data only. Completed diagnostic failures and exceptions are retained and skipped on resume.")
    atomic_json(d1c.ROOT / "logs" / f"d1c-grid-{stamp}.json", log)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--reps", type=int, required=True)
    start.add_argument("--draws", type=int, default=d1c.DRAWS)
    start.add_argument("--tune", type=int, default=d1c.TUNE)
    start.add_argument("--upstream-draws", type=int,
                       help="retained draws for upstream cut fits; defaults to --draws")
    start.add_argument("--workers", type=int, default=3)
    resume = sub.add_parser("resume")
    resume.add_argument("stamp")
    resume.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    is_resume = args.command == "resume"
    if is_resume:
        stamp = args.stamp
        if not re.fullmatch(r"\d{8}T\d{12}Z", stamp):
            parser.error("stamp must be the UTC identifier printed by grid.py")
        saved = json.loads((d1c.SCRATCH / "grid" / stamp / "manifest.json").read_text())
        old = saved["specification"]
        reps, draws, tune = (old["replicates_per_cell"], old["sampler"]["draws"],
                             old["sampler"]["tune"])
        upstream_draws = old["sampler"]["upstream_draws"]
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        reps, draws, tune = args.reps, args.draws, args.tune
        upstream_draws = draws if args.upstream_draws is None else args.upstream_draws
    if min(reps, draws, tune, upstream_draws) < 1 or draws < d1c.POST_DRAWS // d1c.CHAINS:
        parser.error("positive budgets and enough draws for contrast subsampling are required")
    spec = specification(reps, draws, tune, upstream_draws)
    # Freeze the publication state before any fit. Runtime output may then
    # legitimately dirty logs and results without changing the sampled code.
    tracked = [*spec["sources"], "scripts/d1c/README.md"]
    dirty = git("status", "--porcelain", "--", *tracked)
    if dirty:
        raise RuntimeError(f"Commit sampler code and README before a grid launch:\n{dirty}")
    remote_head = git("ls-remote", "origin", "HEAD").split()[0]
    head = git("rev-parse", "HEAD")
    if remote_head != head:
        raise RuntimeError("Push the launch commit before starting or resuming the grid")
    path = d1c.SCRATCH / "grid" / stamp
    (d1c.ROOT / "logs").mkdir(exist_ok=True)
    with RunState(path, spec, resume=is_resume) as store:
        log_path = d1c.ROOT / "logs" / f"d1c-grid-{stamp}.json"
        sessions = json.loads(log_path.read_text())["sessions"] if log_path.exists() else []
        session = dict(
            started_at=datetime.now(timezone.utc).isoformat(), command=sys.argv,
            pid=os.getpid(), workers=args.workers, git_sha=head,
            remote_head=remote_head, restored_jobs=len(store.records),
            environment={name: os.environ.get(name) for name in
                         ("PYTENSOR_FLAGS", "NUMBA_CACHE_DIR", "OMP_NUM_THREADS",
                          "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")})
        sessions.append(session)
        print(f"D1c grid {stamp}: {len(store.records)}/{len(store.jobs)} completed; "
              f"{args.workers} workers; {draws} production / {upstream_draws} upstream "
              f"retained + {tune} warmup per chain", flush=True)
        publish(store, stamp, sessions, state="running")
        started = time.perf_counter()
        try:
            with closing(completed_jobs(store.pending(), args.workers, draws, tune,
                                        upstream_draws=upstream_draws)) as jobs:
                for job, rows, status in jobs:
                    store.save(job, rows, status)
                    publish(store, stamp, sessions, state="running")
                    print(f"completed {len(store.records)}/{len(store.jobs)}: "
                          f"cell {job['cell']} rep {job['rep']} {status['status']}; "
                          f"session {time.perf_counter()-started:.1f}s", flush=True)
        except BaseException as exc:
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            session["elapsed_seconds"] = time.perf_counter()-started
            publish(store, stamp, sessions, state="interrupted", error=repr(exc))
            raise
        session["ended_at"] = datetime.now(timezone.utc).isoformat()
        session["elapsed_seconds"] = time.perf_counter()-started
        publish(store, stamp, sessions, state="complete")
        print(f"complete: {log_path.relative_to(d1c.ROOT)}", flush=True)


if __name__ == "__main__":
    main()
