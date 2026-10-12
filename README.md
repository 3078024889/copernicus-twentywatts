# TWENTYWATTS | Integrated research release (V8 + V9 + safe operations)

**Status:** locally tested research runtime, **NOT** deployed production, **NOT** twelve certified AI agents.

## Evidence boundary

- V8 has **7,777 uniquely parameterized configurations** across **two** model families and **two** learning-rate schedules. No claim of 7,777 independently discovered algorithms.
- The packaged `data/v8.sqlite` contains 31,108 screening plus 1,800 holdout trial records. Results were generated in synthetic environments.
- V9 has 12 *research participants*, each with checkpointed weights and steps. **None** is a certified winner.
- Early V9 longitudinal synthetic experiment observed negative transfer: persistent learner performance was about 2.92 percentage points below cold-start training. Longer-running cycles are exploratory only.
- `Mother/Blackbox/V3` remain separate and unmodified. All promotion paths in this release are hard-locked. No external LLM/API or real-world source-data learning is included.

## Run on Windows

Unzip into its own folder, **not into old V3**. From PowerShell:

```powershell
& '.\scripts\RUN_WINDOWS.ps1' -Action test
& '.\scripts\RUN_WINDOWS.ps1' -Action inspect
& '.\scripts\RUN_WINDOWS.ps1' -Action run -Cycles 3 -Participants 12
```

If PowerShell execution policy prevents scripts, run with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\scripts\RUN_WINDOWS.ps1' -Action test
```

Run bounded repeated sessions in the **foreground** only (Ctrl+C to stop):

```powershell
& '.\scripts\RUN_WINDOWS.ps1' -Action run -Cycles 1 -Participants 12 -Repeat -IntervalSeconds 600
```

The run will refuse an existing `.runlock`; manually investigate any stale lock before removing it. The *current* V9 implementation advances requested new cycles each invocation; repeating forever is not evidence of algorithmic evolution. Keep bounded and periodically review holdout/cold-start comparison.

## Publishing code safely to the public repository

- The repository main base is V8 commit `3bc6d8a`, as reported by the user's terminal.
- Copy `tw8/`, `tw9/`, `tw10/`, `tests/`, `scripts/`, `README.md`, `.gitignore` into the **existing** V8 Git working directory. Review `git status` before committing.
- Do **not** copy `data/`, `reports/` or checkpoint databases into Git. This package deliberately includes local SQLite research evidence but `.gitignore` excludes it from public code control.
- GitHub connector write returned HTTP 403; no claim is made that this release has been pushed.

## Production acceptance still missing

Real non-synthetic multi-domain data and disjoint evaluation, comprehensive diversity auditing, statistically powered negative-transfer mitigation, stable 12-agent learning state, supervised software-change experiment sandbox, Windows same-host speed tests, and a safe migration of the existing 28720 service. Do not treat this archive as a drop-in production upgrade.
