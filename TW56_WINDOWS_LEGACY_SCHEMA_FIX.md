# TW56 Windows upgrade compatibility: TW55 descendant_learning table absent

Failure reproduced: `sqlite3.OperationalError: no such table: descendant_learning` at `verify_all()` in `migrate_native_state.py`, because TW55 databases predate TW56's per-descendant training evidence table.

Repair: `tw10.dendrite_native.verify_all` and `progress` accept absent `descendant_learning` as an explicitly legacy (non-retroactive) evidence state; `database()` creates the table when TW56 becomes the sole writer. No fictitious old descendant-learning records are generated. Migration remains stopped unless legacy writer is off. Existing checkpoint and `learning`, `offspring` evidence checks remain mandatory.

Validation: 227 regression tests, including 2 new cases: verify legacy without table, and migrate old -> new -> continue training, preserving old evidence. Windows production verification remains required.

Cleanup: don't delete TW55 source while it is the last intact migration source. Archive historic evidence outside release folders before removal. The zip ships independent demonstration snapshots, not the live updated Windows checkpoints.
