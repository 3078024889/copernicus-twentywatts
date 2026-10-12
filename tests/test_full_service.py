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
