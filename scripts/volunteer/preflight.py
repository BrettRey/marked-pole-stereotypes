#!/usr/bin/env python3
"""Check a volunteer Mac's environment without generating study data or fitting a model."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = "3.14.8"


def command(args, *, timeout=30, env=None):
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} exited with {result.returncode}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "volunteer-readiness.json")
    args = parser.parse_args()
    started = time.monotonic()
    checks = {}
    report = dict(timestamp=datetime.now(timezone.utc).isoformat(),
                  purpose="environment readiness only; no generated study data or model fit",
                  platform=platform.system(), architecture=platform.machine(),
                  macos=platform.mac_ver()[0], python=platform.python_version(),
                  initial_worker_limit=1, scientific_batch_assigned=False, checks=checks)
    checks["apple_silicon_macos"] = platform.system() == "Darwin" and platform.machine() == "arm64"
    checks["python_version"] = platform.python_version() == PYTHON
    try:
        report["memory_gib"] = int(command(["/usr/sbin/sysctl", "-n", "hw.memsize"])) / 2**30
        report["chip"] = command(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"])
        checks["memory_at_least_16_gib"] = report["memory_gib"] >= 16
    except Exception as error:
        checks["memory_at_least_16_gib"] = False
        report["hardware_error"] = type(error).__name__
    report["free_disk_gib"] = round(shutil.disk_usage(ROOT).free / 2**30, 1)
    checks["setup_disk_at_least_5_gib"] = report["free_disk_gib"] >= 5
    requirements = ROOT / "requirements-d1.txt"
    report["requirements_sha256"] = hashlib.sha256(requirements.read_bytes()).hexdigest()
    versions, mismatches = {}, {}
    for line in requirements.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==", 1)
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        versions[name] = actual
        if actual != expected:
            mismatches[name] = {"expected": expected, "installed": actual}
    report["packages"] = versions
    report["package_mismatches"] = mismatches
    checks["pinned_packages"] = not mismatches
    try:
        report["source_commit"] = command(["git", "rev-parse", "HEAD"])
        report["source_dirty"] = bool(command(["git", "status", "--porcelain", "--",
                                              "requirements-d1.txt", "scripts/volunteer/preflight.py",
                                              "scripts/d1/bin/clang++"]))
        checks["source_files_clean"] = not report["source_dirty"]
    except Exception as error:
        checks["source_files_clean"] = False
        report["source_error"] = type(error).__name__
    try:
        command(["/usr/bin/xcrun", "--find", "clang++"])
        report["compiler"] = command(["/usr/bin/clang++", "--version"]).splitlines()[0]
        checks["compiler_present"] = True
    except Exception as error:
        checks["compiler_present"] = False
        report["compiler_error"] = type(error).__name__
    if checks["pinned_packages"] and checks["compiler_present"]:
        env = dict(os.environ)
        env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   MPLCONFIGDIR=str(ROOT / ".cache" / "volunteer-matplotlib"),
                   NUMBA_CACHE_DIR=str(ROOT / ".cache" / "volunteer-numba"),
                   PYTENSOR_FLAGS=f"base_compiledir={ROOT / '.cache' / 'volunteer-pytensor'},cxx={ROOT / 'scripts/d1/bin/clang++'}")
        # Scalar arithmetic verifies the compiler path; it supplies no study observations.
        smoke = """import numpy, pymc, nutpie, numba, pytensor
import pytensor.tensor as pt
x = pt.dscalar('x')
f = pytensor.function([x], 2*x+1, mode='FAST_RUN')
assert float(f(2.0)) == 5.0
print('imports and scalar compiler check passed')
"""
        try:
            command([sys.executable, "-c", smoke], timeout=180, env=env)
            checks["imports_and_scalar_compile"] = True
        except Exception as error:
            checks["imports_and_scalar_compile"] = False
            report["smoke_error"] = type(error).__name__ + ": " + str(error)
    else:
        checks["imports_and_scalar_compile"] = False
    report["ready_for_assignment"] = all(checks.values())
    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n")
    for name, good in checks.items():
        print(f"{'PASS' if good else 'FAIL'} {name}")
    print("Readiness report:", args.output)
    print("No study batch has been run. Initial worker limit: one.")
    return 0 if report["ready_for_assignment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
