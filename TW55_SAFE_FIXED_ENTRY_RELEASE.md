# TW55 — fixed entry port ownership and migration rollback

## Why TW54 migration stopped
User Windows output: PID 10956 listening on 28720 and PID 7920 listening on 28727. No database migration performed. NEVER infer the PID identity from port alone.

## Changes
- scripts/INSPECT_PORT_OWNERS_WINDOWS.ps1 reports PID, parent PID, process command line for both ports. It never stops or deletes programs.
- scripts/SWITCH_TO_FIXED_28720_WINDOWS.ps1 invokes the inspector when either port is occupied and refuses migration.
- scripts/migrate_native_state.py rolls back both previously existing targets and newly installed sidecar databases if post-commit verification fails.
- tests/test_tw55_port_owner_contract.py checks port inspection safety and simulates mid-migration failure.

## Windows migration procedure
1. Decompress TW55 to `D:\TWENTYWATTS_TW55_SAFE_FIXED_ORACLE_FULL_MASTER_20261013\TWENTYWATTS_UNIFIED_MASTER`.
2. Run the port inspector: `powershell -NoProfile -ExecutionPolicy Bypass -File "$New\scripts\INSPECT_PORT_OWNERS_WINDOWS.ps1"`.
3. Identify owners of 28720/28727. Stop only confirmed old Oracle services normally via their console CTRL+C. If a process is supervised, identify/stop its supervisor first. Do not terminate unknown apps.
4. Repeat inspection until both ports are free. Then run the TW55 switch script pointing PreviousRoot to latest TW53. The migration reads the latest TW53 SQLite state and preserves old installation untouched.
5. Verify http://127.0.0.1:28720/ and audit state. Do not discard the old directory until full verification and rollback exercises are complete.

## Evidence scope
This release changes only deployment safety and rollback. It does not add an AI learning breakthrough, and 0/12 AI certifications remain. CPU / Windows long-term stability require actual Windows validation. GitHub main not automatically updated.
