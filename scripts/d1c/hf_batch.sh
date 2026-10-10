#!/usr/bin/env bash
set -euo pipefail
SOURCE=$1
OUTPUT=/outputs/20261010
mkdir -p "$OUTPUT/batch-004-006"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt 2>&1 | tee "$OUTPUT/batch-004-006/setup.txt"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec .venv/bin/python -u scripts/d1c/hf_batch.py --source "$SOURCE" --output "$OUTPUT"
