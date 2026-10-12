import tempfile, unittest
from pathlib import Path
from tw8.arena import *
class ArenaTests(unittest.TestCase):
    def test_registry(self):
        r=registry();self.assertEqual(len(r),7777);self.assertEqual(len({c.key for c in r}),7777)
        self.assertEqual(len({(c.family,c.update,c.rate,c.decay) for c in r}),7777)
    def test_learning(self):
        c=registry()[0];m=Learner(c);p=m.predict((.4,.2));m.update((.4,.2),1);self.assertNotEqual(p,m.predict((.4,.2)))
    def test_reproducible(self):
        self.assertEqual(trial(registry()[7],20),trial(registry()[7],20))
    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            db=connect(Path(t)/'a.db');self.assertEqual(register(db),7777)
            self.assertEqual(screen(db,2)['inserted'],8)
            self.assertEqual(screen(db,2)['inserted'],0)
            self.assertEqual(report(db)['screen_records'],8)
            self.assertEqual(select(db,[]),[])
            self.assertEqual(report(db)['certified_independent_ais'],0)
            db.close()
    def test_holdout_disjoint(self):
        self.assertNotEqual(dataset(1,'linear',10),dataset(101,'linear',10))
    def test_all_families(self):self.assertEqual(set(c.family for c in registry()),set(FAMILIES))
if __name__=='__main__':unittest.main()
