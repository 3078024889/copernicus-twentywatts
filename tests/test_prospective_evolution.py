from contextlib import closing
import json
import tempfile
import unittest
from pathlib import Path
from tw10.prospective_evolution import learn_priors, policy_choice, experiment, PROTOCOL
from tw10.relational_dendrites import catalogue

class ProspectiveEvolutionTests(unittest.TestCase):
    def test_no_sealed_data_for_prior(self):
        history=[{'no_history':[{'domain':'linear','proposal_gains':[.2,0,0,0,0], 'proposal_comparable':[True]*5}], 'audits':{'linear':{'no_history':.999}}}]
        a=learn_priors(history)
        history[0]['audits']['linear']['no_history']=-999
        self.assertEqual(a,learn_priors(history))
    def test_prior_changes_precommitted_choice(self):
        priors={('linear','memory'):(.4,100)}
        self.assertEqual(policy_choice('linear',priors,22,'meta'),3)
    def test_deterministic_sealed_audit(self):
        a=experiment(catalogue()[100],33000,{},2)
        b=experiment(catalogue()[100],33000,{},2)
        # CPU counters are measured metadata, not stable deterministic evidence.
        for r in (a,b):
            for entries in r['traces'].values():
                for e in entries:e.pop('cpu_process_ns',None)
            r.pop('evidence_hash')
        self.assertEqual(a,b)
        self.assertFalse(a['sealed_used_for_selection'])
        self.assertFalse(a['certified'])
        self.assertTrue(a['probe_budget_equal'])
    def test_invalid_generation(self):
        with self.assertRaises(ValueError):experiment(catalogue()[0],1,{},1)

class ProspectivePersistenceTests(unittest.TestCase):
    def test_restart_and_tamper_rejection(self):
        from unittest.mock import patch
        from tw10.prospective_evolution import run
        history=[{'seed':15500,'no_history':[{'domain':'linear','proposal_gains':[.2,0,0,0,0], 'proposal_comparable':[True]*5}]}]
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'future.sqlite'
            with patch('tw10.meta_prediction_audit.read_trials',return_value=history):
                first=run('mock',db,count=2,seed=33000,generations=2)
                second=run('mock',db,count=2,seed=33000,generations=2)
                self.assertEqual(first['new_trials'],2)
                self.assertEqual(second['new_trials'],0)
                self.assertEqual(second['sqlite_integrity'],'ok')
                with closing(__import__('sqlite3').connect(db)) as conn, conn:
                    conn.execute("UPDATE prospective_trials SET evidence='{}' WHERE rowid=1")
                with self.assertRaises(ValueError):run('mock',db,count=2,seed=33000,generations=2)
    def test_history_future_overlap_rejected(self):
        from unittest.mock import patch
        from tw10.prospective_evolution import run
        with tempfile.TemporaryDirectory() as tmp:
            with patch('tw10.meta_prediction_audit.read_trials',return_value=[{'seed':33000,'no_history':[]}]):
                with self.assertRaises(ValueError):run('mock',Path(tmp)/'future.sqlite',count=1,seed=33000,generations=2)
