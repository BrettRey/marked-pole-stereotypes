"""Durable completed-job records for D1c; no sampling or model code."""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def plain(value):
    """JSON values, including NumPy scalars; missing diagnostics stay missing."""
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def encoded(value):
    return json.dumps(plain(value), sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def atomic_json(path, value):
    """Publish a complete JSON file, with both data and rename flushed."""
    path = Path(path)
    payload = encoded(value) + b"\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def job_key(job):
    cell, rep = job["cell"], job["rep"]
    if type(cell) is not int or type(rep) is not int or min(cell, rep) < 0:
        raise ValueError("Jobs require nonnegative integer cell and rep identifiers")
    return f"cell-{cell:04d}-rep-{rep:06d}"


class RunState:
    """One writer, frozen specification, one atomic file per completed job.

    Diagnostic failures and worker exceptions are terminal records. Resumption
    skips them, just as it skips successful jobs. A job without a complete
    record may be repeated with its original seeds after an interruption.
    """

    def __init__(self, path, specification, *, resume=False):
        self.path = Path(path)
        self.specification = plain(specification)
        self.signature = digest(self.specification)
        self.jobs = {job_key(job): job for job in self.specification["jobs"]}
        if len(self.jobs) != len(self.specification["jobs"]):
            raise ValueError("Duplicate job identifiers in run specification")
        if resume and not self.path.is_dir():
            raise FileNotFoundError(f"No run to resume: {self.path}")
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock = (self.path / "writer.lock").open("a+")
        try:
            try:
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Another process owns this run") from exc
            manifest = self.path / "manifest.json"
            if resume:
                saved = json.loads(manifest.read_text())
                if (saved.get("schema") != 1
                        or saved.get("signature") != self.signature
                        or digest(saved.get("specification")) != self.signature):
                    raise ValueError("Run specification changed; refusing to mix results")
                self.manifest = saved
            else:
                if manifest.exists() or any(self.path.glob("cell-*.json")):
                    raise FileExistsError("Run already exists; use explicit resumption")
                self.manifest = dict(
                    schema=1, signature=self.signature,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    specification=self.specification)
                atomic_json(manifest, self.manifest)
            self.records = self._read_records()
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self._lock.closed:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _validate(self, key, record):
        if key not in self.jobs:
            raise ValueError(f"Unexpected completed job: {key}")
        job = self.jobs[key]
        if record.get("job") != job or record.get("signature") != self.signature:
            raise ValueError(f"Completed job belongs to another specification: {key}")
        rows, status = record["rows"], record["status"]
        kind = status["status"]
        if kind not in ("converged", "diagnostic_failure", "exception"):
            raise ValueError(f"Invalid terminal status: {kind}")
        if bool(rows) != (kind != "exception"):
            raise ValueError("Only completed fits have estimate rows")
        for entry in [status, *rows]:
            if any(entry.get(name) != value for name, value in job.items()):
                raise ValueError(f"Result identifiers do not match job: {key}")
        if any(row.get("good") != (kind == "converged") for row in rows):
            raise ValueError(f"Estimate and diagnostic status disagree: {key}")

    def _read_records(self):
        records = {}
        for path in sorted(self.path.glob("cell-*.json")):
            envelope = json.loads(path.read_text())
            record = envelope["record"]
            if envelope.get("sha256") != digest(record):
                raise ValueError(f"Damaged completed-job record: {path.name}")
            self._validate(path.stem, record)
            records[path.stem] = record
        return records

    def pending(self):
        return [job for key, job in self.jobs.items() if key not in self.records]

    def save(self, job, rows, status):
        key = job_key(job)
        path = self.path / f"{key}.json"
        if key in self.records or path.exists():
            raise FileExistsError(f"Completed jobs cannot be overwritten: {key}")
        record = plain(dict(signature=self.signature, job=job, rows=rows, status=status))
        self._validate(key, record)
        atomic_json(path, dict(record=record, sha256=digest(record)))
        self.records[key] = record

    def results(self):
        """Return deterministic job order regardless of worker completion order."""
        records = [self.records[key] for key in self.jobs if key in self.records]
        return ([row for record in records for row in record["rows"]],
                [record["status"] for record in records])
