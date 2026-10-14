# TW46 — CPU-measured cross-generation research and offline Oracle integration

## Evidence and source-first limits

The novel describes dendritic connections, algorithm variants, knowledge challenges and eventual self-improvement; it does not provide an executable per-arm CPU budgeting formula. This resource measurement and independent research scheduling are engineering hypotheses. The source-first goal remains independently verified learning-method improvement, not merely a live process or green tests.

## New code

- `tw10/resource_meter.py`: real process CPU seconds, wall seconds, start/end resident memory; no fabricated energy or peak RSS.
- `tw10/inherited_routing.py`: optional per-arm process CPU profiling; deterministic regular algorithm evidence is unchanged when profiling is off.
- `tw10/compute_backtest.py`: isolated child-process research runs, per-arm CPU ratio, paired accuracy, equal-update/probe flags, and certification remains locked.
- `tw10/offline_oracle.py`: background research run every N training batches, separately persisted `*.research.json`, `/api/live` includes research status and per-batch resources. Research errors are isolated from full-pool checkpoint. Dashboard clearly labels 7777 as initial configurations, not verified algorithms.
- `scripts/START_OFFLINE_ORACLE.ps1`: new `-ResearchEvery`, `-ResearchSeeds`, `-StateDBOverride`; use alternate port to verify safely.
- `scripts/START_BACKGROUND_WINDOWS.ps1`: passes research schedule into background server.
- `tw10/cli.py`: `compute-backtest` standalone repeatable experiment.

## Verified local lab

- Unittest discovery **199/199 passing**, including resource, HTTP research cycle and retained deterministic algorithm evidence tests.
- TW46 compute-backtest: 24 paired synthetic seeds, 24 equal model update/probe count, **22/24 within ±10% per-arm CPU**, mean CPU ratio inherited/reset **1.016** (measured, not enforced), mean unknown relation +0.521 percentage points and retention +0.130 pp. Results are exploratory and not an efficacy certification.
- Total recorded process CPU about 2.15 s for 24 isolated paired runs; highest end-of-process resident memory ~101.6MB. Neither is a Windows measurement or peak RSS.
- **0/12 certified**; real V3 Mother integration remains unverified. The legacy `full_pool_fair_v2` is candidate-configuration longitudinal training; TW45 research is a **separate scheduled investigation**, not yet the 7777-variant evolutionary scheduler.

## Windows rollout: new port first, no deletion

Unpack the unified master into a new location. Start the new service on port 28724 without shutting down the old one:

```powershell
$Root = 'D:\TWENTYWATTS_TW46_UNIFIED_MASTER\TWENTYWATTS_UNIFIED_MASTER'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\START_OFFLINE_ORACLE.ps1" -PythonExe 'C:\Python314\python.exe' -Port 28724 -ResearchEvery 2 -ResearchSeeds 4
```

Confirm `http://127.0.0.1:28724/api/live` shows `worker`, `all_candidates`, `research`, and `worker.latest.resources`. Keep the PowerShell window open. For production reduce extra CPU overhead by increasing `-ResearchEvery 20`. No POST/start/delete action is exposed through HTTP. This deliberately creates a different new checkpoint rather than claiming to automatically migrate the live `28723` state. Historical V3 remains untouched.

After verifying this, push code to GitHub using `scripts/SYNC_MAIN_WINDOWS.ps1` as in the previously successful `e849351` Windows push, targeting the existing clean Git `main` checkout. The cloud connector did not grant repository write (403); no cloud push can be claimed.
