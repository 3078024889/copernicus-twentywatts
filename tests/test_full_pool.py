import tempfile,unittest,sqlite3
from pathlib import Path
from tests.fixture_source import source_db
from tw10.full_pool import init,bootstrap,batch,status

class PoolTests(unittest.TestCase):
    def test_round_robin_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=source_db()
            db=init(d/'pool.sqlite')
            try:
                bootstrap(db,source)
                self.assertEqual(batch(db,limit=3)['advanced'],3)
                self.assertEqual(status(db)['trained_distinct'],3)
                self.assertEqual(status(db)['max_cycles'],1)
                self.assertEqual(batch(db,limit=3)['advanced'],3)
                self.assertEqual(status(db)['trained_distinct'],6)
                self.assertEqual(status(db)['audit_records'],6)
            finally:db.close()
            db=init(d/'pool.sqlite')
            try:
                bootstrap(db,source)
                self.assertEqual(status(db)['audit_records'],6)
                self.assertEqual(status(db)['certified_ai'],0)
            finally:db.close()
    def test_source_required(self):
        with tempfile.TemporaryDirectory() as d:
            db=init(Path(d)/'pool.sqlite')
            try:
                with self.assertRaises(FileNotFoundError):bootstrap(db,Path(d)/'missing.sqlite')
                with self.assertRaises(ValueError):batch(db,limit=0)
            finally:db.close()
