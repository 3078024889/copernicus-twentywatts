"""TW56 descendant continuation has individually verifiable evidence."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from tw10.dendrite_native import advance, advance_descendants, database, digest, encode, verify_all, snapshot
from tw10.relational_dendrites import catalogue, RelationalLearner
from tw10.dendrite_native import export


class DescendantEvidenceTests(unittest.TestCase):
    def seed_child(self, path):
        # Use a legitimate catalogue parent and a checkpoint to test the
        # descendant update/audit without triggering 7777 expensive proposals.
        with closing(database(path)) as db:
            from tw10.dendrite_native import bootstrap
            bootstrap(db)
            parent = catalogue()[0]
            child_id = f'{parent.id}.g1'
            v = parent.genotype()
            state = export(RelationalLearner(parent))
            proposal = {'adopted': True, 'selection_gain': .01, 'scope': 'TEST_ONLY'}
            with db:
                db.execute('INSERT INTO offspring VALUES (?,?,?,?,?,?,?,?,?)',
                           (parent.id, 1, encode(v), .01, 0., 0., 1, encode(proposal), digest(proposal)))
                db.execute('INSERT INTO descendant_checkpoints(child_id,parent_id,birth_step,genotype,checkpoint,checkpoint_hash) VALUES(?,?,?,?,?,?)',
                           (child_id, parent.id, 1, encode(v), encode(state), digest(state)))
        return child_id

    def test_individual_descendant_steps_persist_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'native.sqlite'
            child_id = self.seed_child(path)
            self.assertEqual(advance_descendants(path, limit=1)['advanced_descendants'], 1)
            self.assertEqual(advance_descendants(path, limit=1)['advanced_descendants'], 1)
            self.assertEqual(snapshot(path)['descendant_evidence_records'], 2)
            self.assertEqual(verify_all(path)['integrity'], 'FULL_CHECK_OK')
            with closing(sqlite3.connect(path)) as db:
                with db:
                    db.execute("UPDATE descendant_learning SET domain='tampered' WHERE child_id=? AND step=1", (child_id,))
            with self.assertRaisesRegex(ValueError, 'descendant training evidence changed'):
                verify_all(path)

    def test_preexisting_descendant_steps_are_not_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'native.sqlite'; cid=self.seed_child(path)
            with closing(sqlite3.connect(path)) as db:
                with db:
                    db.execute('UPDATE descendant_checkpoints SET step=9 WHERE child_id=?', (cid,))
            # Existing TW55 steps were not per-step journaled: do not fake them.
            self.assertEqual(snapshot(path)['descendant_evidence_records'],0)
            self.assertEqual(verify_all(path)['integrity'],'FULL_CHECK_OK')
            advance_descendants(path,limit=1)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT step FROM descendant_learning').fetchone()[0],10)
            self.assertEqual(verify_all(path)['integrity'],'FULL_CHECK_OK')

if __name__ == '__main__': unittest.main()
