import unittest,tempfile
from pathlib import Path
from tw10.algorithm_variants import registry, Learner, task, fingerprint, run, trial

class AlgorithmVariantsTests(unittest.TestCase):
    def test_7777_unique_structural_genotypes(self):
        a=registry();self.assertEqual(len(a),7777)
        self.assertEqual(len({(p.representation,p.loss,p.optimizer,p.memory,p.gate) for p in a}),7777)
    def test_learning_different_mechanisms(self):
        p=registry()[0];m=Learner(p)
        old=m.state()['w'][:]
        for x,y in task(5,'linear',30):m.update(x,y)
        self.assertNotEqual(old,m.w)
    def test_shared_task(self):
        self.assertEqual(task(7,'interaction',20),task(7,'interaction',20))
    def test_fingerprint_is_repeatable(self):
        p=registry()[40];self.assertEqual(fingerprint(p),fingerprint(p))
    def test_resumable_record(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'variants.sqlite'
            a=run(db,limit=3,seed=11);b=run(db,limit=3,seed=11)
            self.assertEqual(a['completed'],3);self.assertEqual(a['new_records'],3)
            self.assertEqual(b['new_records'],0)
    def test_staged_trial(self):
        self.assertEqual(len(trial(registry()[200],200)['stages']),4)

class LineageTests(unittest.TestCase):
    def test_each_parent_is_single_operator_mutation(self):
        rs=registry();by_id={p.id:p for p in rs}
        for p in rs[1:]:
            parent=by_id[p.parent]
            delta=sum(getattr(p,k)!=getattr(parent,k) for k in ('representation','loss','optimizer','memory','gate'))
            self.assertEqual(delta,1,p.id)
            self.assertLess(int(parent.id[1:]),int(p.id[1:]))
