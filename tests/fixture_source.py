"""Portable unit-test fixture ONLY; never used by production training entrypoints.

A fresh public Git clone contains no private SQLite state. Tests may create a
reproducible synthetic V8 source; operational run requires a separate source DB.
"""
import atexit, tempfile
from pathlib import Path
from tw8.arena import connect, register, screen, shortlist, verify, select

_TEMP=None

def source_db():
    global _TEMP
    actual=Path(__file__).resolve().parents[1]/'data'/'v8.sqlite'
    if actual.is_file():
        return actual
    if _TEMP is None:
        _TEMP=tempfile.TemporaryDirectory(prefix='tw11_fixture_')
        atexit.register(_TEMP.cleanup)
        fixture=Path(_TEMP.name)/'synthetic-v8.sqlite'
        db=connect(fixture)
        try:
            register(db)
            screen(db)
            shortlisted=shortlist(db)
            verify(db,shortlisted)
            select(db,shortlisted)
        finally:
            db.close()
    return Path(_TEMP.name)/'synthetic-v8.sqlite'
