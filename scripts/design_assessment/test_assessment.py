"""Analytical/statistical fixtures; no empirical inputs or model fits."""
import copy
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from budget import estimate, replication_count
from metrics import continuous, performance, rate
import report


def row(truth, mean, lo, hi, good=True):
    return dict(truth=truth, mean=mean, lo90=lo, hi90=hi,
                lo50=(3*lo+hi)/4, hi50=(lo+3*hi)/4, good=good)


class MetricTests(unittest.TestCase):
    def test_exact_boundary_uncertainty_and_missing_cases(self):
        none, all_true = rate([False]*2), rate([True]*2)
        self.assertEqual(none["estimate"], 0)
        self.assertIsNone(none["mcse"])
        self.assertAlmostEqual(none["hi95"], 1-math.sqrt(.025))
        self.assertAlmostEqual(all_true["lo95"], math.sqrt(.025))
        self.assertIsNone(rate([])["estimate"])
        self.assertIsNone(continuous([2])["mcse"])

    def test_analytic_mean_and_reproducible_nonlinear_uncertainty(self):
        x = continuous([1, 3])
        self.assertEqual(x["estimate"], 2)
        self.assertEqual(x["mcse"], 1)
        r = continuous([1, 3], statistic="rmse")
        self.assertAlmostEqual(r["estimate"], math.sqrt(5))
        self.assertGreater(r["mcse"], 0)
        self.assertEqual(r, continuous([1, 3], statistic="rmse"))
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            continuous([float("nan")])

    def test_failure_denominators_selection_and_direction(self):
        rows = [row(1, 1.5, .5, 2), row(1, -.8, -1.5, -.2),
                row(0, .15, .1, .2), row(1, 1, .5, 2, False)]
        result = performance(rows, 5)
        self.assertEqual((result["converged_fits"], result["diagnostic_failures"], result["execution_failures"]), (3, 1, 1))
        metrics = result["metrics"]
        self.assertEqual(metrics["correct_direction_detection"]["estimate"], .5)
        self.assertEqual(metrics["usable_correct_detection_per_attempted_dataset"]["estimate"], .2)
        self.assertEqual(metrics["wrong_sign"]["estimate"], .5)
        self.assertEqual(metrics["selected_wrong_sign"]["n"], 2)
        self.assertAlmostEqual(metrics["selected_exaggeration"]["estimate"], 1.15)
        self.assertEqual(metrics["false_exclusion_at_null"]["events"], 1)
        self.assertEqual(metrics["coverage90"]["events"], 1)
        self.assertEqual(metrics["coverage90"]["n"], 3)

    def test_root_solve_residue_is_not_a_nonzero_effect(self):
        result = performance([row(2.3e-11, 0, -.1, .1)], 1)
        self.assertEqual(result["metrics"]["correct_direction_detection"]["n"], 0)
        self.assertEqual(result["metrics"]["false_exclusion_at_null"]["n"], 1)
        empty = performance([], 2)
        self.assertEqual(empty["execution_failures"], 2)
        self.assertIsNone(empty["metrics"]["bias"]["estimate"])


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = patch.object(report, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.cell = dict(design="uwa", scenario="baseline", target=0., feedback="joint",
                         reliability=0., prior=1., cell=0)
        self.statuses = [dict(self.cell, rep=i, status="converged", data_seed=i+10, fit_seed=i+20)
                         for i in range(2)]
        self.fits = [dict(self.cell, rep=s["rep"], data_seed=s["data_seed"], fit_seed=s["fit_seed"],
                         estimand=e, **row(0, 0, -.2, .2)) for s in self.statuses for e in report.ESTIMANDS]
        self.log = dict(script="scripts/d1c/d1c.py", args=dict(command="pilot"), cells=[self.cell],
            outputs=["fits.csv", "statuses.csv"], sampler=dict(cut_draws=8), statuses=[])
        self.files = [self.root / name for name in ("fits.csv", "statuses.csv", "log.json")]

    def write(self, diagnostics=None):
        for rows, path in zip((self.fits, self.statuses), self.files):
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        self.log["statuses"] = [dict(s, diagnostics=diagnostics or
            [dict(good=True, contrast_good=True, mode="joint")]) for s in self.statuses]
        self.files[2].write_text(json.dumps(self.log))

    def test_complete_run_and_paired_specifications_keep_dataset_denominators(self):
        self.write()
        fits, statuses, _ = report.load_run(*self.files)
        self.assertEqual(len(fits), 8)
        second = [dict(r, feedback="cut", cell=1, mean=r["mean"]+.1,
                       lo90=r["lo90"]-.1, hi90=r["hi90"]+.1) for r in fits]
        more_statuses = [dict(s, feedback="cut", cell=1) for s in statuses]
        summaries, pairs = report.summarize(fits+second, statuses+more_statuses)
        self.assertEqual(len(summaries), 8)
        self.assertTrue(all(s["attempted_datasets"] == 2 for s in summaries))
        self.assertEqual(len(pairs), 4)
        self.assertTrue(all(p["n_paired"] == 2 for p in pairs))
        self.assertAlmostEqual(abs(pairs[0]["bias_difference"]["estimate"]), .1)
        self.assertAlmostEqual(abs(pairs[0]["width90_difference"]["estimate"]), .2)

    def test_duplicate_dataset_and_missing_estimand_are_rejected(self):
        self.fits.pop()
        self.write()
        with self.assertRaisesRegex(ValueError, "Missing whole-fit"):
            report.load_run(*self.files)
        self.fits.append(dict(self.fits[-1], estimand="marking"))
        for s in self.statuses:
            s["data_seed"] = 10
        for r in self.fits:
            r["data_seed"] = 10
        self.write()
        with self.assertRaisesRegex(ValueError, "repeated as an independent"):
            report.load_run(*self.files)

    def test_partial_run_and_conditional_cut_are_rejected(self):
        self.statuses.pop()
        self.write()
        with self.assertRaisesRegex(ValueError, "Run is incomplete"):
            report.load_run(*self.files)
        self.statuses.append(dict(self.statuses[0], rep=1, data_seed=11, fit_seed=21))
        self.cell["feedback"] = "cut"
        for r in self.statuses+self.fits:
            r["feedback"] = "cut"
        self.write([dict(good=True, mode="upstream"),
                    dict(good=True, contrast_good=True, mode="downstream")])
        with self.assertRaisesRegex(ValueError, "conditional cut components"):
            report.load_run(*self.files)

    def test_seed_or_status_disagreement_is_rejected(self):
        self.fits[0]["data_seed"] += 1
        self.write()
        with self.assertRaisesRegex(ValueError, "seed mismatch"):
            report.load_run(*self.files)

    def test_all_execution_failures_still_produce_an_assessment(self):
        for status in self.statuses:
            status["status"] = "exception"
        self.write()
        fits, statuses, _ = report.load_run(None, *self.files[1:])
        summaries, pairs = report.summarize(fits, statuses)
        self.assertEqual(len(summaries), 4)
        self.assertFalse(pairs)
        self.assertTrue(all(s["execution_failures"] == 2 for s in summaries))
        self.assertTrue(all(s["metrics"]["bias"]["estimate"] is None for s in summaries))


class BudgetTests(unittest.TestCase):
    def test_worst_case_replication_and_assumed_rate(self):
        self.assertEqual(replication_count(.025), 400)
        self.assertEqual(replication_count(.05), 100)
        self.assertEqual(replication_count(.1), 25)
        self.assertEqual(replication_count(.025, .9), 144)
        with self.assertRaises(ValueError):
            replication_count(0)

    def test_machine_billing_not_multiplied_by_worker_count(self):
        plan = dict(launch_authorized=False, remaining_authorized_usd=.5,
            platforms=dict(hf=dict(machines=1, workers_per_machine=2,
                                   usd_per_machine_hour=.03, timeout_hours=24)),
            cells=[dict(id="fixture", platform="hf", components=[dict(count=2, seconds=3600, source="analytical fixture")])])
        result = estimate(plan, 10)
        self.assertEqual(result["platforms"]["hf"]["worker_hours"], 20)
        self.assertEqual(result["ideal_elapsed_hours"], 10)
        self.assertAlmostEqual(result["estimated_compute_usd"], .3)
        self.assertAlmostEqual(result["conservative_session_reservation_usd"], .72)
        self.assertFalse(result["reservation_within_budget"])
        self.assertFalse(result["launch_authorized"])
        plan["cells"].append(copy.deepcopy(plan["cells"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            estimate(plan, 10)


if __name__ == "__main__":
    unittest.main()
