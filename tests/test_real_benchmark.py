import unittest
from tw10.real_benchmark import _split,_normalize,evaluate

class ExternalBenchmarkTests(unittest.TestCase):
    def test_seeded_splits_are_disjoint_and_repeatable(self):
        rows=[(i,(float(i),float(i%7)),i%2) for i in range(100)]
        a=_split(rows,5);b=_split(rows,5)
        self.assertEqual(a,b)
        ids=[{r[0] for r in fold} for fold in a]
        self.assertFalse(ids[0]&ids[1]);self.assertFalse(ids[0]&ids[2]);self.assertFalse(ids[1]&ids[2])
    def test_no_test_leakage_in_scaling(self):
        train=[(0,(0.,0.),0),(1,(2.,2.),1)]
        held=[(2,(1000.,1000.),1)]
        _,norm=_normalize(train,held)
        self.assertEqual(norm[0][0],(999.,999.))
    def test_real_datasets_reproducible_and_not_certified(self):
        try:r=evaluate(314159,8)
        except RuntimeError as e:self.skipTest(str(e))
        self.assertEqual(r,evaluate(314159,8))
        self.assertEqual(len(r['results']),2)
        self.assertFalse(r['scientific_certification'])
        self.assertEqual(r['certified_independent_ais'],0)
        for result in r['results']:
            self.assertEqual(result['samples'],result['train']+result['selection']+result['holdout'])
    def test_bounds(self):
        with self.assertRaises(ValueError):evaluate(candidate_cap=0)

class UnifiedBenchmarkEntryTests(unittest.TestCase):
    def test_cli_benchmark_requires_no_synthetic_source_or_state(self):
        import tempfile, json
        from pathlib import Path
        from tw10.cli import main
        try:
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'benchmark.json'
                self.assertEqual(main(['benchmark','--root',d,'--report',str(out)]),0)
                result=json.loads(out.read_text(encoding='utf8'))
                self.assertEqual(len(result['results']),2)
                self.assertFalse(result['scientific_certification'])
                self.assertFalse((Path(d)/'data'/'v11.sqlite').exists())
        except RuntimeError as e:self.skipTest(str(e))


class RepeatedBenchmarkTests(unittest.TestCase):
    def test_seed_validation(self):
        from tw10.real_benchmark import evaluate_repeated
        for seeds in ((), (1,1), tuple(range(31))):
            with self.assertRaises(ValueError):evaluate_repeated(seeds=seeds)

    def test_repeated_is_deterministic_and_cannot_promote(self):
        from tw10.real_benchmark import evaluate_repeated
        try:
            a=evaluate_repeated(seeds=(1,2,3),candidate_cap=8)
            b=evaluate_repeated(seeds=(1,2,3),candidate_cap=8)
        except RuntimeError as e:self.skipTest(str(e))
        self.assertEqual(a,b)
        self.assertFalse(a['checkpoint_mutation'])
        self.assertFalse(a['eligible_for_production'])
        self.assertEqual(a['certified_independent_ais'],0)
        for r in a['results']:
            self.assertEqual(r['seed_count'],3)
            self.assertGreaterEqual(r['different_holdout_splits'],2)
            self.assertEqual(len(r['per_seed']),3)

    def test_repeated_cli_writes_no_checkpoint(self):
        import tempfile,json
        from pathlib import Path
        from tw10.cli import main
        try:
            with tempfile.TemporaryDirectory() as d:
                report=Path(d)/'repeat.json'
                self.assertEqual(main(['benchmark-repeat','--root',d,'--report',str(report)]),0)
                result=json.loads(report.read_text(encoding='utf8'))
                self.assertFalse(result['eligible_for_production'])
                self.assertFalse((Path(d)/'data'/'v11.sqlite').exists())
        except RuntimeError as e:self.skipTest(str(e))
