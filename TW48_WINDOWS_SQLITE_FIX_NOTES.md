# TW48 Windows SQLite handle fix — 2026-10-13

## Reported Windows failure

`VERIFY_AND_START_TW48_WINDOWS.ps1` correctly blocked launch when 8 of 201 tests failed on Windows with `PermissionError: [WinError 32]` deleting temporary SQLite files. SQLite `Connection.__exit__` commits or rolls back but does not close; on Windows an unclosed connection locks files.

## Corrective changes

Eight persistence tests now explicitly close every SQLite connection using `contextlib.closing` while retaining transaction context. One additional arena test also closes unconditionally. Added `test_windows_sqlite_lifetime.py`. The source, experiment protocols, training data, service ports and Mother/Blackbox were not changed.

## Local verification

`python -m unittest discover -s tests -q`: 202 tests PASS in Linux. SQLite integrity checked on all bundled `*.sqlite` snapshots. SHA-256 manifest regenerated. Windows confirmation is pending user running the provided verification script. Do not bypass regression test gate or replace a running 28723/28724 server.
