"""Isolated, bounded TwentyWatts operations. No uncontrolled self-edit or Mother promotion."""
from __future__ import annotations
import argparse, json, os, socket, sqlite3, time
from contextlib import contextmanager, closing
from pathlib import Path
from tw9.continuity import run as continuity_run

PROTOCOL='TW10_SAFE_RESEARCH_OPERATIONS_V1'

@contextmanager
def single_writer(path: Path):
    """Fail closed on another writer; stale locks require explicit manual review."""
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as e:
        raise RuntimeError(f'Existing lock: {path}; check active process before removal') from e
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write(json.dumps({'pid':os.getpid(),'host':socket.gethostname(),'created':time.time()}))
        yield
    finally:
        path.unlink(missing_ok=True)

def inspect(v8db, v9db):
    v8db=Path(v8db);v9db=Path(v9db)
    if not v8db.is_file():raise FileNotFoundError(f'V8 source database not found: {v8db}')
    with closing(sqlite3.connect(f'file:{v8db.resolve().as_posix()}?mode=ro',uri=True)) as c:
        integral=c.execute('PRAGMA integrity_check').fetchone()[0]
        n=c.execute("SELECT COUNT(*) FROM registry").fetchone()[0]
        screens=c.execute("SELECT COUNT(*) FROM trials WHERE phase='screen'").fetchone()[0]
        holdouts=c.execute("SELECT COUNT(*) FROM trials WHERE phase='holdout'").fetchone()[0]
    if (integral,n,screens,holdouts)!=('ok',7777,31108,1800):
        raise RuntimeError(f'V8 protocol evidence mismatch: {(integral,n,screens,holdouts)}')
    output={'protocol':PROTOCOL,'source':{'configurations':n,'screen':screens,'holdout':holdouts,'integrity':integral},
            'certified_independent_ais':0,'promotion':'LOCKED','training':'NOT_RUNNING'}
    if v9db.exists():
        with closing(sqlite3.connect(f'file:{v9db.resolve().as_posix()}?mode=ro',uri=True)) as c:
            if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'").fetchone():
                output['research_participants']=c.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
                output['longitudinal_cycles']=c.execute('SELECT COALESCE(SUM(cycles),0) FROM agents').fetchone()[0]
                output['continuity_integrity']=c.execute('PRAGMA integrity_check').fetchone()[0]
    return output

def execute(v8db, v9db, cycles, participants=12):
    if not 1<=cycles<=25:raise ValueError('Bounded cycle count must be 1..25')
    if not 1<=participants<=12:raise ValueError('Participants must be 1..12')
    status=inspect(v8db,v9db)
    with single_writer(Path(str(v9db)+'.runlock')):
        results=continuity_run(str(v8db),str(v9db),cycles,participants)
    if results['integrity']!='ok' or results['mother_promotion']!='LOCKED':
        raise RuntimeError('Failed post-run integrity gate')
    results['source_validation']=status['source']; results['protocol_operations']=PROTOCOL
    return results
