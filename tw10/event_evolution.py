"""Durable, bounded offline mutation trials triggered by observed learning failures.

Caution: legacy full-pool consists of parameter configs. The event selects a
separate executable D-series dendritic genotype; it does NOT transfer the G-series
learner's state. Such trials are exploratory and never award certification.
"""
from __future__ import annotations
import json
import sqlite3
import hashlib
from contextlib import closing
from pathlib import Path
from .relational_dendrites import catalogue
from .first_generation import trial

PROTOCOL = 'TW51_EVENT_DESCENDANT_V1'

def _encode(v):
    return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def _digest(v):
    return hashlib.sha256(_encode(v).encode()).hexdigest()

def _db(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=20)
    db.execute('PRAGMA busy_timeout=20000')
    db.execute('''CREATE TABLE IF NOT EXISTS event_trials (
      event_id TEXT PRIMARY KEY, protocol TEXT NOT NULL, batch INTEGER NOT NULL,
      trigger TEXT NOT NULL, observed_gain REAL NOT NULL, observed_resets INTEGER NOT NULL, observed_accuracy REAL,
      candidate TEXT NOT NULL, seed INTEGER NOT NULL, status TEXT NOT NULL,
      payload TEXT, digest TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS event_trials_state ON event_trials(status,batch)')
    db.commit()
    return db

def enqueue(path,*,batch,gain,resets,accuracy=None):
    if batch < 1: raise ValueError('batch must be >=1')
    if not isinstance(gain,(int,float)) or not (-1 <= gain <= 1): raise ValueError('gain outside [-1,1]')
    if resets < 0: raise ValueError('negative reset count')
    if accuracy is not None and not 0 <= accuracy <= 1: raise ValueError('invalid accuracy')
    # Trigger on observed aggregate failure; do not manufacture a trigger from a timer.
    if gain >= 0 and not resets and (accuracy is None or accuracy >= .90):return None
    catalog=catalogue()
    chosen=catalog[(batch-1)%len(catalog)]
    seed=910000+batch
    event_id=f'{PROTOCOL}:{batch}'
    trigger='reset' if resets else ('negative_transfer' if gain < 0 else 'low_holdout_accuracy')
    row=(event_id,PROTOCOL,batch,trigger,float(gain),int(resets),accuracy,chosen.id,seed,'PENDING',None,None)
    with closing(_db(path)) as db:
        prev=db.execute('SELECT * FROM event_trials WHERE event_id=?',(event_id,)).fetchone()
        if prev is not None:
            if prev[:9] != row[:9]:raise ValueError('Evidence identity drift for event')
        else:
            with db:db.execute('INSERT INTO event_trials VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',row)
    return event_id

def process_pending(path, *, limit=1):
    if not 1 <= limit <= 16:raise ValueError('invalid bounded limit')
    completed=0;rejected=0
    variants={v.id:v for v in catalogue()}
    with closing(_db(path)) as db:
        pending=db.execute("SELECT event_id,candidate,seed FROM event_trials WHERE status='PENDING' ORDER BY batch LIMIT ?",(limit,)).fetchall()
    for event_id,cid,seed in pending:
        # All training and sealed audit occur outside SQLite write locks.
        result=trial(variants[cid],seed)
        equal=result['baseline_updates']==result['challenger_updates'] and result['baseline_probes']==result['challenger_probes']
        # A positive selection-set result is merely a provisional proposal.
        # Sealed audit results never influence selection or certify a winner.
        result['resource_eligible_updates_probes']=equal
        result['promotion']='LOCKED'
        result['research_only']=True
        result['trigger_is_aggregate_legacy_config_pool']=True
        body=_encode(result);digest=_digest(result)
        with closing(_db(path)) as db:
            with db:
                changed=db.execute("UPDATE event_trials SET status='COMPLETED',payload=?,digest=? WHERE event_id=? AND status='PENDING'",(body,digest,event_id)).rowcount
            completed+=changed
            rejected+=int(not equal) if changed else 0
    return {'completed':completed,'budget_ineligible':rejected,'remaining':status(path)['pending']}

def status(path):
    if not Path(path).exists():return {'protocol':PROTOCOL,'events':0,'completed':0,'pending':0,'resource_ineligible':0,'latest':None,'integrity':'NOT_CREATED','certified':0}
    with closing(sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True,timeout=3)) as db:
        rows=db.execute('SELECT event_id,status,payload,digest FROM event_trials ORDER BY batch').fetchall()
        counts={'COMPLETED':0,'PENDING':0};ineligible=0;latest=None
        for eid,s,body,d in rows:
            if s not in counts:raise ValueError('Invalid trial status')
            counts[s]+=1
            if s=='COMPLETED':
                if _digest(json.loads(body)) != d or _encode(json.loads(body)) != body:raise ValueError(f'Tampered event evidence {eid}')
                obj=json.loads(body)
                ineligible+=int(not obj['resource_eligible_updates_probes'])
                latest={'event':eid,'candidate':obj['ancestor'],'mutation':obj['mutation'],'accepted_selection_only':obj['accepted'],
                        'transfer_pp':round(obj['sealed_transfer_gain']*100,3),'retention_pp':round(obj['sealed_retention_gain']*100,3),
                        'resource_eligible':obj['resource_eligible_updates_probes']}
            elif body is not None or d is not None:raise ValueError('Pending trial cannot contain evidence')
    return {'protocol':PROTOCOL,'events':len(rows),'completed':counts['COMPLETED'],'pending':counts['PENDING'],
            'resource_ineligible':ineligible,'latest':latest,'integrity':'CHECKED','certified':0}
