import unittest
from tw10.association_partitions import trial,run,partition_key,PartitionedLearner,PROTOCOL
from tw10.intervention_lab import PARENT
from tw10.relational_dendrites import RelationalLearner

class AssociationPartitionTests(unittest.TestCase):
    def test_partition_key(self):
        self.assertEqual(partition_key((.1,-.5),0,'interaction_sign'),0)
        self.assertEqual(partition_key((.1,.5),0,'interaction_sign'),1)
        with self.assertRaises(ValueError):partition_key((.1,.5),0,'invalid')
    def test_immutable_inference(self):
        model=RelationalLearner(PARENT);edge=model.graph[0]
        policy=PartitionedLearner(model,edge,'context',(0.,1.))
        before=model.syn[edge];policy.predict((.4,-.2),0)
        self.assertEqual(model.syn[edge],before)
    def test_determinism(self):
        a=trial(7,training_count=16,calibration_count=16,selection_count=20,audit_count=20)
        self.assertEqual(a,trial(7,training_count=16,calibration_count=16,selection_count=20,audit_count=20))
        self.assertEqual(a['protocol'],PROTOCOL)
        self.assertTrue(a['parent_unchanged'])
    def test_validation(self):
        with self.assertRaises(ValueError):trial(-1)
        with self.assertRaises(ValueError):run([1,1])
