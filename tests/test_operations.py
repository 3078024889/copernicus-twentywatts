import tempfile, unittest
from pathlib import Path
from tw10.operations import inspect,execute,single_writer
from fixture_source import source_db
SOURCE=source_db()
class OperationsTest(unittest.TestCase):
    def test_read_only_audit(self):
        report=inspect(SOURCE,Path('/path/that/does/not/exist.sqlite'))
        self.assertEqual(report['source']['configurations'],7777)
        self.assertEqual(report['promotion'],'LOCKED')
    def test_locked_safety(self):
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/'run.lock'
            with single_writer(lock):
                with self.assertRaises(RuntimeError):
                    with single_writer(lock):pass
            self.assertFalse(lock.exists())
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):inspect(Path(d)/'missing.sqlite',Path(d)/'state.sqlite')
    def test_bound_limits(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(SOURCE,Path(d)/'state.sqlite',0)
            with self.assertRaises(ValueError):execute(SOURCE,Path(d)/'state.sqlite',26)
    def test_resume_cycles(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.sqlite'
            first=execute(SOURCE,state,1,2)
            self.assertEqual(first['advanced_this_run'],2)
            second=execute(SOURCE,state,1,2)
            self.assertEqual(second['evidence_records'],4)
            self.assertEqual(inspect(SOURCE,state)['longitudinal_cycles'],4)
            self.assertEqual(second['certified_independent_ais'],0)
            self.assertFalse(Path(str(state)+'.runlock').exists())
if __name__=='__main__':unittest.main()
