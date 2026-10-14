from contextlib import closing
import tempfile
import sqlite3
import unittest
from pathlib import Path
from tw10.twin_evolution import one_trial, rows_for, store

class CrossDomainTwinTests(unittest.TestCase):
    def test_same_experience_sealed_tests_and_matching_budget(self):
        current = one_trial(4, generations=3, proposals=3)
        cross = one_trial(4, generations=3, proposals=3, selection_policy='cross_domain')
        self.assertEqual(current['initial_state_sha256'], cross['initial_state_sha256'])
        self.assertEqual(cross, one_trial(4,3,3,selection_policy='cross_domain'))
        self.assertEqual(cross['fixed_updates'],cross['adaptive_updates'])
        self.assertEqual(cross['selection_predictions']['fixed'],cross['selection_predictions']['adaptive'])
        self.assertEqual(cross['sealed_predictions']['fixed'],cross['sealed_predictions']['adaptive'])
        self.assertEqual(cross['search_updates']['fixed'],cross['search_updates']['adaptive'])
        self.assertEqual([g['fixed_transfer'] for g in current['generations']], [g['fixed_transfer'] for g in cross['generations']])
        self.assertEqual([g['fixed_retention'] for g in current['generations']], [g['fixed_retention'] for g in cross['generations']])
        self.assertNotEqual(current['protocol'], cross['protocol'])
    def test_sealed_data_not_in_selection(self):
        self.assertNotEqual(rows_for(3,0,'linear','cross_retention',40), rows_for(3,0,'linear','sealed_retention',40))
        self.assertNotEqual(rows_for(3,0,'context','cross_transfer',40), rows_for(3,0,'context','sealed_transfer',40))
    def test_database_protocols_coexist(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'results.sqlite'
            store(path,[one_trial(0,2,2),one_trial(0,2,2,selection_policy='cross_domain')])
            with closing(sqlite3.connect(path)) as c, c:
                self.assertEqual(c.execute('select count(*) from twin_trials').fetchone()[0],2)
                self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok')
    def test_bad_policy_rejected(self):
        with self.assertRaises(ValueError):
            one_trial(1,selection_policy='sealed_transfer')
