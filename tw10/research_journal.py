"""Durable, append-only research evidence journal for local offline service.

The journal is intentionally separate from learning checkpoints and immutable V3 data.
It never certifies AIs; restarts can resume dispatch counts without destroying evidence.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

PROTOCOL = 'TW48_OFFLINE_JOURNAL_V1'

def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def init(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute('PRAGMA busy_timeout=10000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS journal (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol TEXT NOT NULL,
        kind TEXT NOT NULL,
        payload TEXT NOT NULL,
        digest TEXT NOT NULL,
        at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    return db

def append(db,kind,payload):
    if kind not in ('training','research','research_error','service'):
        raise ValueError('Unsupported journal kind')
    body = canonical(payload)
    digest=hashlib.sha256((PROTOCOL+'\n'+kind+'\n'+body).encode()).hexdigest()
    with db:
        cur=db.execute('INSERT INTO journal(protocol,kind,payload,digest) VALUES(?,?,?,?)',
                       (PROTOCOL,kind,body,digest))
    return cur.lastrowid

def record(path,kind,payload):
    with closing(init(path)) as db:
        return append(db,kind,payload)

def inspect(path, *, tail=4):
    if not Path(path).exists():
        return {'entries':0,'training_batches':0,'research_completed':0,'research_failed':0,'latest':[],'integrity':'NOT_CREATED'}
    with closing(sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        records=dict(db.execute('SELECT kind,COUNT(*) FROM journal WHERE protocol=? GROUP BY kind',(PROTOCOL,)))
        rows=db.execute('SELECT seq,kind,payload,digest,at_utc FROM journal ORDER BY seq DESC LIMIT ?', (tail,)).fetchall()
        research_row=db.execute(
            "SELECT seq,kind,payload,digest,at_utc FROM journal WHERE protocol=? AND kind IN ('research','research_error') ORDER BY seq DESC LIMIT 1",
            (PROTOCOL,)).fetchone()
        latest_research=None
        if research_row:
            seq,kind,body,digest,at=research_row
            expected=hashlib.sha256((PROTOCOL+'\n'+kind+'\n'+body).encode()).hexdigest()
            if digest!=expected:raise RuntimeError(f'Research journal evidence digest mismatch at {seq}')
            latest_research={'seq':seq,'kind':kind,'at_utc':at,'payload':json.loads(body)}
        latest=[]
        for seq,kind,body,digest,at in rows:
            expected=hashlib.sha256((PROTOCOL+'\n'+kind+'\n'+body).encode()).hexdigest()
            if digest!=expected: raise RuntimeError(f'Journal evidence digest mismatch at {seq}')
            latest.append({'seq':seq,'kind':kind,'at_utc':at,'payload':json.loads(body)})
    return {'entries':sum(records.values()),'training_batches':records.get('training',0),
            'research_completed':records.get('research',0),'research_failed':records.get('research_error',0),
            'latest':latest,'latest_research':latest_research,'integrity':'RECENT_DIGESTS_OK'}

def verify_all(path):
    with closing(sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Research journal SQLite corruption')
        for seq,kind,body,digest in db.execute('SELECT seq,kind,payload,digest FROM journal ORDER BY seq'):
            expected=hashlib.sha256((PROTOCOL+'\n'+kind+'\n'+body).encode()).hexdigest()
            if digest!=expected:raise RuntimeError(f'Research journal evidence changed: {seq}')
    return True
