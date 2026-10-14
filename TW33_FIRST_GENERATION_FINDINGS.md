# TW33 | First-generation algorithm lineage and falsifiable descendant trial

## Source-first boundary

The narrative describes 7000+ learning-algorithm variants, dendritic connectivity/weights/activation and long-term staged learning. It does **not** publish an exact executable formula for the variants, or a path from 7777 to 12. This implementation is an *engineering hypothesis* rather than an exact reconstruction of a published fictional algorithm.

## Implemented

- `tw10/first_generation.py`: idempotent 7777-entry operator-program registry with stable structural hashes and parent lineage, preserving exact genotype identities on restart.
- Each trial copies the same trained parent state and changes precisely one executable operator (topology, branch integration, plasticity, memory or meta rule) in the descendant, rather than changing a numerical parameter alone.
- Both siblings get the same training records. A selection split decides provisional acceptance; separate held-out transfer and retention splits are only audited after selection.
- Persistent evidence hash, SQLite protocol, mismatch rejection, and explicit equal-update/equal-probe flags.
- Unified `python -m tw10.cli first-generation --generation-count 120 --generation-db data/first_generation_tw33.sqlite --report reports/first_generation_tw33.json`.

## Observed evidence (2026-10-12, isolated synthetic tasks)

- First generation: 7777 different operator tuples / structural hashes. This is **not** 7777 independently validated algorithms.
- Descendant comparisons: 120; provisionally selected on selection data: 19.
- Equal-update-and-probe eligible: 118; **2 excluded due to unequal replay update budgets**.
- Eligible 118 mean sealed new-task delta: -0.2847 percentage points, mean old-task retention delta: -0.0066 percentage points.
- No certified AI; no real Mother comparison; no demonstrated knowledge discovery.
- SQLite integrity `ok`, 136/136 tests passed.

## Critical blockers for certification

1. Matching update counts and probe counts does not establish equal measured compute time or memory.
2. Five operator dimensions permit structurally different definitions, but probe collisions and functional equivalence must be investigated before declaring independent algorithms.
3. Selection is one generation, not cumulative autonomous descendants that demonstrate self-improvement.
4. All tasks remain synthetic; no sealed out-of-family real knowledge transfer.
5. The running Windows 28723 server and GitHub main were not modified.

A failed or negative result is preserved; none of these candidates receives AI-seat certification.
