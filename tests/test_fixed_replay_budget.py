import unittest
from tw10.relational_dendrites import catalogue, RelationalLearner, tasks
from tw10.prospective_evolution import experiment, PROTOCOL

class FixedReplayBudgetTests(unittest.TestCase):
    def test_all_memory_variants_equal_updates_under_fixed_policy(self):
        models=[RelationalLearner(catalogue()[i]) for i in (0,1,2,3,4,5,1297,7776)]
        for x,y,c in tasks(741,'relation',48):
            for m in models:m.learn(x,y,c,replay_policy='fixed')
        self.assertEqual({m.updates for m in models},{57})
        self.assertEqual({m.experience for m in models},{48})
    def test_native_policy_still_differs_by_memory(self):
        models=[RelationalLearner(catalogue()[i]) for i in (0,6,12)]
        for x,y,c in tasks(741,'linear',48):
            for m in models:m.learn(x,y,c)
        self.assertGreater(len({m.updates for m in models}),1)
    def test_prospective_budget_is_precommitted(self):
        result=experiment(catalogue()[1599],51000,{},4)
        self.assertEqual(result['protocol'],PROTOCOL)
        self.assertTrue(result['candidate_update_budget_equal'])
        self.assertTrue(result['all_selected_proposals_comparable'])
        self.assertEqual(result['compute_updates']['random'],result['compute_updates']['meta'])
        self.assertEqual({e['replay_updates'] for track in result['traces'].values() for e in track},{9,10})

if __name__=='__main__':unittest.main()
