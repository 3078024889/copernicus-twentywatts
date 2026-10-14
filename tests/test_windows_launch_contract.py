import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class WindowsLauncherTests(unittest.TestCase):
    def test_both_launch_modes_enforce_full_pool(self):
        for name in ('START_BACKGROUND_WINDOWS.ps1', 'START_OFFLINE_ORACLE.ps1'):
            s=(ROOT/'scripts'/name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertIn('--all-configs',s)
                self.assertIn('ValidateRange(1,7777)',s)
                self.assertIn('full_pool_fair_v2.sqlite',s)
                self.assertIn('STOP_FULL_POOL',s)
                self.assertNotIn('v14_offline.sqlite',s)
    def test_stop_targets_full_pool(self):
        s=(ROOT/'scripts'/'STOP_OFFLINE_ORACLE.ps1').read_text(encoding='utf-8')
        self.assertIn('STOP_FULL_POOL',s)
