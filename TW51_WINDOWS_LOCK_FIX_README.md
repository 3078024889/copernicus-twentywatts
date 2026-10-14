# TW51 Windows SQLite file-lock correction — 2026-10-13

**Problem reproduced from Windows user log:** unittest `test_event_evolution.EvolutionEventTests.test_failure_persistent_idempotent_and_tamper_rejected` completed an SQLite transaction using `with sqlite3.connect(path)` without explicitly closing the connection. Python's SQLite context manager manages transactions, not connection lifetime. `TemporaryDirectory` cleanup subsequently raised WinError 32 for `e.sqlite`.

**Corrections:**
1. `tests/test_event_evolution.py`: use `contextlib.closing(sqlite3.connect(...))` around the evidence-tamper operation, nesting `with db:` inside for transaction commit.
2. `scripts/VERIFY_AND_START_TW48_WINDOWS.ps1`: use explicit `closing(...)` for both source (read-only) and target checkpoint connections in preflight integrity verification.

**Scope:** lifecycle correction only. No changes to learning algorithms, checkpoint structure, event-protocol version or existing data. Old TW49/TW51 services must not be overwritten while running.

**Local verification:** Linux environment: `python -m unittest discover -s tests -q` — 209 tests pass. Windows file-lock behavior must be confirmed by running the normal Windows launcher on the user's PC. Production deployment, Mother migration and 12-seat certification remain pending.
