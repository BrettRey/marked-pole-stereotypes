"""No model fits: test provenance, task identity and resource ceilings."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark as b
import launch_packing as launch


class BenchmarkContract(unittest.TestCase):
    def test_packing_arms_share_scientific_identity(self):
        two, three = b.specification("hf-two"), b.specification("hf-three")
        for key in ("job", "sampler", "packages", "root_seed", "upstream_sha256"):
            self.assertEqual(two[key], three[key])
        self.assertEqual(two["settings"]["components"], three["settings"]["components"])
        self.assertEqual(two["job"]["design"], "nicolas")
        self.assertFalse(two["calibration_replicate"])
        self.assertEqual(two["retries"], 0)

    def test_colab_matches_volunteer_archived_fit(self):
        spec = b.specification("colab-one")
        archived = json.loads((b.ROOT / b.JOINT / "manifest.json").read_text())["specification"]
        self.assertEqual(spec["job"], archived["job"])
        self.assertEqual(spec["sampler"], archived["sampler"])
        self.assertEqual(spec["settings"]["workers"], 1)

    def test_archived_upstream_hash_and_selected_shapes(self):
        with tempfile.TemporaryDirectory() as folder:
            metadata, arrays = b.import_upstream(Path(folder))
            self.assertEqual({k: v.shape for k, v in arrays.items()},
                             {"z": (8, 400), "v": (8, 400), "s": (8, 400), "h": (8, 400, 3)})
            self.assertIn("rng_state", metadata)

    def test_provider_ceiling_and_no_retry(self):
        self.assertAlmostEqual(launch.MAXIMUM_NEW_USD, .72)
        self.assertLessEqual(launch.TOTAL_RESERVED_USD, 15)
        command = launch.command("a"*40, "hf-three", True)
        self.assertEqual(command[command.index("--timeout")+1], "12h")
        self.assertEqual(command[command.index("--attempts")+1], "1")
        self.assertNotIn("--dry-run", command)
        self.assertIn("--dry-run", launch.command("a"*40, "hf-three"))
        with self.assertRaises(ValueError):
            launch.command("a"*40, "hf-four", True)


if __name__ == "__main__":
    unittest.main()
