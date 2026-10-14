from contextlib import closing
import tempfile
import sqlite3
import unittest
from pathlib import Path
from tw10.twin_evolution import BASE, PROTOCOL, one_trial, study, store, rows_for, variant_proposal

class TwinEvolutionTests(unittest.TestCase):
    def test_different_rule_mutation(self):
        for i in range(6):
            candidate=variant_proposal(BASE,11,0,i)
            self.assertNotEqual(BASE.genotype(),candidate.genotype())
            self.assertEqual(candidate.parent,BASE.id)

    def test_sealed_data_separated(self):
        self.assertNotEqual(rows_for(5,0,'linear','train',40), rows_for(5,0,'linear','sealed_transfer',40))

    def test_equal_budget_and_deterministic(self):
        r=one_trial(7, generations=3, proposals=3)
        self.assertEqual(r,one_trial(7,generations=3,proposals=3))
        self.assertEqual(r['fixed_updates'],r['adaptive_updates'])
        self.assertEqual(r['selection_predictions']['fixed'],r['selection_predictions']['adaptive'])
        self.assertEqual(r['sealed_predictions']['fixed'],r['sealed_predictions']['adaptive'])
        self.assertEqual(r['certified_ais'],0)

    def test_no_unearned_certification(self):
        result=study(range(3),2,2)
        self.assertEqual(result['certified_ais'],0)
        self.assertTrue(result['equal_update_counts'] and result['equal_prediction_counts'])

    def test_persistence_idempotent_and_tamper_refusal(self):
        r=one_trial(2,2,2)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'twin.sqlite'
            store(path,[r]);store(path,[r])
            with closing(sqlite3.connect(path)) as conn, conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM twin_trials').fetchone()[0],1)
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            altered=dict(r,certified_ais=1)
            with self.assertRaises(ValueError):store(path,[altered])

    def test_reject_invalid(self):
        with self.assertRaises(ValueError):one_trial(0, generations=0)

if __name__=='__main__':unittest.main()
