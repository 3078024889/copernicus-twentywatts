# TwentyWatts | Unified V12 research workspace

**Current status: research operational validation passed, production NOT certified.**

## Single supported entrypoint

On Windows, run `scripts/RUN_WINDOWS.ps1 -Action test|inspect|train|gate|benchmark -PythonExe <your Python 3.12 path>`.
The script is the **only** public PowerShell entry; it loads `tw10.cli` explicitly and works with isolated Python distributions.

From a normal Python shell use `python -m tw10.cli <action>` in the project root.

- `test`: 31 unit tests, a missing local database is replaced by a temporary **test-only** synthetic fixture.
- `inspect`: read-only check of a separately supplied `data/v8.sqlite` and guarded `data/v11.sqlite` state.
- `train`: bounded, single-writer, restartable guarded research cycles in **V11-only** state.
- `benchmark`: optional scikit-learn public real-data challenge (UCI Wine and Wisconsin diagnostic), three-way stratified split, no mutation of learning checkpoints and no promotion. Requires scikit-learn; records kept separate from synthetic metrics.
- `gate`: fail-closed review of scientific and migration requirements; production remains blocked.

`data/v8.sqlite` is never committed to Git; a fresh clone must obtain legitimate source evidence by a separate, verified local import. **Training will refuse to substitute a test fixture.**

## Retained vs removed

- **Retained as internal libraries**: `tw8.arena` (registry and test generator), `tw9.continuity` (persistent state), `tw10.operations`, `tw10.guard`, `tw10.supervisor`, and `tw10.release_gate`. These implement distinct behavior and cannot yet be safely deleted.
- **Removed from this integrated workspace**: redundant `scripts/RUN_V11_WINDOWS.ps1`. One supported user entry remains.
- **Not included or touched**: original Oracle 28720, V3 worker, Mother, Blackbox, V3 Evidence, and any old production service.
- **Compatibility risk**: deprecated Python module `__main__` entrypoints still exist internally. Callers should migrate to `tw10.cli`; do not delete them until Windows dependency audit is complete.

## Evidence and release gates

7777 **parameter configurations** do not mean 7777 algorithm architectures. The historical dataset has 31,108 screening and 1800 synthetic holdout records. The 12 persistent study participants are NOT twelve certified AI models.

A transfer-protection probe may use cold restart when old weights hinder new tasks, using disjoint selection and audit data. Synthetic accuracy gains do not establish scientific discovery, real-world transfer, or production readiness.

Production blocks remain: external real-world multi-domain challenge data, independent candidate architectures, long-term retention results, supervised change proposal sandbox, measured Windows soak/performance test, and safe Oracle migration with rollback. Promotion remains **LOCKED**.

## Security and data hygiene

No secrets, SQLite state, .runlock files, model checkpoints, or generated experiments should be put into the public repo. No unattended code self-modification, no production promotion, and no implicit Git push.

## V12 independent public-data benchmark (optional)

- `scripts/RUN_WINDOWS.ps1 -Action benchmark -PythonExe <python>` executes a real-dataset **research** benchmark, not the V8/V11 synthetic arena. It requires an interpreter with scikit-learn installed; the known isolated Python on the user's machine is only verified for stdlib/SQLite, not sklearn.
- Two scikit-learn bundled datasets: UCI Wine binary class 0/1 subset (130 samples) and Wisconsin Diagnostic (569 samples). A stratified 60/20/20 split is deterministic, feature scaling is fit ONLY on training. Selection fold chooses candidate; holdout fold reports results. Test labels never select models.
- Current single-seed initial holdout observations: Wine 25/27 = 92.59%; Wisconsin 105/115 = 91.30%. These are **not** robust confidence intervals or evidence of 12 distinct AI architectures, and checkpoint mutation is disabled. Benchmark outputs are not a production-release permit.
- Production gate remains closed. Future: multi-seed protocol preregistration, adversarial tasks, paired retention/forgetting experiments, real Windows-soak and migration rollback rehearsal.

## V13 repeated public-data validation (2026-10-12)

`benchmark-repeat` executes 5 deterministic but different stratified 60/20/20 folds of both bundled public datasets, retraining and selecting each candidate only on that fold's training/selection labels. The repeated folds are not a sealed, third-party certification holdout; do not tune the pipeline against them and then call them unbiased final evidence.

In the current environment: 39/39 tests passed; Wine mean holdout 0.91852 (range 0.88889–0.92593); Wisconsin diagnostic mean holdout 0.89043 (range 0.86087–0.92174). The protocol logs individual fold IDs, candidate identities, negative-label controls, and majority-class baselines to `reports/repeated_public_benchmark.json`. Neither benchmark nor its tests mutate training checkpoints. Production promotion stays locked. The optional `scikit-learn` dependency must be installed and validated separately on Windows.

**Still blocking release:** independent multi-domain long-term transfer and forgetting audits; diversity beyond two candidate architecture families; rigorous 12-winner certification; operator-reviewed deployment/rollback rehearsal on Windows, and Oracle 28720 acceptance tests. No V13 code has been pushed to GitHub main; main remains on the earlier Windows-validated V8/V9 revision unless separately changed.

## V14 Offline Oracle (2026-10-12)

**New functional local service:** `tw10.offline_oracle` serves the new independent Oracle at `http://127.0.0.1:28722/`, JSON at `/api/live`, and executes guarded, recoverable learning cycles without calling external APIs. The page refreshes automatically. No browser internet connection required.

**Windows first run:** use `scripts/START_OFFLINE_ORACLE.ps1` from this package (Python `C:\Python314\python.exe`). Open 28722 in the browser. Stop with Ctrl+C or the explicit `scripts/STOP_OFFLINE_ORACLE.ps1` stop request. On restart, remove the stop file deliberately before resuming.

**Windows background run:** `scripts/START_BACKGROUND_WINDOWS.ps1` starts `C:\Python314\pythonw.exe` after checking that 28722 is unused, and checks `/api/live`. Optional `scripts/INSTALL_LOGIN_AUTOSTART.ps1` adds a per-user Windows Startup shortcut; `-Remove` undoes that registration. Neither tool automatically stops V3 or opens remote network ports. The background service will not automatically recover from an unexpected worker exception: it stops training and reports `ERROR`, requiring diagnosis.

**Real scope:** the source database holds 7777 *parameter configurations*, with 31,108 synthetic screening and 1800 synthetic holdout records. Training uses a separately checkpointed group of 12 *research participants*. It **does not** certify twelve distinct AI algorithms, and does not migrate the historical V3 Mother/Blackbox or claim a production cutover. The original 28720 service remains untouched; the new server is deliberately read-only over HTTP and restricted to loopback. Local data must not be published to a public Git repository.


## TW18 — Paired four-architecture audit

Run `python -m tw10.cli architecture-audit --architecture-seeds 12`; real-world certification remains disabled. See `TW18_EXPERIMENT_FINDINGS.md`. Source-only GitHub main sync: `scripts/SYNC_MAIN_WINDOWS.ps1 -Repo <existing V8 checkout> -PythonExe C:\Python314\python.exe`. This is an explicit, manual, fail-closed operation.
