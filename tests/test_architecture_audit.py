import tempfile
import unittest
from pathlib import Path
from tw10.architecture_audit import ARCHITECTURES, BoundedKNN, construct, evaluate, run

class ArchitectureAuditTests(unittest.TestCase):
    def test_distinct_families_update(self):
        self.assertEqual(len(ARCHITECTURES),4)
        for a in ARCHITECTURES:
            m=construct(a)
            for _ in range(4):m.update((0.4,-0.2),1)
            self.assertTrue(0<=m.predict((0.2,0.1))<=1)
    def test_bounded_memory(self):
        m=BoundedKNN(limit=8)
        for i in range(30):m.update((i/30,0),i%2)
        self.assertEqual(len(m.memory),8)
    def test_paired_reproducible(self):
        self.assertEqual(evaluate('gaussian_nb',201),evaluate('gaussian_nb',201))
        self.assertNotEqual(evaluate('gaussian_nb',201),evaluate('gaussian_nb',202))
    def test_database_resume_and_scope(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'audit.sqlite'
            a=run(p,(201,202));b=run(p,(201,202));c=run(p,(203,))
            self.assertEqual((a['new_trials'],b['new_trials'],c['new_trials']),(8,0,4))
            self.assertEqual(b['integrity'],'ok')
            self.assertEqual(c['trials'],4)
            self.assertEqual(c['certified_independent_ais'],0)
    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):evaluate('unknown',1)
        with self.assertRaises(ValueError):run('ignored.sqlite',(1,1))
