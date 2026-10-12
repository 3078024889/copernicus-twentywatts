"""Single supported command-line entrypoint for guarded research operations.

This runner cannot write to Mother, V3 or Blackbox and never certifies winners.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import unittest
from pathlib import Path
from .operations import inspect
from .release_gate import assess
from .supervisor import supervise

ROOT = Path(__file__).resolve().parents[1]

def main(argv=None):
    ap = argparse.ArgumentParser(description='TwentyWatts verified research entrypoint')
    ap.add_argument('action', choices=('test', 'inspect', 'train', 'gate', 'benchmark', 'benchmark-repeat', 'challenge', 'architecture-audit'))
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--source-db', type=Path)
    ap.add_argument('--state-db', type=Path)
    ap.add_argument('--batches', type=int, default=1)
    ap.add_argument('--cycles', type=int, default=1)
    ap.add_argument('--participants', type=int, default=12)
    ap.add_argument('--stop-file', type=Path)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--challenge-count', type=int, default=24)
    ap.add_argument('--challenge-seeds', type=int, default=3)
    ap.add_argument('--challenge-db', type=Path)
    ap.add_argument('--architecture-seeds', type=int, default=5)
    ap.add_argument('--architecture-db', type=Path)
    a = ap.parse_args(argv)
    root = a.root.resolve()
    source = (a.source_db or root / 'data' / 'v8.sqlite').resolve()
    state = (a.state_db or root / 'data' / 'v11.sqlite').resolve()
    # Strong safety boundary: reject an older state target and the immutable V8 source.
    prohibited = {source, (root / 'data' / 'v9.sqlite').resolve(), (root / 'data' / 'tw8.sqlite').resolve()}
    if a.action != 'test' and state in prohibited:
        ap.error('State path collides with V8 source or legacy V9 database; refusing to modify')
    if a.action in ('benchmark', 'benchmark-repeat'):
        from .real_benchmark import evaluate, evaluate_repeated
        payload = evaluate_repeated() if a.action == 'benchmark-repeat' else evaluate()
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if a.action == 'test':
        tests = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root / 'tests'))
        result = unittest.TextTestRunner(verbosity=2).run(tests)
        return 0 if result.wasSuccessful() else 1
    if not source.is_file():
        ap.error(f'Missing verified V8 source: {source}. Never use synthetic fixture for training.')
    if a.action == 'architecture-audit':
        from .architecture_audit import run as architecture_run
        if not 1 <= a.architecture_seeds <= 30: ap.error('Invalid architecture seed count')
        destination=(a.architecture_db or root/'data'/'architecture_audit.sqlite').resolve()
        if destination in prohibited: ap.error('Architecture database path collision')
        payload=architecture_run(destination,range(201,201+a.architecture_seeds))
    elif a.action == 'challenge':
        import sqlite3
        from contextlib import closing
        from .staged_challenges import run as run_challenges
        from tw8.arena import registry
        from tw8.arena import PROTOCOL as SOURCE_PROTOCOL
        if not (1 <= a.challenge_count <= 7777 and 1 <= a.challenge_seeds <= 30):
            ap.error('Challenge count or seed count out of bounds')
        with closing(sqlite3.connect(f'file:{source.as_posix()}?mode=ro', uri=True)) as conn:
            count = conn.execute('SELECT COUNT(*) FROM registry').fetchone()[0]
            trials = conn.execute('SELECT COUNT(*) FROM trials WHERE protocol=?',(SOURCE_PROTOCOL,)).fetchone()[0]
            if (count, trials) != (7777,32908):ap.error('Unverified V8 source database')
        destination = (a.challenge_db or root/'data'/'staged_challenges.sqlite').resolve()
        if destination in prohibited or destination == source: ap.error('Challenge database path collision')
        pool=registry()
        stride=max(1,len(pool)//a.challenge_count)
        selected=[c.key for c in pool[::stride]][:a.challenge_count]
        payload=run_challenges(destination,selected,range(1,a.challenge_seeds+1))
    elif a.action == 'inspect':
        payload = inspect(source, state)
    elif a.action == 'gate':
        payload = assess(source, state)
    else:
        stop = a.stop_file if a.stop_file else root / 'data' / 'STOP_TW11'
        payload = supervise(source, state, batches=a.batches, cycles=a.cycles,
                            participants=a.participants, stop_file=stop, report=a.report)
    if a.report and a.action in ('inspect', 'gate'):
        a.report.parent.mkdir(parents=True, exist_ok=True)
        temp = a.report.with_suffix(a.report.suffix + '.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, a.report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
