import unittest
from tw10.meta_prediction_audit import evaluate,full_behaviour_registry,predict,_fit

class TW36MetaPredictionTests(unittest.TestCase):
    def trial(self,seed,gain):
        return {'seed':seed,'strategy_memory':[{'domain':'linear','proposal_gains':[gain,0,0,0,0], 'proposal_comparable':[True]*5}]}
    def test_disjoint_seed_holdout(self):
        out=evaluate([self.trial(1,.5)],[self.trial(2,.2)])
        self.assertTrue(out['training_and_holdout_seed_disjoint'])
        self.assertFalse(out['certified'])
        self.assertEqual(out['holdout_decisions'],1)
    def test_seed_leakage_rejected(self):
        with self.assertRaisesRegex(ValueError,'Seed leakage'):
            evaluate([self.trial(1,.5)],[self.trial(1,.2)])
    def test_bad_dimensions_rejected(self):
        t=self.trial(1,.3);t['strategy_memory'][0]['proposal_gains']=[.2]
        with self.assertRaises(ValueError):evaluate([t],[self.trial(2,.2)])
    def test_shrinkage(self):
        m=_fit([(1,'linear','topology',1.)])
        self.assertAlmostEqual(predict(m,'linear','topology'),1.)
        self.assertAlmostEqual(predict(m,'context','plasticity'),1.)
    def test_structural_registry(self):
        from tw10.relational_dendrites import catalogue
        p=catalogue()
        self.assertEqual(len(p),7777)
        self.assertEqual(len({v.genotype() for v in p}),7777)
