import unittest
from tw10.dendritic_structural_evolution import changed_graph, run_pair, run_study
from tw10.relational_dendrites import RelationalLearner, Variant

PARENT = Variant('ROOT','ring','context','three_factor','associative','error_slope',None,'root')

class StructuralEvolutionTests(unittest.TestCase):
    def test_edge_mutation_changes_graph_not_training_history(self):
        m=RelationalLearner(PARENT)
        children=changed_graph(m,7)
        for child,info in children:
            self.assertEqual(len(child.graph),len(m.graph))
            self.assertNotEqual(child.graph,m.graph)
            self.assertEqual(child.experience,m.experience)
            self.assertNotIn(info['removed'],child.graph)
            self.assertIn(info['inserted'],child.graph)
    def test_deterministic_selection_and_no_holdout_selection(self):
        a=run_pair(17,PARENT);b=run_pair(17,PARENT)
        self.assertEqual(a,b)
        self.assertGreaterEqual(a['selection_gain'],0)
        self.assertEqual(a['parent_updates'],a['offspring_updates'])
        self.assertEqual(a['certified_ais'],0)
    def test_study_is_not_certification(self):
        r=run_study(range(3))
        self.assertEqual(r['runs'],3)
        self.assertEqual(r['certified_ais'],0)
        self.assertEqual(len(r['trials']),3)
