"""Offline round-robin training of ALL 7777 registered configurations.

This is a bounded synthetic research experiment, not certification of AI identities.
One transaction commits each candidate's training state and fresh audit evidence.
"""
from __future__ import annotations
import json, math, sqlite3, statistics, random
from contextlib import closing
from pathlib import Path
from tw8.arena import Candidate, Learner, dataset, registry, PROTOCOL as SOURCE_PROTOCOL
from tw10.guard import choose

PROTOCOL = 'TW15_ALL_CONFIGS_LONGITUDINAL_V1'
TASKS = ('linear', 'interaction', 'shift')
EXPECTED = 7777


def init(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.execute('PRAGMA busy_timeout=30000')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS candidates (
        id TEXT PRIMARY KEY, definition TEXT NOT NULL, state TEXT NOT NULL,
        cycles INTEGER NOT NULL DEFAULT 0, experience_steps INTEGER NOT NULL DEFAULT 0,
        last_task TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS audits (
        protocol TEXT NOT NULL, id TEXT NOT NULL, cycle INTEGER NOT NULL,
        task TEXT NOT NULL, report TEXT NOT NULL,
        PRIMARY KEY(protocol,id,cycle)
      );
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS idx_candidate_cycles ON candidates(cycles,id);
    ''')
    return db


def bootstrap(db, source):
    """Reject unverified source and altered candidate identities. Never write source DB."""
    source = Path(source)
    if not source.is_file(): raise FileNotFoundError(source)
    if source.resolve() == Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve():
        raise ValueError('Source and state database may not coincide')
    with closing(sqlite3.connect(f'file:{source.resolve().as_posix()}?mode=ro', uri=True)) as old:
        if old.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Invalid source DB')
        n = old.execute('SELECT COUNT(*) FROM registry').fetchone()[0]
        screen = old.execute('SELECT COUNT(*) FROM trials WHERE protocol=? AND phase=?', (SOURCE_PROTOCOL,'screen')).fetchone()[0]
        holdout = old.execute('SELECT COUNT(*) FROM trials WHERE protocol=? AND phase=?', (SOURCE_PROTOCOL,'holdout')).fetchone()[0]
        if (n, screen, holdout) != (EXPECTED, 31108, 1800):
            raise ValueError(f'Source research coverage incomplete: {(n,screen,holdout)}')
        real = dict(old.execute('SELECT id, definition FROM registry'))
    all_candidates = registry()
    if len(all_candidates) != EXPECTED: raise ValueError('Registry size changed')
    # Refuse to attach source snapshots with different parameter definitions.
    for c in all_candidates:
        if json.loads(real[c.key]) != c.definition(): raise ValueError(f'Source identity drift: {c.key}')
    existing = dict(db.execute('SELECT key,value FROM settings'))
    if existing and (existing.get('protocol') != PROTOCOL or existing.get('source_protocol') != SOURCE_PROTOCOL):
        raise ValueError('Incompatible checkpoint format')
    with db:
        db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('protocol',PROTOCOL))
        db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('source_protocol',SOURCE_PROTOCOL))
        for c in all_candidates:
            state = {'weights':[0.0]*(4 if c.family == 'interaction' else 3), 'steps':0}
            db.execute('INSERT OR IGNORE INTO candidates(id,definition,state) VALUES (?,?,?)',
                       (c.key, json.dumps(c.definition(),sort_keys=True), json.dumps(state)))
    if db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0] != EXPECTED: raise ValueError('Pool mismatch')
    for cid, definition in db.execute('SELECT id,definition FROM candidates'):
        if json.loads(definition) != json.loads(real[cid]): raise ValueError(f'Checkpoint candidate drift: {cid}')
    return {'candidates':EXPECTED,'screen':screen,'holdout':holdout}


def cycle_once(db, c):
    row = db.execute('SELECT state,cycles,experience_steps FROM candidates WHERE id=?',(c.key,)).fetchone()
    if row is None: raise ValueError(f'Unknown candidate {c.key}')
    state_json, cycle, experience = row
    prev = json.loads(state_json)
    learner = Learner(c)
    if len(prev['weights']) != len(learner.w) or not all(math.isfinite(float(w)) for w in prev['weights']):
        raise ValueError('Corrupt state weights')
    learner.w = [float(w) for w in prev['weights']]
    learner.steps = int(prev['steps'])
    task = TASKS[(cycle + (c.index % 3)) % 3]
    seed = 2000000 + cycle*7919 + c.index
    train = dataset(seed,task,48)
    audit = dataset(seed+9000000,task,96)
    before = learner.accuracy(audit)
    cold = Learner(c)
    sham = Learner(c)
    rng=random.Random(f'{PROTOCOL}/{c.key}/{cycle}/sham')
    for x,y in train:
        learner.update(x,y)
        cold.update(x,y)
        sham.update(x,rng.randint(0,1))
    decision=choose(learner,cold,seed=seed,task=task)
    winner=decision.selected
    after=winner.accuracy(audit)
    report={'seed':seed,'before':before,'after':after,'cold':cold.accuracy(audit),
            'sham':sham.accuracy(audit),'guard':decision.action,
            'gain_vs_cold':after-cold.accuracy(audit),
            'gain_vs_sham':after-sham.accuracy(audit),
            'selection_independent_from_audit':True,
            'scope':'SYNTHETIC_ONLY'}
    new_state=json.dumps({'weights':winner.w,'steps':winner.steps},sort_keys=True)
    with db:
        updated=db.execute('''UPDATE candidates SET state=?, cycles=cycles+1,
            experience_steps=experience_steps+48,last_task=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND cycles=?''',(new_state,task,c.key,cycle)).rowcount
        if updated != 1: raise RuntimeError('State concurrency conflict')
        db.execute('INSERT INTO audits VALUES (?,?,?,?,?)',
                   (PROTOCOL,c.key,cycle,task,json.dumps(report,sort_keys=True)))
    return report


def batch(db, *, limit=64):
    if not isinstance(limit,int) or not 1 <= limit <= 7777: raise ValueError('limit must be 1..7777')
    # Fair minimum-cycles-first scheduler: every candidate reaches its next
    # cycle before a higher-cycle candidate is scheduled. No static top-12.
    ids=[x[0] for x in db.execute('SELECT id FROM candidates ORDER BY cycles ASC, id ASC LIMIT ?', (limit,))]
    all_defs={c.key:c for c in registry()}
    reports=[]
    for cid in ids: reports.append(cycle_once(db,all_defs[cid]))
    return {'advanced':len(reports),'reset_count':sum(r['guard']=='reset' for r in reports),
            'mean_gain_vs_cold':round(statistics.fmean(r['gain_vs_cold'] for r in reports),6),
            'mean_gain_vs_sham':round(statistics.fmean(r['gain_vs_sham'] for r in reports),6),
            'status':status(db)}


def status(db):
    n,min_cycle,max_cycle,sum_cycles,steps=db.execute('''SELECT COUNT(*),MIN(cycles),MAX(cycles),SUM(cycles),
        SUM(experience_steps) FROM candidates''').fetchone()
    touched=db.execute('SELECT COUNT(*) FROM candidates WHERE cycles>0').fetchone()[0]
    records=db.execute('SELECT COUNT(*) FROM audits WHERE protocol=?',(PROTOCOL,)).fetchone()[0]
    return {'registered':n,'trained_distinct':touched,'min_cycles':min_cycle,'max_cycles':max_cycle,
            'total_cycles':sum_cycles,'experience_steps':steps,'audit_records':records,
            'integrity':db.execute('PRAGMA quick_check').fetchone()[0],
            'certified_ai':0,'mother_promotion':'LOCKED'}
