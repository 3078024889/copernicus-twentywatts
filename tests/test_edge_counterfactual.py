import unittest
from tw10.edge_counterfactual import trial,run,PROTOCOL

class EdgeCounterfactualTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(trial(2),trial(2))
    def test_only_one_edge_and_four_sealed_domains(self):
        t=trial(3)
        self.assertEqual(t['protocol'],PROTOCOL)
        self.assertEqual(len(t['edge_effects']),t['edge_count'])
        self.assertEqual(len(t['sealed_audit']),4)
        self.assertTrue(t['audit_unused_for_edge_choice'])
        self.assertFalse(any('certified' in str(x) and x!=0 for x in [t['certified_ais']]))
    def test_invalid_seed(self):
        with self.assertRaises(ValueError):trial(-1)
    def test_paired_run(self):
        r=run(range(2))
        self.assertEqual(r['seed_count'],2)
        self.assertEqual(r['certified_ais'],0)
        self.assertEqual(len(r['results']),4)
