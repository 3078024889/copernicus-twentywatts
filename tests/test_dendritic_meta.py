import unittest,tempfile
from pathlib import Path
from tw10.dendritic_meta import dataset,paired_trial,run,summarize,CHOICES

class DendriticMetaTests(unittest.TestCase):
    def test_disjoint_partitions(self):
        self.assertNotEqual(dataset(17,'linear',10,'learn'),dataset(17,'linear',10,'audit'))
    def test_repeatability(self):
        self.assertEqual(paired_trial(4).to_dict(),paired_trial(4).to_dict())
    def test_actual_rule_choice(self):
        t=paired_trial(6)
        self.assertIn(t.selected_optimizer,CHOICES)
        self.assertGreaterEqual(t.challenger_updates,t.mother_updates)
        self.assertEqual(len(t.selection_error_by_optimizer),6)
    def test_resume(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'meta.sqlite'
            a=run(p,seed_start=1,count=2)
            b=run(p,seed_start=1,count=2)
            self.assertEqual(a,b)
            self.assertEqual(a['integrity'],'ok')
    def test_no_certification_from_synthetic(self):
        self.assertFalse(summarize([paired_trial(1)])['certified_better_than_mother'])
