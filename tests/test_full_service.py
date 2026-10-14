import tempfile,time,unittest
from pathlib import Path
from fixture_source import source_db
from tw10.offline_oracle import OfflineRuntime

class FullServiceTests(unittest.TestCase):
    def test_all_config_mode_auto_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            one=OfflineRuntime(source_db(),d/'full.sqlite',interval=1,participants=9,
                    all_configs=True,stop_file=d/'STOP',report=d/'report.json')
            one.start()
            for _ in range(150):
                if one.worker['batches_completed']>=1:break
                time.sleep(.05)
            one.stop()
            self.assertGreaterEqual(one.worker['batches_completed'],1)
            snap=one.snapshot()
            self.assertEqual(snap['source']['configurations'],7777)
            self.assertEqual(snap['source']['screen'],31108)
            self.assertEqual(snap['source']['holdout'],1800)
            self.assertGreaterEqual(snap['trained_distinct'],9)
            two=OfflineRuntime(source_db(),d/'full.sqlite',interval=1,participants=9,all_configs=True)
            self.assertEqual(two.snapshot()['trained_distinct'],snap['trained_distinct'])
            self.assertEqual(two.snapshot()['certified_independent_ais'],0)

    def test_snapshot_only_reads_and_refuses_missing_state(self):
        from tw10.full_pool import init, bootstrap
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            state=d/'pool.sqlite'
            source=source_db()
            runtime=OfflineRuntime(source,state,all_configs=True,training=False)
            # GET must not silently create missing state files.
            error=runtime.snapshot()
            self.assertEqual(error.get('health'),'ERROR')
            self.assertFalse(state.exists())
            with closing(init(state)) as db: bootstrap(db,source)
            stamp=state.stat().st_mtime_ns
            for _ in range(12):
                snap=runtime.snapshot()
                self.assertEqual(snap['source']['configurations'],7777)
                self.assertEqual(snap['all_candidates']['audit_records'],0)
            self.assertEqual(state.stat().st_mtime_ns,stamp)
            with closing(sqlite3.connect(state)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM audits').fetchone()[0],0)

class PollingPerformanceTests(unittest.TestCase):
    def test_poll_does_not_run_database_deep_integrity_checks(self):
        from tw10.full_pool import init,bootstrap
        from contextlib import closing
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'fair.sqlite';src=source_db()
            with closing(init(state)) as db:bootstrap(db,src)
            rt=OfflineRuntime(src,state,all_configs=True,training=False)
            # Tests both values are not deceptive 'ok' without checking.
            for _ in range(4):
                snap=rt.snapshot()
                self.assertEqual(snap['source']['integrity'],'NOT_CHECKED_IN_POLL')
                self.assertEqual(snap['all_candidates']['integrity'],'NOT_CHECKED_IN_POLL')
            # Startup is responsible for expensive integrity verification.
            rt.start();self.assertEqual(rt.worker['status'],'READ_ONLY');rt.stop()
