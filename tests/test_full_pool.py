import tempfile,unittest,sqlite3
from pathlib import Path
from tests.fixture_source import source_db
from tw10.full_pool import init,bootstrap,batch,status,cycle_once,PROTOCOL
from tw8.arena import registry

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

class FairnessTests(unittest.TestCase):
    def test_shared_task_and_data_for_candidates(self):
        # Same first cycle must generate identical task, training seed and audit
        # regardless of candidate identity, even if they train sequentially.
        with tempfile.TemporaryDirectory() as d:
            db=init(Path(d)/'fair.sqlite')
            try:
                bootstrap(db,source_db())
                a,b=registry()[0],registry()[1]
                x=cycle_once(db,a)
                y=cycle_once(db,b)
                self.assertEqual(x['seed'],y['seed'])
                self.assertEqual(x['fairness_protocol'],'SHARED_TASK_SEED_PER_CYCLE')
                rows=db.execute('SELECT task FROM audits WHERE protocol=? AND id IN (?,?)',(PROTOCOL,a.key,b.key)).fetchall()
                self.assertEqual(len(rows),2)
                self.assertEqual(rows[0][0],rows[1][0])
            finally:db.close()
    def test_refuse_legacy_state_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            db=init(Path(d)/'fair.sqlite')
            try:
                with db:
                    db.execute('INSERT INTO settings VALUES (?,?)',('protocol','TW15_ALL_CONFIGS_LONGITUDINAL_V1'))
                with self.assertRaises(ValueError):bootstrap(db,source_db())
            finally:db.close()
