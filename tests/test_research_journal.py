from contextlib import closing
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from fixture_source import source_db
from tw10.research_journal import record, inspect, verify_all
from tw10.offline_oracle import OfflineRuntime

class ResearchJournalTests(unittest.TestCase):
    def test_append_restart_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal.sqlite'
            record(path,'training',{'batch':1,'x':3})
            record(path,'research',{'batch':1,'passed':False})
            self.assertEqual(inspect(path)['training_batches'],1)
            self.assertEqual(inspect(path)['research_completed'],1)
            self.assertTrue(verify_all(path))
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE journal SET payload=? WHERE seq=1",(json.dumps({'batch':900}),))
            with self.assertRaises(RuntimeError):inspect(path)
            with self.assertRaises(RuntimeError):verify_all(path)
    def test_worker_resume_and_research_files_never_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=dict(interval=1,participants=2,stop_file=root/'stop',report=root/'status.json',
                      all_configs=True,research_every=1,research_seeds=2)
            rt=OfflineRuntime(source_db(),root/'state.sqlite',**args)
            rt.start()
            until=time.monotonic()+15
            while time.monotonic()<until:
                if rt.research['status']=='COMPLETED' and rt.worker['batches_completed']>=1:break
                time.sleep(.05)
            rt.stop()
            self.assertEqual(rt.research['status'],'COMPLETED',rt.research)
            journal=inspect(rt.journal_path)
            self.assertGreaterEqual(journal['training_batches'],1)
            self.assertTrue((root/'status.research.batch1.json').exists())
            again=OfflineRuntime(source_db(),root/'state.sqlite',**args)
            self.assertEqual(again.worker['batches_completed'],journal['training_batches'])
            self.assertTrue(verify_all(rt.journal_path))
