"""Collection accepts intact assigned results and keeps diagnostic failures."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import collect_parallel as collection
from component_state import ComponentState
from run_state import atomic_json, digest


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.job = dict(cell=10, rep=0, feedback="cut")
        self.spec = dict(job=self.job, root_seed=20261009,
                         sampler=dict(chains=4, draws=4000, tune=2000))
        upstream = self.root / "upstream"
        with ComponentState(upstream, self.spec) as store:
            store.save("upstream", {}, {"z": np.zeros((8, 400))})
            self.upstream_record = store.records["upstream"]
        self.canonical = collection.json_file(upstream / "manifest.json")
        self.addCleanup(patch.stopall)
        patch.object(collection, "UPSTREAM_SHA", self.upstream_record["archive_sha256"]).start()
        self.assigned = dict(self.spec, component=1, upstream_archive_sha256=self.upstream_record["archive_sha256"],
                             upstream_commit=collection.UPSTREAM_COMMIT,
                             upstream_specification_signature=self.canonical["signature"])
        self.metadata = dict(diagnostic=dict(seed=int(np.random.SeedSequence(20261009, spawn_key=(4, 10, 0, 1)).generate_state(1)[0]),
                                            mode="downstream", draws=4000, tune=2000,
                                            good=False, contrast_good=True, rhat=1.03, ess=70, divergences=0))
        self.arrays = {name: np.arange(16000, dtype=float) for name in collection.NAMES}

    def save_component(self, *, metadata=None, arrays=None):
        with ComponentState(self.root / "checkpoints", self.assigned) as store:
            store.save("downstream-001", metadata or self.metadata, arrays or self.arrays)

    def test_verified_failure_survives_collection_and_source_removal(self):
        self.save_component()
        record, arrays = collection.validate_assignment(self.root, "local", 1, self.canonical)
        self.assertFalse(record["metadata"]["diagnostic"]["good"])
        for name in collection.NAMES:
            np.testing.assert_array_equal(arrays[name], self.arrays[name])
        with tempfile.TemporaryDirectory() as destination:
            with patch.object(collection, "OUTPUT", Path(destination)):
                collection.preserve(self.root, "local", 1)
                import shutil
                shutil.rmtree(self.root)
                restored = collection.validate_assignment(Path(destination) / "collected/local", "local", 1, self.canonical)
                self.assertEqual(restored[0], record)

    def test_incomplete_archive_is_not_accepted(self):
        with ComponentState(self.root / "checkpoints", self.assigned):
            (self.root / "checkpoints/component-downstream-001.npz").write_bytes(b"unfinished")
        self.assertIsNone(collection.validate_assignment(self.root, "local", 1, self.canonical))

    def test_corrupt_archive_and_wrong_manifest_are_rejected(self):
        self.save_component()
        with self.assertRaisesRegex(ValueError, "assignment differs"):
            collection.validate_assignment(self.root, "local", 2, self.canonical)
        archive = self.root / "checkpoints/component-downstream-001.npz"
        archive.write_bytes(b"damaged")
        with self.assertRaisesRegex(ValueError, "Damaged component archive"):
            collection.validate_assignment(self.root, "local", 1, self.canonical)

    def test_seed_and_draw_budget_are_checked_beyond_checksums(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["diagnostic"]["seed"] += 1
        self.save_component(metadata=metadata)
        with self.assertRaisesRegex(ValueError, "diagnostic does not match"):
            collection.validate_assignment(self.root, "local", 1, self.canonical)
        import shutil
        shutil.rmtree(self.root / "checkpoints")
        self.save_component(arrays={name: value[:-1] for name, value in self.arrays.items()})
        with self.assertRaisesRegex(ValueError, "16,000 draws"):
            collection.validate_assignment(self.root, "local", 1, self.canonical)


if __name__ == "__main__":
    unittest.main()
