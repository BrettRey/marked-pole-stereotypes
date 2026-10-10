#!/usr/bin/env bash
set -euo pipefail
RUN_SOURCE=$1
RUN_SHARD=$2
RUN_LOCATION=$3
RUN_NAME=hf-shard-$RUN_SHARD
if [ "$RUN_LOCATION" = hf-joint ]; then RUN_NAME=hf-joint; fi
RUN_OUTPUT=/outputs/20261010/paired-batch/$RUN_NAME
mkdir -p "$RUN_OUTPUT"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt 2>&1 | tee "$RUN_OUTPUT/setup.txt"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec .venv/bin/python -u scripts/d1c/paired_batch.py --source "$RUN_SOURCE" --location "$RUN_LOCATION" --shard "$RUN_SHARD" --export-directory "$RUN_OUTPUT"
