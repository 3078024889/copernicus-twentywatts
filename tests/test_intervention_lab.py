import unittest
from tw10.intervention_lab import trial,run,INTERVENTIONS,aligned_state,PARENT
from tw10.relational_dendrites import RelationalLearner

class InterventionLabTest(unittest.TestCase):
    def test_ablation_changes_only_declared_operator(self):
        original=RelationalLearner(PARENT)
        for name,changes in INTERVENTIONS.items():
            altered=aligned_state(original,name,2)
            for key,value in changes.items():self.assertEqual(getattr(altered.v,key),value)
            self.assertEqual(original.v,PARENT)
    def test_trial_deterministic_and_sealed(self):
        a=trial(3,count=8,audit_count=8)
        self.assertEqual(a,trial(3,count=8,audit_count=8))
        self.assertTrue(a['sealed_audit_not_used_for_selection'])
        self.assertEqual(set(a['interventions']),set(INTERVENTIONS))
        self.assertEqual(a['certified_ais'],0)
    def test_reject_insufficient_seeds(self):
        with self.assertRaises(ValueError):run([1,1])
    def test_paired_summary(self):
        result=run(range(3),count=8,audit_count=8)
        self.assertEqual(result['seeds'],3)
        self.assertEqual(result['promotion'][:7],'BLOCKED')
