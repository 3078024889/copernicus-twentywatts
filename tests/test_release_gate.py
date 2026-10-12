import unittest,tempfile
from pathlib import Path
from fixture_source import source_db
from tw10.release_gate import assess
class ReleaseGateTests(unittest.TestCase):
    def test_synthetic_never_certifies(self):
        with tempfile.TemporaryDirectory() as d:
            result=assess(source_db(),Path(d)/'unused.sqlite')
            self.assertTrue(result['operational_integrity'])
            self.assertFalse(result['eligible_for_production'])
            self.assertEqual(result['certified_independent_ais'],0)
            self.assertEqual(result['mother_promotion'],'LOCKED')
            self.assertIn('REAL_WORLD_HOLDOUT_NOT_VERIFIED',result['blockers'])
if __name__=='__main__':unittest.main()
