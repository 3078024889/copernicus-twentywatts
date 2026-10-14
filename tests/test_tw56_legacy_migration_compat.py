"""Windows upgrade regressions: TW55 lacks TW56-only descendant ledger."""
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from tw10.dendrite_native import advance, database, progress, snapshot, verify_all
from scripts.migrate_native_state import migrate


class LegacyNativeMigrationCompatibility(unittest.TestCase):
    def test_legacy_database_without_descendant_learning_is_verifiable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'legacy.sqlite'
            advance(path, limit=4)
            with closing(sqlite3.connect(path)) as db:
                db.execute('DROP TABLE descendant_learning')
                db.commit()
            self.assertEqual(verify_all(path)['integrity'], 'FULL_CHECK_OK')
            self.assertEqual(snapshot(path)['descendant_evidence_records'], 0)
            # The upgraded writer creates TW56-only schema before new training.
            advance(path, limit=1)
            with closing(sqlite3.connect(path)) as db:
                self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name='descendant_learning'").fetchone())
            self.assertEqual(verify_all(path)['integrity'], 'FULL_CHECK_OK')

    def test_real_migration_of_missing_ledger_preserves_old_training(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / 'old'; new = root / 'new'
            for installation in (old, new):
                (installation / 'data').mkdir(parents=True)
                shutil.copy2(Path(__file__).resolve().parents[1] / 'data' / 'v8.sqlite', installation / 'data' / 'v8.sqlite')
            source = old / 'data' / 'full_pool_fair_v2.sqlite'
            with closing(sqlite3.connect(source)) as db: db.execute('CREATE TABLE marker (id INTEGER)')
            advance(Path(str(source) + '.dendrite_native.sqlite'), limit=5)
            with closing(sqlite3.connect(str(source) + '.dendrite_native.sqlite')) as db:
                db.execute('DROP TABLE descendant_learning'); db.commit()
            result = migrate(old, new)
            dest = new / 'data' / 'full_pool_fair_v2.sqlite.dendrite_native.sqlite'
            self.assertEqual(result['native']['learning_records'], 5)
            self.assertEqual(verify_all(dest)['learning_records'], 5)
            advance(dest, limit=1)
            self.assertEqual(verify_all(dest)['learning_records'], 6)

if __name__ == '__main__':
    unittest.main()
