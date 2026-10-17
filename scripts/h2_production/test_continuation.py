"""Controller state and budget checks, with no research observations or fits."""
import time
import unittest
from launch_continuation import budget, PAST_JOBS
import test_recovery as fixtures


class ContinuationBudgetTests(unittest.TestCase):
    def test_both_prior_hosts_count_and_credit_limits_deadline(self):
        now = time.time()
        providers = [dict(id=j, status={'stage':'CANCELED'}, durations={'total_secs':3600}) for j in PAST_JOBS]
        costs, seconds, deadline = budget(providers, 1, now, now+100*3600)
        self.assertEqual(set(costs), set(PAST_JOBS))
        self.assertLessEqual(seconds*.04/3600, 1)
        self.assertLessEqual(sum(costs.values())+seconds*.04/3600, 12)
        self.assertLess(deadline, now+100*3600)
        _, _, deadline = budget(providers, 11, now, now+3600)
        self.assertLess(deadline, now+3600)
        providers[1]['status']['stage'] = 'RUNNING'
        with self.assertRaises(ValueError): budget(providers, 11, now, now+3600)


class ContinuationFailureTests(unittest.TestCase):
    setUp = fixtures.RecoveryTests.setUp
    tearDown = fixtures.RecoveryTests.tearDown
    registry = fixtures.RecoveryTests.registry

    def test_post_release_failure_stops_new_claims(self):
        reg, _ = self.registry()
        reg.data['phase'] = 'released'
        job = reg.claim('hf-1')['job']
        reg.failed_before_receipt(job, 'hf-1', 'operational fixture')
        self.assertEqual(reg.data['phase'], 'blocked')
        self.assertEqual(reg.claim('hf-2')['action'], 'stop')


if __name__ == '__main__':
    unittest.main()
