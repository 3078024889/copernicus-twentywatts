import unittest
from tw10.twin_backtest import bootstrap_interval,run
class TwinBacktestTests(unittest.TestCase):
    def test_deterministic_statistics(self):
        self.assertEqual(bootstrap_interval([1,-1,2,0],100),bootstrap_interval([1,-1,2,0],100))
    def test_computation_difference_disclosed(self):
        r=run(range(2),generations=2,proposals=2)
        self.assertFalse(r['cross_policy_equal_selection_compute'])
        self.assertTrue(r['same_task_rows'])
        self.assertEqual(r['certified_ais'],0)
    def test_duplicate_seeds_forbidden(self):
        with self.assertRaises(ValueError):run([4,4])
