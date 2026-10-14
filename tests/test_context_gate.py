import unittest
from tw10.context_gate import trial,run,GatedLearner
from tw10.intervention_lab import PARENT
from tw10.relational_dendrites import RelationalLearner

class ContextGateTests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(trial(0),trial(0))
    def test_parent_not_mutated_and_splits(self):
        r=trial(4)
        self.assertTrue(r['parent_unchanged'])
        self.assertTrue(r['sealed_audit_unused_in_selection'])
        self.assertEqual(set(r['audit']),{'linear','context','interaction','relation'})
    def test_invalid(self):
        with self.assertRaises(ValueError):trial(-1)
        m=RelationalLearner(PARENT)
        with self.assertRaises(ValueError):GatedLearner(m,m.graph[0],(.25,1.))
    def test_run(self):
        r=run(range(2))
        self.assertEqual(r['certified_ais'],0)
        self.assertEqual(r['seed_count'],2)
