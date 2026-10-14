from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from tw10.strategy_memory import experiment, run, choose, mutations
from tw10.relational_dendrites import catalogue, FIELDS

class StrategyMemoryTests(unittest.TestCase):
    def test_mutations_change_executable_operator(self):
        v=catalogue()[5]
        children=mutations(v,13)
        self.assertEqual(len(children),5)
        for field,child in zip(FIELDS,children):
            self.assertEqual(child.parent,v.id)
            self.assertEqual(child.changed,field)
            self.assertEqual(sum(a!=b for a,b in zip(v.genotype(),child.genotype())),1)
    def test_choice_responds_to_prior_selection_results(self):
        gains=[.01,.02,0,0,0]
        memory={('linear','topology'):[.5,.5]}
        self.assertEqual(choose(gains,memory,'linear',False),1)
        self.assertEqual(choose(gains,memory,'linear',True),0)
        self.assertEqual(choose(gains,memory,'relation',True),1)
    def test_history_without_sealed_leakage_and_equal_probes(self):
        result=experiment(catalogue()[0],101,8)
        self.assertFalse(result['sealed_used_for_selection'])
        self.assertFalse(result['certified'])
        self.assertTrue(result['equal_probes'])
        self.assertTrue(result['equal_candidate_training_updates'])
        self.assertEqual(result['strategy_memory_records'],sum(sum(row['proposal_comparable']) for row in result['strategy_memory']))
    def test_repeat_and_database_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'test.sqlite'
            first=run(db,3,1234,4)
            second=run(db,3,1234,4)
            self.assertEqual(first['trials'],3)
            self.assertEqual(first['new_trials'],3)
            self.assertEqual(second['new_trials'],0)
            self.assertEqual(second['sqlite_integrity'],'ok')
            with closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("UPDATE strategy_memory_trials SET evidence='{}' WHERE rowid=1")
            with self.assertRaises(ValueError):run(db,3,1234,4)
    def test_seed_replay(self):
        a=experiment(catalogue()[111],6,4)
        b=experiment(catalogue()[111],6,4)
        a.pop('cpu_process_ns_observed');b.pop('cpu_process_ns_observed')
        self.assertEqual(a,b)
    def test_invalid_ranges(self):
        with self.assertRaises(ValueError):experiment(catalogue()[0],1,1)
        with self.assertRaises(ValueError):run('/tmp/not_written.sqlite',0)
