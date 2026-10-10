"""Atomic D1c component checkpoints, with exact latent/contrast draw recovery."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from run_state import atomic_json, digest, plain


class ComponentLimitReached(Exception):
    """A prespecified partial-cut benchmark reached its component boundary."""


def contrast_arrays(rows):
    return {name: np.asarray([row[name] for row in rows], dtype=np.float64)
            for name in rows[0]}


def contrast_rows(arrays):
    lengths = {len(value) for value in arrays.values()}
    if len(lengths) != 1 or not lengths or any(value.ndim != 1 for value in arrays.values()):
        raise ValueError("Contrast archives require equal-length scalar draw arrays")
    return [dict(zip(arrays, values)) for values in zip(*arrays.values())]


def contrast_summaries(arrays):
    return {name: dict(draws=len(values), mean=float(np.mean(values)),
                       median=float(np.median(values)),
                       lo50=float(np.quantile(values, .25)),
                       hi50=float(np.quantile(values, .75)),
                       lo90=float(np.quantile(values, .05)),
                       hi90=float(np.quantile(values, .95)))
            for name, values in arrays.items()}


class ComponentState:
    """One writer per job; retain failed diagnostics, reject altered records."""

    def __init__(self, path, specification):
        self.path = Path(path)
        self.specification = plain(specification)
        self.signature = digest(self.specification)
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock = (self.path / "writer.lock").open("a+")
        try:
            try:
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Another process owns these components") from exc
            path = self.path / "manifest.json"
            if path.exists():
                saved = json.loads(path.read_text())
                if (saved.get("schema") != 1 or saved.get("signature") != self.signature
                        or digest(saved.get("specification")) != self.signature):
                    raise ValueError("Component specification changed; refusing resumption")
            else:
                if list(self.path.glob("component-*.json")):
                    raise ValueError("Component records have no manifest")
                atomic_json(path, dict(schema=1, signature=self.signature,
                                      specification=self.specification,
                                      created_at=datetime.now(timezone.utc).isoformat()))
            self.records = {p.stem.removeprefix("component-"): self._record(p)
                            for p in sorted(self.path.glob("component-*.json"))}
            self.publish()
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self._lock.closed:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def validate_key(key):
        if not re.fullmatch(r"upstream|joint|downstream-[0-9]{3}", key):
            raise ValueError("Invalid component key")

    def _record(self, path):
        envelope = json.loads(path.read_text())
        record = envelope["record"]
        key = path.stem.removeprefix("component-")
        self.validate_key(key)
        if (envelope.get("sha256") != digest(record)
                or record.get("signature") != self.signature or record.get("key") != key):
            raise ValueError(f"Damaged or incompatible component record: {key}")
        if record.get("archive") != f"component-{key}.npz":
            raise ValueError("Invalid component archive path")
        return record

    def load(self, key):
        self.validate_key(key)
        if key not in self.records:
            return None
        record = self.records[key]
        path = self.path / record["archive"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["archive_sha256"]:
            raise ValueError(f"Damaged component archive: {key}")
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        description = {name: dict(shape=list(value.shape), dtype=str(value.dtype))
                       for name, value in arrays.items()}
        if description != record["arrays"]:
            raise ValueError(f"Component array schema changed: {key}")
        return record["metadata"], arrays

    def save(self, key, metadata, arrays):
        self.validate_key(key)
        if key in self.records:
            raise FileExistsError(f"Completed components cannot be overwritten: {key}")
        arrays = {name: np.asarray(value) for name, value in arrays.items()}
        if not arrays or any(value.dtype.hasobject for value in arrays.values()):
            raise ValueError("Only nonempty numeric-array archives are supported")
        destination = self.path / f"component-{key}.npz"
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=self.path)
        try:
            with os.fdopen(fd, "wb") as stream:
                np.savez_compressed(stream, **arrays)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        record = plain(dict(
            key=key, signature=self.signature, metadata=metadata,
            saved_at=datetime.now(timezone.utc).isoformat(),
            archive=destination.name,
            archive_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
            arrays={name: dict(shape=list(value.shape), dtype=str(value.dtype))
                    for name, value in arrays.items()}))
        # The JSON record is the commit marker. An orphan archive left by an
        # interruption is not a completed component and can be replaced.
        atomic_json(self.path / f"component-{key}.json",
                    dict(record=record, sha256=digest(record)))
        self.records[key] = record
        self.publish()
        print(f"saved component {key}: {self.path}", flush=True)

    def publish(self):
        atomic_json(self.path / "progress.json", dict(
            signature=self.signature, job=self.specification["job"],
            updated_at=datetime.now(timezone.utc).isoformat(),
            completed_components=list(self.records),
            components={key: record["metadata"] for key, record in self.records.items()},
            note="Component summaries are conditional results; an incomplete cut is not a full cut estimate."))
