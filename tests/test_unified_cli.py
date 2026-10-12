import tempfile, unittest, json
from pathlib import Path
from tw10.cli import main
from fixture_source import source_db
class UnifiedCliTests(unittest.TestCase):
    def test_reject_missing_real_source(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                main(['inspect','--root',d])
    def test_reject_old_state_target(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                main(['train','--root',d,'--source-db',str(source_db()),'--state-db',str(Path(d)/'data'/'v9.sqlite')])
    def test_gate_never_promotes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(['gate','--source-db',str(source_db()),'--state-db',str(Path(d)/'state.sqlite')]),0)
    def test_training_creates_recoverable_state(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'state.sqlite'
            args=['train','--source-db',str(source_db()),'--state-db',str(state),'--participants','2','--cycles','1']
            self.assertEqual(main(args),0)
            self.assertEqual(main(args),0)
            self.assertTrue(state.exists())
if __name__=='__main__':unittest.main()
