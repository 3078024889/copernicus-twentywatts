import unittest
from tw10.conflict_branching import conflict_edge, EdgeBranchLearner, run_seed, evaluate
from tw10.relational_dendrites import RelationalLearner, catalogue

class ConflictBranchingTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(run_seed(71001), run_seed(71001))
    def test_budget_and_sealed(self):
        r=run_seed(71000)
        if r['branch_created']:
            self.assertTrue(r['updates_equal'])
            self.assertEqual(r['branch_extra_parameters'],1)
            self.assertFalse(r['sealed_used_for_selection'])
            self.assertEqual(set(r['audits']), {'linear','interaction','context','relation'})
        self.assertFalse(r['certified'])
    def test_gate_routing_distinct(self):
        m=RelationalLearner(catalogue()[120]);e=m.graph[0]
        contextual=EdgeBranchLearner(m,e,'context')
        feature=EdgeBranchLearner(m,e,'feature')
        self.assertNotEqual(contextual.gate((-.5,.2),1),feature.gate((-.5,.2),1))
        self.assertEqual(contextual.model.state(),m.state())
    def test_forward_uses_branch_weights_and_restores_parent_edge(self):
        m=RelationalLearner(catalogue()[120]);e=m.graph[0]
        b=EdgeBranchLearner(m,e,'context')
        old=b.model.syn[e]
        b.weights=[-1.,1.]
        _=b.predict((.3,.4),1)
        self.assertEqual(b.model.syn[e],old)
        self.assertEqual(b.weights,[-1.,1.])
    def test_no_conflict(self):
        m=RelationalLearner(catalogue()[0]);e,s=conflict_edge(m,[])
        self.assertIsNone(e);self.assertEqual(s,0.)
    def test_evaluation(self):
        r=evaluate(2,71900)
        self.assertEqual(r['trials'],2)
        self.assertEqual(r['certified_ais'],0)
        self.assertIn('relation',r['results'])
        with self.assertRaises(ValueError):evaluate(1)

class ReplayRoutingTests(unittest.TestCase):
    def test_replay_uses_its_own_context(self):
        # An old context=0 memory replayed while training context=1 must use
        # the old context's branch, not borrow the current observation's route.
        m=RelationalLearner(catalogue()[120]);e=m.graph[0]
        b=EdgeBranchLearner(m,e,'context')
        b.weights=[-.75,.75]
        b.model.memory.append(((-.8,.7),1,0,.9))
        b.model.experience=4
        before=b.model.updates
        b.learn((.7,.4),0,1)
        self.assertEqual(b.model.updates-before,2)
        self.assertEqual(b.model.syn[e],m.syn[e])
        self.assertNotEqual(b.weights[0],-.75)
        self.assertNotEqual(b.weights[1],.75)
