import unittest
from tw10.cooperative_branches import _MultiRouted,rank_conflicts,run_seed,evaluate
from tw10.relational_dendrites import RelationalLearner,catalogue

class CooperativeBranchTests(unittest.TestCase):
    def test_deterministic_seed(self):
        a=run_seed(81000);b=run_seed(81000)
        # wall-clock measurement is intentionally not deterministic
        a.pop('training_wall_seconds_not_budget_matched',None)
        b.pop('training_wall_seconds_not_budget_matched',None)
        self.assertEqual(a,b)
    def test_budget_and_sealing(self):
        r=run_seed(81001)
        self.assertFalse(r['sealed_used_for_selection'])
        self.assertFalse(r['certified'])
        if r['comparable']:
            self.assertEqual(len(set(r['budget_updates'].values())),1)
            self.assertEqual(r['added_weights_multi'],len(r['edges']))
    def test_routing_and_replay(self):
        m=RelationalLearner(catalogue()[120]);edges=m.graph[:3]
        model=_MultiRouted(m,edges,'context')
        for e in edges:model.branch_weights[e]=[-.7,.7]
        model.memory.append(((-.3,.5),1,0,.9))
        model.experience=4
        before=model.updates
        model.learn((.5,.2),0,1,replay_policy='fixed')
        self.assertEqual(model.updates-before,2)
        for e in edges:
            self.assertNotEqual(model.branch_weights[e][0],-.7)
            self.assertNotEqual(model.branch_weights[e][1],.7)
            self.assertEqual(model.syn[e],m.syn[e])
    def test_no_diagnostics(self):
        self.assertEqual(rank_conflicts(RelationalLearner(catalogue()[120]),[]),[])
    def test_summary(self):
        r=evaluate(2,81005)
        self.assertEqual(r['trials'],2)
        self.assertIn('relation',r['results'])
        self.assertEqual(r['certified_ais'],0)
