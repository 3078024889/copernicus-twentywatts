from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from tw10.recursive_lineage import experiment, reprogram, run
from tw10.relational_dendrites import catalogue, RelationalLearner, edges

class RecursiveLineageTests(unittest.TestCase):
    def test_topology_mutation_rebuilds_actual_graph(self):
        source=catalogue()[0]
        target=catalogue()[6**4]
        m=RelationalLearner(source)
        m.syn[next(iter(m.graph))]=.7
        old=m.graph
        reprogram(m,target)
        self.assertNotEqual(old,m.graph)
        self.assertEqual(m.graph,edges(target.topology))
        self.assertEqual(set(m.syn),set(m.graph))
    def test_sealed_audit_is_not_selector(self):
        r=experiment(catalogue()[0],123,3)
        self.assertFalse(r['sealed_used_for_selection'])
        self.assertFalse(r['certified'])
        self.assertEqual(len(r['lineage']),3)
        for step in r['lineage']:
            self.assertFalse(step['accepted'] and not step['proposal_comparable'])
    def test_repeated_trial_is_identical_except_instrumented_time(self):
        a=experiment(catalogue()[117],52,4)
        b=experiment(catalogue()[117],52,4)
        a.pop('cpu_process_ns_observed'); b.pop('cpu_process_ns_observed')
        self.assertEqual(a,b)
    def test_resume_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'lineage.sqlite'
            a=run(db,4,88,3)
            self.assertEqual(a,run(db,4,88,3))
            self.assertEqual(a['sqlite_integrity'],'ok')
            with closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("UPDATE recursive_trials SET evidence='{}' WHERE rowid=1")
            with self.assertRaises(ValueError):run(db,4,88,3)
    def test_invalid_generations_and_count(self):
        with self.assertRaises(ValueError):experiment(catalogue()[0],1,0)
        with self.assertRaises(ValueError):run('/tmp/unused.sqlite',7778)
