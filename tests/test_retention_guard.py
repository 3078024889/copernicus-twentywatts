import unittest
from tw10.retention_guard import evaluate, run_seed, choose, PROTOCOL
from tw10.relational_dendrites import catalogue

class RetentionGuardTests(unittest.TestCase):
    def test_determinism_and_budget(self):
        v=catalogue()[125]
        a=run_seed(v, 63000, {}, 2)
        self.assertEqual(a, run_seed(v,63000,{},2))
        self.assertTrue(a['budget_operations_equal'])
        self.assertFalse(a['certified'])
    def test_no_sealed_selection(self):
        r=run_seed(catalogue()[9], 63001, {}, 3)
        self.assertTrue(all(not e['sealed_used_in_selection'] for arm in r['traces'].values() for e in arm))
        for generation in range(3):
            self.assertEqual(r['traces']['control'][generation]['probe_budget'],r['traces']['protected'][generation]['probe_budget'])
    def test_history_choice_only(self):
        self.assertEqual(choose('linear',{('linear','memory'):(.5,30)},13,list(range(5))),3)
    def test_invalid(self):
        with self.assertRaises(ValueError):run_seed(catalogue()[0], 1, {}, 1)
        with self.assertRaises(ValueError):evaluate([],0)
