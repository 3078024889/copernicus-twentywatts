import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from tw10.event_evolution import enqueue, process_pending, status
from tw10.offline_oracle import OfflineRuntime

class EvolutionEventTests(unittest.TestCase):
    def test_nonfailure_does_not_schedule(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.sqlite'
            self.assertIsNone(enqueue(p,batch=1,gain=.2,resets=0))
            self.assertFalse(p.exists())

    def test_failure_persistent_idempotent_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.sqlite'
            eid=enqueue(p,batch=2,gain=-.1,resets=0)
            self.assertEqual(eid,enqueue(p,batch=2,gain=-.1,resets=0))
            self.assertEqual(status(p)['pending'],1)
            result=process_pending(p)
            self.assertEqual(result['completed'],1)
            self.assertEqual(process_pending(p)['completed'],0)
            self.assertEqual(status(p)['completed'],1)
            self.assertEqual(status(p)['certified'],0)
            with closing(sqlite3.connect(p)) as db:
                with db:
                    db.execute("UPDATE event_trials SET payload=? WHERE event_id=?",('{}',eid))
            with self.assertRaises(ValueError):status(p)

    def test_identity_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.sqlite'
            enqueue(p,batch=1,gain=-.2,resets=0)
            with self.assertRaises(ValueError):enqueue(p,batch=1,gain=-.3,resets=0)

    def test_runtime_can_report_evolution_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            r=OfflineRuntime(p/'source.sqlite',p/'state.sqlite',all_configs=True,event_evolution=True)
            self.assertEqual(r.evolution_path.name,'state.sqlite.event_evolution.sqlite')
            self.assertFalse(r.evolution_path.exists())

if __name__=='__main__':unittest.main()

class SignalTests(unittest.TestCase):
    def test_low_holdout_is_a_real_event(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.sqlite'
            self.assertIsNotNone(enqueue(p,batch=31,gain=.002889,resets=132,accuracy=.741211))
            self.assertEqual(status(p)['pending'],1)
            self.assertEqual(process_pending(p)['completed'],1)
            self.assertEqual(status(p)['completed'],1)
