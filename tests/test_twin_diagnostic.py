from contextlib import closing
import tempfile
import unittest
import sqlite3
from pathlib import Path
from tw10.twin_evolution import diagnose, diagnostic_proposal, BASE, one_trial
from tw10.twin_diagnostic_backtest import run

class DiagnosticEvolutionTests(unittest.TestCase):
    def test_failure_classes(self):
        self.assertEqual(diagnose([.9,.5,.6],0),'memory_interference')
        self.assertEqual(diagnose([.9,.9,.5],0),'transfer_failure')
        self.assertEqual(diagnose([.5,.5,.5],0),'prediction_error')
        self.assertEqual(diagnose([.9,.9,.9],0),'stability')
    def test_diagnostic_changes_actual_operator(self):
        v=diagnostic_proposal(BASE,4,0,0,'transfer_failure')
        self.assertEqual(v.changed,'branch')
        self.assertNotEqual(v.branch,BASE.branch)
        self.assertEqual(v.parent,BASE.id)
    def test_reproducible_and_budget_pair(self):
        a=one_trial(7,3,3,selection_policy='diagnostic')
        b=one_trial(7,3,3,selection_policy='cross_domain')
        self.assertEqual(a,one_trial(7,3,3,selection_policy='diagnostic'))
        self.assertEqual(a['initial_state_sha256'],b['initial_state_sha256'])
        self.assertEqual(a['selection_predictions'],b['selection_predictions'])
        self.assertEqual(a['search_updates'],b['search_updates'])
        self.assertEqual([g['fixed_transfer'] for g in a['generations']],[g['fixed_transfer'] for g in b['generations']])
    def test_distinct_evidence_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(range(3),generations=2,db=Path(d)/'diagnostic.sqlite')
            self.assertEqual(r['seeds'],3)
            self.assertTrue(r['same_probe_and_update_counts'])
            with closing(sqlite3.connect(Path(d)/'diagnostic.sqlite')) as c, c:
                self.assertEqual(c.execute('select count(*) from twin_trials').fetchone()[0],6)
                self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok')
