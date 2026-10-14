import tempfile
import unittest
from pathlib import Path
from tw10.first_generation import initialise, mutate, run, trial, stable_hash
from tw10.relational_dendrites import catalogue

class FirstGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool=catalogue()
    def test_mutation_changes_operator(self):
        for idx in (0,59,2586,7776):
            parent=self.pool[idx]
            child=mutate(parent,19)
            self.assertEqual(sum(a!=b for a,b in zip(parent.genotype(),child.genotype())),1)
    def test_pair_repeatability(self):
        self.assertEqual(trial(self.pool[14],55),trial(self.pool[14],55))
    def test_sealed_not_selected(self):
        p=trial(self.pool[1],71)
        self.assertEqual(p['accepted'],p['selection_gain']>0 and p['baseline_updates']==p['challenger_updates'])
        self.assertFalse(p['certified'])
    def test_inventory_immutable_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'pool.sqlite'
            a=initialise(path)
            b=initialise(path)
            self.assertEqual(a,b)
            self.assertEqual(a['registered'],7777)
            self.assertEqual(a['unique_structural_programs'],7777)
            first=run(path,count=3)
            second=run(path,count=3)
            self.assertEqual(first,second)
            self.assertTrue(first['budget_equal'])
    def test_no_false_mother_claim(self):
        p=trial(self.pool[1],7)
        self.assertEqual(p['comparison'],'PARENT_CONTROL_ONLY')
        self.assertFalse(p['mother_is_proxy'])
    def test_unmatched_replay_budget_is_excluded_from_aggregate(self):
        with tempfile.TemporaryDirectory() as td:
            payload=run(Path(td)/'pool.sqlite',count=120)
            self.assertEqual(payload['budget_eligible_trials']+payload['budget_ineligible_trials'],120)
            self.assertGreater(payload['budget_ineligible_trials'],0)
            self.assertFalse(payload['budget_equal'])
