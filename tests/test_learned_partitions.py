import unittest
from tw10.learned_partitions import trial,run,ExperiencePartition,learn_boundary,features,PROTOCOL
from tw10.intervention_lab import PARENT
from tw10.relational_dendrites import RelationalLearner

class LearnedPartitionsTests(unittest.TestCase):
    def test_deterministic_protocol(self):
        a=trial(3,16,16,20,20)
        self.assertEqual(a,trial(3,16,16,20,20))
        self.assertEqual(a['protocol'],PROTOCOL)
        self.assertTrue(a['parent_unchanged'])
    def test_feature_observable_without_answer(self):
        self.assertEqual(len(features((.1,.2),1)),8)
    def test_invalid_bounds(self):
        with self.assertRaises(ValueError):trial(-1)
        with self.assertRaises(ValueError):run([2,2])
    def test_inference_no_parent_mutation(self):
        p=RelationalLearner(PARENT);edge=p.graph[0]
        policy=ExperiencePartition(p,edge,((1.,0.,0.,0.,0.,0.,0.,0.),0.),(0.,1.))
        before=p.state();policy.predict((.1,-.2),0)
        self.assertEqual(before,p.state())
