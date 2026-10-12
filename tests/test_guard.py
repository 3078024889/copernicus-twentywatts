import unittest
from tw8.arena import registry, Learner, dataset
from tw10.guard import choose

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.c=registry()[0]
    def test_reproducible_and_no_mutation(self):
        previous=Learner(self.c)
        for x,y in dataset(1,'interaction',40):previous.update(x,y)
        cold=Learner(self.c)
        for x,y in dataset(2,'linear',40):cold.update(x,y)
        a=choose(previous,cold,seed=71,task='linear')
        b=choose(previous,cold,seed=71,task='linear')
        self.assertEqual(a.details(),b.details())
        self.assertEqual(previous.steps,40)
        self.assertEqual(cold.steps,40)
        self.assertIn(a.action,('retain','reset'))
        self.assertEqual(a.audit_selected,a.audit_continued if a.action=='retain' else a.audit_cold)
    def test_disjoint_probes(self):
        from tw8.arena import dataset
        self.assertNotEqual(dataset(71+3100000,'linear',96),dataset(71+4300000,'linear',96))
    def test_mismatch_and_margin_rejected(self):
        a=Learner(self.c)
        b=Learner(registry()[1])
        with self.assertRaises(ValueError):choose(a,b,seed=1,task='linear')
        with self.assertRaises(ValueError):choose(a,a,seed=1,task='linear',margin=-1)
    def test_guard_resets_under_high_margin(self):
        a=Learner(self.c)
        b=Learner(self.c)
        decision=choose(a,b,seed=1,task='linear',margin=.5)
        self.assertEqual(decision.action,'reset')

if __name__=='__main__':unittest.main()
