import unittest
from tw10.adaptive_routing import LearnedRoute,run_seed,evaluate,POLICIES
from tw10.relational_dendrites import RelationalLearner,catalogue

class AdaptiveRoutingTests(unittest.TestCase):
    def test_gates(self):
        p=RelationalLearner(catalogue()[120]);e=p.graph[:2]
        self.assertEqual(LearnedRoute(p,e,'context').gate((-.2,.4),1),1)
        self.assertEqual(LearnedRoute(p,e,'a_sign').gate((-.2,.4),1),0)
        self.assertEqual(LearnedRoute(p,e,'b_sign').gate((-.2,.4),0),1)
        self.assertEqual(LearnedRoute(p,e,'product_sign').gate((-.2,.4),0),0)
        self.assertEqual(LearnedRoute(p,e,'xor_sign').gate((-.2,.4),0),1)
    def test_sealed_no_selection(self):
        r=run_seed(91000)
        self.assertFalse(r['sealed_used_for_selection'])
        self.assertFalse(r['certified'])
        if r['comparable']:
            self.assertEqual(len(set(r['budget_updates'].values())),1)
            self.assertIn(r['selected'],POLICIES)
            self.assertEqual(r['selection_probes'],640)
    def test_deterministic(self):
        a=run_seed(91001);b=run_seed(91001)
        for d in (a,b):d.pop('wall_seconds_unmatched',None)
        self.assertEqual(a,b)
    def test_evaluate(self):
        r=evaluate(2,91010)
        self.assertEqual(r['trials'],2)
        self.assertEqual(r['certified_ais'],0)
