import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from tw10.dendrite_native import advance, snapshot, database, restore, export, offspring_trial
from tw10.relational_dendrites import catalogue, RelationalLearner

class NativeDendriticTests(unittest.TestCase):
    def test_population_and_persistent_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'native.sqlite'
            a=advance(path,limit=7,offspring_every=2)
            self.assertEqual((a['registered'],a['trained'],a['learning_steps']),(7777,7,7))
            b=advance(path,limit=7,offspring_every=2)
            self.assertEqual(b['trained'],14)
            self.assertEqual(b['learning_steps'],14)
            self.assertEqual(b['offspring_trials'],0)
            self.assertEqual(snapshot(path)['learning_steps'],14)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_checkpoint_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'native.sqlite';advance(path,limit=1)
            with closing(sqlite3.connect(path)) as db:
                with db:db.execute("UPDATE learners SET checkpoint='{}' WHERE id='D0002'")
            with self.assertRaises(ValueError):advance(path,limit=1)
    def test_state_round_trip(self):
        v=catalogue()[3];m=RelationalLearner(v)
        for i in range(8):m.learn((.2,.4),i%2,i%2,replay_policy='fixed')
        a=restore(v,export(m))
        self.assertEqual(m.state(),a.state())
        self.assertEqual(m.updates,a.updates)
    def test_descendant_roundtrip_from_real_training(self):
        from tw10.dendrite_native import database, export, digest, encode, advance_descendants
        from tw10.first_generation import mutate
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'native.sqlite'
            with closing(database(path)) as db:
                v=catalogue()[17]
                m=RelationalLearner(v)
                for k in range(32):m.learn((.1,.3),k%2,0,replay_policy='fixed')
                child=mutate(v,810004)
                # In the real engine this copy is produced by the parent-child selection gate.
                state=export(m)
                db.execute('INSERT INTO descendant_checkpoints(child_id,parent_id,birth_step,genotype,checkpoint,checkpoint_hash) VALUES (?,?,?,?,?,?)',
                           (child.id,v.id,4,encode(child.genotype()),encode(state),digest(state)))
                db.commit()
            # Topology-changing offspring require re-mapping, tested in the actual mutation handler.
            if child.topology==v.topology:
                result=advance_descendants(path,limit=1)
                self.assertEqual(result['advanced_descendants'],1)
                self.assertEqual(result['descendant_progress'],1)

    def test_offspring_inherits_and_budget(self):
        v=catalogue()[35];m=RelationalLearner(v)
        for i in range(32):m.learn((.2,.4),i%2,0,replay_policy='fixed')
        result=offspring_trial(m,v,4,'context')
        self.assertTrue(result['updates_equal'])
        self.assertFalse(result['certified'])
if __name__=='__main__':unittest.main()
