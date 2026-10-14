import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from tw10.dendrite_native import advance, verify_all
from tw10.offline_oracle import OfflineRuntime
from scripts.migrate_native_state import migrate

class TW54NativeReleaseTests(unittest.TestCase):
    def test_all_initial_states_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'native.sqlite'
            advance(path,limit=2)
            result=verify_all(path)
            self.assertEqual((result['initial_variants'],result['offspring_trials']),(7777,0))
            with closing(sqlite3.connect(path)) as db:
                with db:db.execute("UPDATE learners SET checkpoint_hash='bad' WHERE id='D0002'")
            with self.assertRaisesRegex(ValueError,'checkpoint tamper'):
                verify_all(path)

    def test_native_dashboard_journal_not_confused_with_d_steps(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r=OfflineRuntime(root/'source.sqlite',root/'state.sqlite',all_configs=True,native_dendrites=True,participants=2,interval=1)
            r._training_batch()
            self.assertEqual(r._batch_result['dendritic_learning_steps'],2)
            self.assertEqual(r._batch_result['offspring_evidence_total'],0)
            self.assertEqual(r._batch_result['selection_adoptions'],0)

    def test_migration_preserves_original_and_independent_states(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);old=base/'old';new=base/'new'
            for r in [old,new]:(r/'data').mkdir(parents=True)
            # Source identity proof uses the same source bytes; no existing system is touched.
            for r in [old,new]:(r/'data'/'v8.sqlite').write_bytes(b'common fixture identity')
            src=old/'data'/'full_pool_fair_v2.sqlite'
            with closing(sqlite3.connect(src)) as db:
                db.execute('CREATE TABLE fixture(x INTEGER)');db.execute('INSERT INTO fixture VALUES(99)');db.commit()
            native=Path(str(src)+'.dendrite_native.sqlite')
            advance(native,limit=2)
            with closing(sqlite3.connect(new/'data'/'full_pool_fair_v2.sqlite')) as db:
                db.execute('CREATE TABLE old_state(z INTEGER)');db.commit()
            result=migrate(old,new)
            self.assertEqual(result['native']['initial_variants'],7777)
            self.assertEqual(result['native']['descendants'],0)
            self.assertEqual(verify_all(native)['initial_variants'],7777)
            self.assertEqual(verify_all(new/'data'/native.name)['initial_variants'],7777)
            with closing(sqlite3.connect(new/'data'/'full_pool_fair_v2.sqlite')) as db:
                self.assertEqual(db.execute('SELECT x FROM fixture').fetchone()[0],99)
            self.assertTrue(list((new/'migration_archive').glob('*/full_pool_fair_v2.sqlite')))

if __name__=='__main__':unittest.main()
