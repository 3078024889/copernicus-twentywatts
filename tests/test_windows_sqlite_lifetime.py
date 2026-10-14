"""Regression: sqlite3.Connection context does NOT close the handle on exit."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

class WindowsSqliteLifetimeTests(unittest.TestCase):
    def test_transaction_and_explicit_close_before_unlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"lifetime.sqlite"
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute("CREATE TABLE records(value INTEGER)")
                conn.execute("INSERT INTO records VALUES (7)")
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")
            with closing(sqlite3.connect(path)) as verify:
                self.assertEqual(verify.execute("SELECT value FROM records").fetchone()[0], 7)
            path.unlink()
            self.assertFalse(path.exists())
