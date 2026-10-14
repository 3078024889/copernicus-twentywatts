import tempfile, time, unittest
from pathlib import Path
from tw10.compute_backtest import evaluate
from tw10.offline_oracle import OfflineRuntime, _HTML
from tw10.resource_meter import measure
from fixture_source import source_db

class ComputeResearchTests(unittest.TestCase):
    def test_resource_meter_records_real_nonnegative_usage(self):
        m={}
        with measure(m):
            sum(x*x for x in range(10000))
        self.assertGreaterEqual(m['process_cpu_seconds'],0)
        self.assertGreaterEqual(m['wall_seconds'],0)
        self.assertFalse(m['rss_is_peak'])
    def test_compute_backtest_is_bounded_and_compares(self):
        with self.assertRaises(ValueError):evaluate(1)
        r=evaluate(2,180900,3)
        self.assertEqual(r['valid'],2)
        self.assertEqual(len(r['records']),2)
        self.assertGreater(r['total_process_cpu_seconds'],0)
        self.assertEqual(r['certified_ais'],0)
        self.assertEqual(r['cpu_fair_pairs']+r['cpu_mismatched_pairs'],r['valid'])
        self.assertEqual(r['cpu_within_10pct_count'],r['cpu_fair_pairs'])
        self.assertAlmostEqual(r['cpu_fair_pair_fraction'],r['cpu_fair_pairs']/r['seeds'])
        for item in r['records']:
            self.assertEqual(item['cpu_budget_matched'],.9 <= item['cpu_ratio_inherit_to_reset'] <= 1.1)
    def test_research_loop_surfaces_evidence_and_does_not_certify(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=OfflineRuntime(source_db(),root/'state.sqlite',interval=1,participants=2,
                stop_file=root/'STOP',report=root/'status.json',all_configs=True,
                research_every=1,research_seeds=2)
            runtime.start()
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if runtime.research['status'] in ('COMPLETED','ERROR'):break
                time.sleep(.05)
            runtime.stop()
            self.assertEqual(runtime.research['status'],'COMPLETED',runtime.research)
            self.assertTrue((root/'status.research.batch1.json').exists())
            s=runtime.snapshot()
            self.assertGreaterEqual(s['worker']['batches_completed'],1)
            self.assertIn('resources',s['worker']['latest'])
            self.assertEqual(s['certified_independent_ais'],0)
            self.assertIn('research',s)
            self.assertIn('科研实验',_HTML)
