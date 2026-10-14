from contextlib import closing
import unittest
from tw10.prospective_evolution import policy_choice, experiment
from tw10.relational_dendrites import catalogue

class EligibilityProtocolTests(unittest.TestCase):
    def test_meta_respects_budget_eligibility(self):
        priors={('linear','memory'):(.9,80),('linear','topology'):(.1,40)}
        self.assertEqual(policy_choice('linear',priors,44,'meta',[0,1]),0)
    def test_no_eligible_has_no_selection(self):
        self.assertIsNone(policy_choice('linear',{},1,'meta',[]))
        self.assertIsNone(policy_choice('linear',{},1,'random',[]))
    def test_both_arms_select_only_equal_update_mutations(self):
        result=experiment(catalogue()[199],46000,{},4)
        for arm in ('random','meta'):
            for e in result['traces'][arm]:
                if e['selected_field'] is not None:
                    self.assertIn(e['selected_field'],e['eligible_fields'])
                    self.assertTrue(e['budget_comparable'])
        self.assertTrue(result['candidate_update_budget_equal'])
        self.assertTrue(result['probe_budget_equal'])
    def test_sealed_not_used(self):
        result=experiment(catalogue()[10],46001,{},2)
        self.assertFalse(result['sealed_used_for_selection'])

class EvidenceIntegrityTests(unittest.TestCase):
    def test_evidence_hash_field_tamper_is_rejected(self):
        import json,sqlite3,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tw10.prospective_evolution import run
        fake_history=[{'seed':15500,'no_history':[]}]
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'future.sqlite'
            with patch('tw10.meta_prediction_audit.read_trials',return_value=fake_history):
                run('mock',db,count=1,seed=73000,generations=2)
                with closing(sqlite3.connect(db)) as c, c:
                    text=c.execute('SELECT evidence FROM prospective_trials').fetchone()[0]
                    row=json.loads(text);row['evidence_hash']='fake'
                    c.execute('UPDATE prospective_trials SET evidence=?',(json.dumps(row),))
                with self.assertRaises(ValueError):
                    run('mock',db,count=1,seed=73000,generations=2)
