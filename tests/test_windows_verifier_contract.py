import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class WindowsSQLiteVerifierContract(unittest.TestCase):
    def test_powershell_invokes_script_not_inline_python(self):
        script = (ROOT / 'scripts' / 'VERIFY_AND_START_TW48_WINDOWS.ps1').read_text(encoding='utf-8')
        self.assertIn('verify_sqlite_evidence.py', script)
        self.assertIn('--source $Source --state $State', script)
        self.assertNotIn('$Probe=@', script)
        self.assertNotIn('-c $Probe', script)

    def test_read_only_uri_and_connection_close(self):
        verifier = (ROOT / 'scripts' / 'verify_sqlite_evidence.py').read_text(encoding='utf-8')
        self.assertIn('src.as_uri() + "?mode=ro"', verifier)
        self.assertIn('with closing(sqlite3.connect', verifier)
        self.assertIn('with closing(init(', verifier)
