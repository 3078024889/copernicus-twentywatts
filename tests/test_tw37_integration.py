import unittest
from tw10.active_differentiation import audit, second_probe
from tw10.relational_dendrites import catalogue
from tw10.history_model_selection import compare

class TW37Tests(unittest.TestCase):
    def test_second_probe_repeatable(self):
        v=catalogue()[10]
        self.assertEqual(second_probe(v),second_probe(v))
    def test_probe_partial_scope(self):
        r=audit(20)
        self.assertEqual(r['candidate_count'],20)
        self.assertFalse(r['full_pool'])
        self.assertEqual(r['combined_unique_fingerprints']+r['combined_collisions'],20)
        self.assertEqual(r['certified_independent_algorithms'],0)
    def test_bad_limit(self):
        with self.assertRaises(ValueError):audit(0)
    def test_seed_leakage(self):
        rows=[{'seed':j,'strategy_memory':[{'domain':'linear','proposal_gains':[0]*5,'proposal_comparable':[True]*5}]} for j in range(5)]
        with self.assertRaises(ValueError):compare(rows,rows[:1])
    def test_train_only_fit_and_zero_candidate(self):
        def sample(seed,reward):
            return {'seed':seed,'strategy_memory':[{'domain':'linear','proposal_gains':[reward]*5,'proposal_comparable':[True]*5}]}
        r=compare([sample(i,0.) for i in range(8)],[sample(99,.1)])
        self.assertEqual(r['selected_shrinkage'],0.)
        self.assertFalse(r['certified_predictive_advantage'])
