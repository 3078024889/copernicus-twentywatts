import unittest
from tw10.relational_dendrites import (catalogue,edges,RelationalLearner,tasks,behaviour_fingerprint,paired_experiment,audit_catalogue)

class RelationalDendritesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.pool=catalogue()
    def test_7777_unique_operator_graphs(self):
        self.assertEqual(len(self.pool),7777)
        self.assertEqual(len({p.genotype() for p in self.pool}),7777)
    def test_all_have_valid_mutation_parent(self):
        by_id={p.id:p for p in self.pool}
        for p in self.pool[1:]:
            self.assertEqual(sum(a!=b for a,b in zip(p.genotype(),by_id[p.parent].genotype())),1)
    def test_graph_topology_changes_edges(self):
        self.assertNotEqual(edges('ring'),edges('star'))
        self.assertNotEqual(edges('ring'),edges('reciprocal'))
    def test_local_learning_changes_weights_and_synapses(self):
        m=RelationalLearner(self.pool[0]);before=m.state()
        for x,y,c in tasks(2,'interaction',28):m.learn(x,y,c)
        self.assertNotEqual(before['readout'],m.state()['readout'])
        self.assertNotEqual(before['syn'],m.state()['syn'])
    def test_meta_rule_responds_to_error(self):
        v=next(v for v in self.pool if v.meta=='surprise')
        m=RelationalLearner(v)
        for x,y,c in tasks(2,'context',15):m.learn(x,y,c)
        self.assertGreater(m.rule_changes,0)
    def test_same_seed_same_challenge(self):
        self.assertEqual(tasks(42,'relation',30),tasks(42,'relation',30))
    def test_behaviour_repeatable(self):
        self.assertEqual(behaviour_fingerprint(self.pool[341]),behaviour_fingerprint(self.pool[341]))
    def test_mother_paired_and_not_certified(self):
        r=paired_experiment([self.pool[0],self.pool[122]],seed=44)
        self.assertEqual(len(r['stages']),4)
        self.assertTrue(r['mother_proxy'])
        self.assertEqual(r['scope'],'SYNTHETIC_EXPLORATION_ONLY')
    def test_audit(self):
        r=audit_catalogue();self.assertEqual(r['registered_variants'],7777)
        self.assertTrue(r['single_step_parent_mutations_valid'])
        self.assertEqual(r['certified_ais'],0)
