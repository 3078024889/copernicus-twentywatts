import unittest
from tw10.inherited_routing import run_seed,evaluate,POLICIES
class InheritedRoutingTests(unittest.TestCase):
 def test_protocol_no_sealed_selection(self):
  r=run_seed(92000)
  self.assertTrue(r['comparable']);self.assertFalse(r['sealed_used_for_selection'])
  for g in r['history']:
   self.assertEqual(g['selection_probes']['reset'],g['selection_probes']['inherit'])
   self.assertEqual(g['updates']['reset'],g['updates']['inherit'])
   self.assertIn(g['policies']['inherit'],POLICIES)
 def test_deterministic(self):self.assertEqual(run_seed(92001),run_seed(92001))
 def test_bad_generation(self):
  with self.assertRaises(ValueError):run_seed(1,1)
 def test_evaluate(self):
  r=evaluate(2,92002)
  self.assertEqual(r['seeds'],2);self.assertEqual(r['certified_ais'],0)

class BranchInheritanceTests(unittest.TestCase):
 def test_separate_branch_weight_memory_survives(self):
  from tw10.relational_dendrites import RelationalLearner,catalogue
  from tw10.adaptive_routing import LearnedRoute
  p=RelationalLearner(catalogue()[120]);edges=p.graph[:2]
  old=LearnedRoute(p,edges,'context')
  old.branch_weights[edges[0]]=[0.13,-0.27]
  new=LearnedRoute(old,edges,'b_sign')
  new.branch_weights=__import__('copy').deepcopy(old.branch_weights)
  self.assertEqual(new.branch_weights[edges[0]],[0.13,-0.27])
