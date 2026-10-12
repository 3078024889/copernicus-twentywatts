import json, tempfile, unittest
from pathlib import Path
from tw9.continuity import run, init_db, agent_pool, restore
from tw8.arena import registry

SOURCE=Path(__file__).resolve().parents[1]/'data'/'v8.sqlite'

class V9Tests(unittest.TestCase):
    def test_real_source_pool(self):
        p=agent_pool(SOURCE,3)
        self.assertEqual(len(p),3)
        self.assertEqual(p[0].key,'G0148')
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception): agent_pool(Path(d)/'missing.sqlite',2)
    def test_restore_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):restore(registry()[0],'{"weights":[],"steps":0}')
    def test_restore_rejects_steps(self):
        with self.assertRaises(ValueError):restore(registry()[0],'{"weights":[0,0,0],"steps":-1}')
    def test_cycles_checkpoint_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.sqlite'
            a=run(SOURCE,path,2,2)
            self.assertEqual(a['evidence_records'],4)
            self.assertEqual(a['integrity'],'ok')
            self.assertEqual(a['certified_independent_ais'],0)
            b=run(SOURCE,path,1,2)
            self.assertEqual(b['evidence_records'],6)
            self.assertEqual(set(b['participant_cycles'].values()),{3})
            self.assertEqual(b['mother_promotion'],'LOCKED')
            db=init_db(path)
            try:
                for sid,cycles,state in db.execute('SELECT id,cycles,state FROM agents'):
                    self.assertEqual(json.loads(state)['steps'],cycles*48)
            finally:db.close()
    def test_pool_mutation_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.sqlite'
            run(SOURCE,path,1,2)
            with self.assertRaises(ValueError):run(SOURCE,path,1,3)
    def test_zero_cycles_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.sqlite'
            a=run(SOURCE,path,0,2)
            b=run(SOURCE,path,0,2)
            self.assertEqual(a['evidence_records'],0)
            self.assertEqual(b['advanced_this_run'],0)
    def test_invalid_cycle_range(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run(SOURCE,Path(d)/'a.sqlite',201,2)

if __name__=='__main__':unittest.main()
