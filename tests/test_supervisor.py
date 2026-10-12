import tempfile,unittest
from pathlib import Path
from tw10.supervisor import supervise
from fixture_source import source_db
SOURCE=source_db()

class SupervisorTests(unittest.TestCase):
    def test_bounded_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            s=Path(d)/'study.sqlite';r=Path(d)/'report.json'
            a=supervise(SOURCE,s,batches=2,cycles=1,participants=2,report=r)
            self.assertEqual(a['batches_completed'],2)
            self.assertEqual(a['records'][-1]['evidence_records'],4)
            b=supervise(SOURCE,s,batches=1,cycles=1,participants=2,report=r)
            self.assertEqual(b['records'][-1]['evidence_records'],6)
            self.assertTrue(r.is_file())
    def test_stop_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            stop=Path(d)/'STOP';stop.touch();state=Path(d)/'db.sqlite'
            r=supervise(SOURCE,state,stop_file=stop)
            self.assertEqual(r['batches_completed'],0)
            self.assertFalse(state.exists())
    def test_bounds(self):
        with self.assertRaises(ValueError):supervise(SOURCE,'unused',batches=0)
        with self.assertRaises(ValueError):supervise(SOURCE,'unused',participants=13)

if __name__=='__main__':unittest.main()
