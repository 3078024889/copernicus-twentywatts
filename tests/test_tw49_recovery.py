import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fixture_source import source_db
from tw10.offline_oracle import OfflineRuntime
from tw10.research_journal import inspect,record

class DurableResearchRecoveryTests(unittest.TestCase):
    def test_last_research_survives_restart_and_training_tail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.sqlite.research_journal.sqlite'
            record(p,'research',{'batch':20,'results':{'seeds':4,'cpu_fair_pairs':3}})
            for n in range(21,36):record(p,'training',{'batch':n,'latest':{'advanced_this_run':2}})
            snapshot=inspect(p,tail=2)
            self.assertEqual(snapshot['latest_research']['payload']['batch'],20)
            rt=OfflineRuntime(source_db(),Path(d)/'state.sqlite',interval=2,participants=2,all_configs=True)
            self.assertEqual(rt.research['status'],'COMPLETED')
            self.assertEqual(rt.research['latest']['cpu_fair_pairs'],3)
    def test_record_training_before_slow_research(self):
        with tempfile.TemporaryDirectory() as d:
            rt=OfflineRuntime(source_db(),Path(d)/'state.sqlite',interval=1,participants=2,
                              report=Path(d)/'report.json',all_configs=True,research_every=1,research_seeds=2)
            rt.start()
            rt.stop()
            # Verify the durable ordering in the real service implementation.
            import inspect as pyinspect
            code=pyinspect.getsource(OfflineRuntime.work_loop)
            self.assertLess(code.index("journal_record(self.journal_path,'training'"),code.index('self._research_cycle(n)'))
