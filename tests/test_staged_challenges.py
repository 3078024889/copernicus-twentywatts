import tempfile
import unittest
from pathlib import Path
from tw8.arena import registry
from tw10.staged_challenges import evaluate, run

class StagedChallengeTests(unittest.TestCase):
    def test_stages_disjoint(self):
        r=evaluate(registry()[0],8)
        self.assertEqual([x['task'] for x in r['stages']],['linear','interaction','shift','linear'])
        for x in r['stages']:
            self.assertEqual(len({x['train_fingerprint'], x['selector_fingerprint'],x['holdout_fingerprint']}),3)
        self.assertFalse(r['certified'])
    def test_paired_candidates_share_exact_same_task_data(self):
        a=evaluate(registry()[0],7)
        b=evaluate(registry()[1],7)
        for x,y in zip(a['stages'],b['stages']):
            for field in ('train_fingerprint','selector_fingerprint','holdout_fingerprint'):
                self.assertEqual(x[field],y[field])
    def test_reproducibility(self):
        self.assertEqual(evaluate(registry()[11],3),evaluate(registry()[11],3))
    def test_idempotency(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'staged.sqlite'
            one=run(p,['G0001','G0012'],(1,2))
            two=run(p,['G0001','G0012'],(1,2))
            self.assertEqual(one['new_trials'],4)
            self.assertEqual(two['new_trials'],0)
            self.assertEqual(two['total_trials'],4)
            self.assertEqual(two['integrity'],'ok')
            self.assertEqual(two['certified_independent_ais'],0)
    def test_cohort_results_are_not_contaminated(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'staged.sqlite'
            run(p, ['G0001'], (1, 2))
            narrow = run(p, ['G0012'], (3,))
            self.assertEqual(narrow['total_trials'], 1)
            self.assertEqual(narrow['stored_trials_all_cohorts'], 3)
            self.assertEqual(narrow['requested_candidates'], 1)
            self.assertEqual(narrow['requested_seeds'], 1)
            self.assertEqual(narrow['stage_results'][0]['observations'], 1)
    def test_duplicate_candidate_or_seed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'staged.sqlite'
            with self.assertRaises(ValueError): run(p, ['G0001','G0001'], (1,))
            with self.assertRaises(ValueError): run(p, ['G0001'], (1,1))
            with self.assertRaises(ValueError): run(p, ['G0001'], ())
    def test_bad_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run(Path(d)/'s.sqlite',['NOT_A_CANDIDATE'])

class CliStageTests(unittest.TestCase):
    def test_challenge_cli_accepts_verified_source(self):
        from tw10.cli import main
        from fixture_source import source_db
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'s.sqlite'
            self.assertEqual(main(['challenge','--source-db',str(source_db()),
                '--challenge-db',str(target),'--challenge-count','2','--challenge-seeds','1']),0)
            self.assertTrue(target.exists())
