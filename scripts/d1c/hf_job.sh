#!/usr/bin/env bash
# Called inside the fixed official Python image after checkout of SOURCE.
set -eu
SOURCE=$1
OUTPUT=/outputs/20261010/component-002
mkdir -p "$OUTPUT"
# A fixed package set, installed once. No floating-version fallback.
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt > "$OUTPUT/setup.txt" 2>&1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -u scripts/d1c/run_component.py --source "$SOURCE" \
    --location hf --component 2 --export-directory "$OUTPUT" > "$OUTPUT/worker-stdout.txt" 2>&1
