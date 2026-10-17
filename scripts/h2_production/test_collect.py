"""Analytic arithmetic checks only; no empirical fixture or fitted model."""
import unittest
import numpy as np
from collect import mixture, predictive_mixture


class MixtureTests(unittest.TestCase):
    def test_equal_weights_and_variance_decomposition(self):
        values=np.broadcast_to(np.arange(8.)[:, None, None], (8, 4, 1000))
        result=mixture(values, 'mean_log_ratio', [2.]*8)
        self.assertEqual(result['all_eight']['mean'], 3.5)
        self.assertEqual(result['first_four']['mean'], 1.5)
        self.assertEqual(result['variance']['within'], 0)
        self.assertEqual(result['variance']['between'], 5.25)
        self.assertEqual(result['leave_one_component_out'][0]['mean'], 4)
        self.assertAlmostEqual(result['within_component_mcse_of_mixture_mean'], 2/np.sqrt(8))

    def test_no_missing_component_or_nonfinite_renormalization(self):
        values=np.ones((8,4,1000))
        with self.assertRaises(ValueError):
            mixture(values[:7], 'mean_log_ratio')
        values[7,0,0]=np.nan
        with self.assertRaises(ValueError):
            mixture(values, 'mean_log_ratio')

    def test_ratio_reference_is_one(self):
        values=np.broadcast_to(np.array([.5]*4+[2.]*4)[:,None,None], (8,4,1000))
        result=mixture(values, 'probability_ratio')
        self.assertEqual(result['all_eight']['p_below_one'], .5)
        self.assertNotIn('p_negative', result['all_eight'])

    def test_predictive_observed_values_remain_component_matched(self):
        observed=[{'x':i} for i in range(8)]
        replicated=[[{'x':i+1} for _ in range(200)] for i in range(8)]
        row=predictive_mixture(replicated, observed)[0]
        self.assertEqual(row['discrepancy']['mean'], 1)
        self.assertEqual(row['discrepancy']['sd'], 0)
        replicated[0][0]['x']=None
        row=predictive_mixture(replicated, observed)[0]
        self.assertEqual(row['n_defined'], 1599)
        self.assertIsNone(row['predictive'])
        self.assertIsNone(row['discrepancy'])


if __name__=='__main__':
    unittest.main(verbosity=2)
