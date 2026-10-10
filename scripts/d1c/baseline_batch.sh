#!/usr/bin/env bash
set -euo pipefail
RUN_SOURCE=$1
RUN_HOST=$2
RUN_OUTPUT=/outputs/20261010/baseline-batch/$RUN_HOST
mkdir -p "$RUN_OUTPUT"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt 2>&1 | tee "$RUN_OUTPUT/setup.txt"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec .venv/bin/python -u scripts/d1c/baseline_batch.py --source "$RUN_SOURCE" --host "$RUN_HOST" --export-directory "$RUN_OUTPUT"
