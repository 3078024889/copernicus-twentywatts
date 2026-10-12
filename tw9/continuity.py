"""V9 bounded, resumable longitudinal study; no production promotion.

Research identities persist weights and steps. A completed cycle is atomic.
Unknown-task probes are never used for online updates.
"""
from __future__ import annotations
import argparse, json, random, sqlite3, statistics, math
from contextlib import closing
from pathlib import Path
from tw8.arena import Candidate, Learner, dataset, registry, connect as v8_connect, shortlist as v8_shortlist, PROTOCOL as V8_PROTOCOL
from tw10.guard import choose

PROTOCOL = 'TW9_CONTINUITY_V1'
TASKS = ('linear','interaction','shift')

def agent_pool(source_db: str, limit=12):
    """Select study participants from V8 screen evidence, not certify 12 winners."""
    with closing(sqlite3.connect(f'file:{Path(source_db).resolve().as_posix()}?mode=ro', uri=True)) as db:
        n=db.execute("SELECT COUNT(*) FROM trials WHERE protocol=? AND phase='screen'", (V8_PROTOCOL,)).fetchone()[0]
        if n != 31108:
            raise ValueError(f'V8 full screen not present: {n} records; expected 31108')
        ids=v8_shortlist(db, max(limit,60))
        seat_rows=db.execute('SELECT candidate FROM seats WHERE protocol=? ORDER BY slot',(V8_PROTOCOL,)).fetchall()
        priority=[r[0] for r in seat_rows]
        ids=list(dict.fromkeys(priority+ids))[:limit]
        lookup={c.key:c for c in registry()}
        return [lookup[k] for k in ids]

def init_db(path):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(path, timeout=30)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout=30000')
    db.executescript('''CREATE TABLE IF NOT EXISTS agents(
      id TEXT PRIMARY KEY, definition TEXT NOT NULL, state TEXT NOT NULL,
      cycles INTEGER NOT NULL DEFAULT 0, updated_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS evidence(
      protocol TEXT NOT NULL, id TEXT NOT NULL, cycle INTEGER NOT NULL,
      task TEXT NOT NULL, details TEXT NOT NULL,
      PRIMARY KEY(protocol,id,cycle));
    CREATE TABLE IF NOT EXISTS manifest(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    return db

def setup(db, candidates):
    with db:
        for c in candidates:
            state={'weights':[0.0]*(4 if c.family=='interaction' else 3),'steps':0,'experience_steps':0}
            db.execute('INSERT OR IGNORE INTO agents(id,definition,state) VALUES (?,?,?)',
                       (c.key,json.dumps(c.definition(),sort_keys=True),json.dumps(state)))
        saved=db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
        if saved!=len(candidates):
            raise ValueError('Refusing to mix incompatible study pools')
        manifest={'protocol':PROTOCOL,'pool':','.join(x.key for x in candidates),
                  'source_protocol':V8_PROTOCOL,'learning_policy':'TW11_TRANSFER_GUARD_V1'}
        if db.execute('SELECT COALESCE(SUM(cycles),0) FROM agents').fetchone()[0] > 0 and not db.execute("SELECT 1 FROM manifest WHERE key='learning_policy'").fetchone():
            raise ValueError('Legacy checkpoint requires separate database: use data/v11.sqlite')
        for k,v in manifest.items():
            existing=db.execute('SELECT value FROM manifest WHERE key=?',(k,)).fetchone()
            if existing and existing[0]!=v:raise ValueError(f'manifest mismatch: {k}')
            db.execute('INSERT OR IGNORE INTO manifest(key,value) VALUES (?,?)',(k,v))

def restore(c,state):
    l=Learner(c)
    s=json.loads(state)
    if len(s['weights'])!=len(l.w) or not all(type(v) in (int,float) and math.isfinite(v) and abs(v)<1e8 for v in s['weights']):
        raise ValueError('Invalid checkpoint weights')
    if type(s['steps']) is not int or s['steps']<0:raise ValueError('Invalid checkpoint steps')
    l.w=[float(v) for v in s['weights']];l.steps=s['steps'];return l

def step(db,c):
    record=db.execute('SELECT state,cycles FROM agents WHERE id=?',(c.key,)).fetchone()
    if not record:raise ValueError('Unregistered candidate')
    state,cycle=record
    # Each cycle has a new deterministic training set and an unseen probe set.
    task=TASKS[cycle%len(TASKS)]
    seed=100000+cycle*137+int(c.key[1:])
    train=dataset(seed,task,48)
    probe=dataset(seed+700000,task,96)
    learner=restore(c,state)
    before=learner.accuracy(probe)
    cold=Learner(c)
    for x,y in train:cold.update(x,y)
    negative=Learner(c)
    rng=random.Random(f'{PROTOCOL}/{c.key}/{cycle}/negative')
    for x,y in train:negative.update(x,rng.randint(0,1))
    # Existing weights are retained across different tasks.
    for x,y in train:learner.update(x,y)
    # The guard chooses without using the audit/test probe, preserving a clean
    # separation between model selection and independently reported evidence.
    decision=choose(learner,cold,seed=seed,task=task)
    learner=decision.selected
    after=learner.accuracy(probe)
    # Forgetting probe uses an unseen dataset from the prior task.
    prev_task=TASKS[(cycle-1)%len(TASKS)]
    forgotten_probe=dataset(seed+900000,prev_task,96)
    details={'seed':seed,'task':task,'before':before,'after':after,
             'delta':after-before,'cold_accuracy':cold.accuracy(probe),
             'negative_accuracy':negative.accuracy(probe),
             'prior_task_probe_accuracy':learner.accuracy(forgotten_probe),
             'learning_steps':learner.steps,'transfer_guard':decision.details(),'kind':'SYNTHETIC_RESEARCH_ONLY'}
    old_experience=json.loads(state).get('experience_steps',cycle*48)
    saved=json.dumps({'weights':learner.w,'steps':learner.steps,'experience_steps':old_experience+len(train)},sort_keys=True)
    # Compare-and-swap transaction prevents accidental double advancement.
    with db:
        count=db.execute('UPDATE agents SET state=?,cycles=cycles+1,updated_utc=CURRENT_TIMESTAMP WHERE id=? AND cycles=?',
                         (saved,c.key,cycle)).rowcount
        if count!=1:raise RuntimeError('Concurrent checkpoint update rejected')
        db.execute('INSERT INTO evidence(protocol,id,cycle,task,details) VALUES (?,?,?,?,?)',
                   (PROTOCOL,c.key,cycle,task,json.dumps(details,sort_keys=True)))
    return details

def run(v8_db,db_path,cycles=3,limit=12):
    if cycles<0 or cycles>200:raise ValueError('cycles must be 0..200')
    if limit<1 or limit>12:raise ValueError('limit must be 1..12')
    selected=agent_pool(v8_db,limit)
    db=init_db(db_path)
    try:
        setup(db,selected)
        advanced=0
        for c in selected:
            for _ in range(cycles):step(db,c);advanced+=1
        return report(db,advanced)
    finally:db.close()

def report(db,advanced=0):
    agents=db.execute('SELECT id,cycles,state FROM agents ORDER BY id').fetchall()
    results=[json.loads(row[0]) for row in db.execute('SELECT details FROM evidence WHERE protocol=?',(PROTOCOL,))]
    return {'protocol':PROTOCOL,'study_participants':len(agents),
      'participant_ids':[x[0] for x in agents],
      'participant_cycles':{x[0]:x[1] for x in agents},
      'advanced_this_run':advanced,'evidence_records':len(results),
      'mean_longitudinal_minus_cold':round(statistics.fmean(r['after']-r['cold_accuracy'] for r in results),5) if results else None,
      'mean_after_minus_negative':round(statistics.fmean(r['after']-r['negative_accuracy'] for r in results),5) if results else None,
      'transfer_guard':{'enabled':True,'reset_count':sum(x.get('transfer_guard',{}).get('action')=='reset' for x in results),'mean_audit_gain_vs_cold':round(statistics.fmean(x['transfer_guard']['audit_gain_vs_cold'] for x in results if 'transfer_guard' in x),5) if any('transfer_guard' in x for x in results) else None},
      'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
      'certified_independent_ais':0,'mother_promotion':'LOCKED',
      'note':'Participants are study candidates, not 12 certified independent AI systems.'}
