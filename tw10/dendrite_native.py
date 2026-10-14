"""Persistent D-genotype continual learning, independent of the legacy G-config pool.

Each of 7777 executable programs receives its own checkpoint and shared episode
schedule. Failure may propose a descendant from the *trained* parent's state.
The sealed audit is NEVER used to choose descendants. No Mother certification.
"""
from __future__ import annotations
import copy
import hashlib
import json
import sqlite3
from collections import deque
from contextlib import closing
from pathlib import Path
from .relational_dendrites import RelationalLearner, Variant, catalogue, edges, tasks
from .first_generation import mutate

PROTOCOL='TW56_DENDRITE_NATIVE_V2'
DOMAINS=('linear','context','interaction','relation')

def encode(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def digest(x):return hashlib.sha256(encode(x).encode()).hexdigest()

def export(learner):
    return {'syn':[[a,b,w] for (a,b),w in sorted(learner.syn.items())],
            'readout':list(learner.readout),'error_trace':learner.error_trace,
            'errors':list(learner.errors),'memory':list(learner.memory),
            'experience':learner.experience,'updates':learner.updates,
            'rule_changes':learner.rule_changes,'lr':learner.lr}

def restore(variant,payload):
    m=RelationalLearner(variant)
    state=json.loads(payload) if isinstance(payload,str) else payload
    expected=set(edges(variant.topology))
    syn={(int(a),int(b)):float(w) for a,b,w in state['syn']}
    if set(syn)!=expected or len(syn)!=len(state['syn']):raise ValueError('invalid dendritic topology checkpoint')
    m.syn=syn
    if len(state['readout'])!=8:raise ValueError('invalid readout checkpoint')
    m.readout=list(map(float,state['readout']))
    m.error_trace=float(state['error_trace'])
    m.errors=deque(state['errors'],maxlen=12)
    m.memory=deque([(tuple(x),y,c,err) for x,y,c,err in state['memory']],maxlen=8)
    m.experience=int(state['experience']);m.updates=int(state['updates'])
    m.rule_changes=int(state['rule_changes']);m.lr=float(state['lr'])
    return m

def database(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=30)
    db.execute('PRAGMA busy_timeout=30000')
    db.execute('''CREATE TABLE IF NOT EXISTS learners(
      id TEXT PRIMARY KEY, genotype TEXT NOT NULL, step INTEGER NOT NULL,
      checkpoint TEXT NOT NULL, checkpoint_hash TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS learning(
      id TEXT NOT NULL, step INTEGER NOT NULL, domain TEXT NOT NULL,
      audit_accuracy REAL NOT NULL, old_accuracy REAL NOT NULL,
      error_rate REAL NOT NULL, evidence_hash TEXT NOT NULL,
      PRIMARY KEY(id,step))''')
    db.execute('''CREATE TABLE IF NOT EXISTS offspring(
      parent TEXT NOT NULL, step INTEGER NOT NULL, child_genotype TEXT NOT NULL,
      selection_gain REAL NOT NULL, sealed_gain REAL NOT NULL,
      sealed_retention REAL NOT NULL, adopted INTEGER NOT NULL,
      payload TEXT NOT NULL, evidence_hash TEXT NOT NULL,PRIMARY KEY(parent,step))''')
    db.execute('''CREATE TABLE IF NOT EXISTS descendant_learning (
        child_id TEXT NOT NULL, step INTEGER NOT NULL, domain TEXT NOT NULL,
        checkpoint_hash TEXT NOT NULL, evidence_hash TEXT NOT NULL,
        PRIMARY KEY(child_id,step))''')
    db.execute('CREATE INDEX IF NOT EXISTS native_steps ON learners(step,id)')
    db.execute('''CREATE TABLE IF NOT EXISTS descendant_checkpoints (
        child_id TEXT PRIMARY KEY, parent_id TEXT NOT NULL, birth_step INTEGER NOT NULL,
        genotype TEXT NOT NULL, checkpoint TEXT NOT NULL, checkpoint_hash TEXT NOT NULL, step INTEGER NOT NULL DEFAULT 0)''')
    db.commit();return db

def verify_row(cid,genotype,step,checkpoint,signature,variants):
    v=variants[cid]
    if genotype!=encode(v.genotype()):raise ValueError(f'genotype drift {cid}')
    if digest(json.loads(checkpoint))!=signature:raise ValueError(f'checkpoint tamper {cid}')
    m=restore(v,checkpoint)
    if m.experience!=step*32:raise ValueError(f'step mismatch {cid}')
    return m

def bootstrap(db):
    all_variants=catalogue()
    if len(all_variants)!=7777:raise ValueError('D catalogue incomplete')
    if db.execute('SELECT COUNT(*) FROM learners').fetchone()[0]:
        existing={r[0]:r[1] for r in db.execute('SELECT id,genotype FROM learners')}
        if len(existing)!=7777 or any(existing.get(v.id)!=encode(v.genotype()) for v in all_variants):
            raise ValueError('D population identity drift')
        return
    with db:
        for v in all_variants:
            state=export(RelationalLearner(v))
            db.execute('INSERT INTO learners VALUES (?,?,?,?,?)',
                       (v.id,encode(v.genotype()),0,encode(state),digest(state)))

def progress(db):
    n,trained,steps,min_step,max_step=db.execute('SELECT COUNT(*),SUM(step>0),SUM(step),MIN(step),MAX(step) FROM learners').fetchone()
    offspring=db.execute('SELECT COUNT(*),COALESCE(SUM(adopted),0) FROM offspring').fetchone()
    children=(db.execute('SELECT COUNT(*),COALESCE(SUM(step),0) FROM descendant_checkpoints').fetchone()
              if db.execute("SELECT 1 FROM sqlite_master WHERE name='descendant_checkpoints'").fetchone() else (0,0))
    return {'registered':n,'trained':trained or 0,'learning_steps':steps or 0,'min_step':min_step or 0,
            'max_step':max_step or 0,'offspring_trials':offspring[0],'selection_adoptions':offspring[1],
            'descendant_states':children[0],'descendant_learning_steps':children[1],
            'descendant_evidence_records':(db.execute('SELECT COUNT(*) FROM descendant_learning').fetchone()[0]
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='descendant_learning'").fetchone() else 0),
            'certified':0,'protocol':PROTOCOL}

def verify_all(path):
    """Deep startup/maintenance audit, never called by five-second HTTP polling.

    Verify every genotype/checkpoint and descendant lineage including associated
    proposal evidence. Completeness is a numerical claim, not a certification.
    """
    variants={v.id:v for v in catalogue()}
    with closing(sqlite3.connect(Path(path), timeout=30)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('D native SQLite corruption')
        rows=db.execute('SELECT id,genotype,step,checkpoint,checkpoint_hash FROM learners').fetchall()
        if len(rows)!=7777:raise ValueError('D native initial population incomplete')
        for cid,g,step,cp,signature in rows:
            if cid not in variants:raise ValueError(f'unknown D variant {cid}')
            verify_row(cid,g,step,cp,signature,variants)
        # The entire learning ledger is immutable research evidence. A correct
        # checkpoint alone cannot prove that intervening trials were not edited.
        counts={}
        for cid,step,domain,audit,old,err,signature in db.execute(
                'SELECT id,step,domain,audit_accuracy,old_accuracy,error_rate,evidence_hash FROM learning'):
            record={'id':cid,'step':step,'domain':domain,'audit':audit,'old':old,'error_rate':err}
            if digest(record)!=signature:raise ValueError(f'D learning evidence changed {cid} {step}')
            counts[cid]=counts.get(cid,0)+1
        for cid,_,step,_,_ in rows:
            if counts.get(cid,0)!=step:raise ValueError(f'D learning history incomplete {cid}')
        trials={}
        for parent,step,payload,signature in db.execute('SELECT parent,step,payload,evidence_hash FROM offspring'):
            if parent not in variants:raise ValueError(f'orphan D offspring {parent}')
            obj=json.loads(payload)
            if digest(obj)!=signature:raise ValueError(f'D offspring evidence changed {parent} {step}')
            trials[(parent,step)]=obj
        for cid,parent,birth,genotype,cp,signature,step in db.execute('SELECT child_id,parent_id,birth_step,genotype,checkpoint,checkpoint_hash,step FROM descendant_checkpoints'):
            if cid!=f'{parent}.g{birth}':raise ValueError(f'bad descendant identity {cid}')
            if (parent,birth) not in trials or not trials[(parent,birth)]['adopted']:
                raise ValueError(f'descendant without accepted proposal {cid}')
            if parent not in variants:raise ValueError(f'descendant orphan {cid}')
            if digest(json.loads(cp))!=signature:raise ValueError(f'descendant checkpoint changed {cid}')
            v=Variant(cid,*json.loads(genotype),parent,'descendant')
            restore(v,cp)
            if step<0:raise ValueError(f'negative descendant steps {cid}')
        # Legacy TW53/TW55 descendants have persisted steps without per-step
        # journal records. Do not manufacture retroactive evidence for them.
        # TW56 evidence is verified only for steps explicitly journaled.
        journal_counts={}
        journal_ranges={}
        has_descendant_ledger = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='descendant_learning'").fetchone())
        descendant_records = (db.execute('SELECT child_id,step,domain,checkpoint_hash,evidence_hash FROM descendant_learning')
                              if has_descendant_ledger else ())
        for cid,step,domain,cp_hash,signature in descendant_records:
            record={'child_id':cid,'step':step,'domain':domain,'checkpoint_hash':cp_hash}
            if digest(record)!=signature:raise ValueError(f'descendant training evidence changed {cid} {step}')
            journal_counts[cid]=journal_counts.get(cid,0)+1
            bounds=journal_ranges.setdefault(cid, [step, step, cp_hash])
            if step<bounds[0]:bounds[0]=step
            if step>=bounds[1]:bounds[1]=step;bounds[2]=cp_hash
        for cid,step,current_hash in db.execute('SELECT child_id,step,checkpoint_hash FROM descendant_checkpoints'):
            if cid not in journal_ranges:continue  # pre-TW56 checkpoint
            first,last,last_hash=journal_ranges[cid]
            if first<1 or last!=step or journal_counts[cid] != last-first+1 or last_hash!=current_hash:
                raise ValueError(f'descendant learning ledger incomplete {cid}')
        return {'integrity':'FULL_CHECK_OK','initial_variants':len(rows),
                'offspring_trials':len(trials),'learning_records':sum(counts.values()),
                'descendants':db.execute('SELECT COUNT(*) FROM descendant_checkpoints').fetchone()[0]}

def snapshot(path):
    if not Path(path).exists():return {'registered':0,'trained':0,'status':'NOT_STARTED','certified':0}
    with closing(sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True,timeout=5)) as db:
        return progress(db)

def offspring_trial(parent,variant,step,domain):
    """State-carrying child; selection data and sealed audit are isolated."""
    child_v=mutate(variant,810000+step)
    child=copy.deepcopy(parent); child.v=child_v
    if child_v.topology!=variant.topology:
        previous=child.syn
        child.graph=edges(child_v.topology)
        child.syn={edge:previous.get(edge,.09) for edge in child.graph}
    control=copy.deepcopy(parent)
    # Equal update counts, including memory replay, under fixed replay policy.
    selection_training=tasks(920000+step,domain,32)
    for x,y,c in selection_training:
        child.learn(x,y,c,replay_policy='fixed')
        control.learn(x,y,c,replay_policy='fixed')
    budget_ok=(child.updates==control.updates)
    selection=tasks(930000+step,domain,64)
    gain=child.score(selection)-control.score(selection)
    holdout=tasks(940000+step,'relation',64)
    old=tasks(950000+step,'linear',64)
    sealed_gain=child.score(holdout)-control.score(holdout)
    retention=child.score(old)-control.score(old)
    # Selection gate only, sealed result cannot influence decision.
    accepted=bool(budget_ok and gain>0)
    return {'child':child_v.genotype(),'changed':child_v.changed,'child_state':export(child) if accepted else None,'selection_gain':gain,
            'sealed_gain':sealed_gain,'sealed_retention':retention,'adopted':accepted,
            'updates_equal':budget_ok,'parent_updates':control.updates,'child_updates':child.updates,
            'scope':'SYNTHETIC_EXPLORATION_ONLY','certified':False}

def advance(path,limit=64,offspring_every=4):
    if not 1<=limit<=7777:raise ValueError('invalid batch size')
    variants={v.id:v for v in catalogue()}
    changed=0;mutations=0
    with closing(database(path)) as db:
        bootstrap(db)
        # Least-exposed learners first; no fixed elite shortcut.
        rows=db.execute('SELECT id,genotype,step,checkpoint,checkpoint_hash FROM learners ORDER BY step,id LIMIT ?', (limit,)).fetchall()
        for cid,g,step,cp,sig in rows:
            v=variants[cid];m=verify_row(cid,g,step,cp,sig,variants)
            domain=DOMAINS[step%len(DOMAINS)]
            training=tasks(500000+step,domain,32)
            unseen=tasks(600000+step,domain,64)
            old=tasks(700000+step,'linear',64)
            before=m.score(training)
            for x,y,c in training:m.learn(x,y,c,replay_policy='fixed')
            accuracy=m.score(unseen);retention=m.score(old)
            checkpoint=export(m);h=digest(checkpoint)
            record={'id':cid,'step':step+1,'domain':domain,'audit':accuracy,
                    'old':retention,'error_rate':1-before}
            new_offspring=None
            if offspring_every and (step+1)%offspring_every==0:
                new_offspring=offspring_trial(m,v,step+1,domain)
            with db:
                affected=db.execute('UPDATE learners SET step=?,checkpoint=?,checkpoint_hash=? WHERE id=? AND step=? AND checkpoint_hash=?',
                    (step+1,encode(checkpoint),h,cid,step,sig)).rowcount
                if affected!=1:raise RuntimeError('D state race/corruption')
                db.execute('INSERT INTO learning VALUES (?,?,?,?,?,?,?)',
                    (cid,step+1,domain,accuracy,retention,1-before,digest(record)))
                if new_offspring is not None:
                    if new_offspring['adopted']:
                        child_id=f'{cid}.g{step+1}'
                        child_state=new_offspring['child_state']
                        db.execute('INSERT INTO descendant_checkpoints(child_id,parent_id,birth_step,genotype,checkpoint,checkpoint_hash) VALUES (?,?,?,?,?,?)',
                            (child_id,cid,step+1,encode(new_offspring['child']),encode(child_state),digest(child_state)))
                    db.execute('INSERT INTO offspring VALUES (?,?,?,?,?,?,?,?,?)',
                        (cid,step+1,encode(new_offspring['child']),new_offspring['selection_gain'],
                         new_offspring['sealed_gain'],new_offspring['sealed_retention'],int(new_offspring['adopted']),
                         encode(new_offspring),digest(new_offspring)))
            changed+=1;mutations+=int(new_offspring is not None)
        result=progress(db)
    result.update({'advanced':changed,'new_offspring_trials':mutations})
    return result

def advance_descendants(path,limit=4):
    """Quarantined offspring keep learning under their OWN independent checkpoints.

    Selection-adopted does not mean certified; newborn states inherit the real
    trained parent's synaptic state.  No sealed audit feedback enters lineage selection.
    """
    if not 1<=limit<=128:raise ValueError('invalid descendant budget')
    with closing(database(path)) as db:
        rows=db.execute('SELECT child_id,parent_id,birth_step,genotype,checkpoint,checkpoint_hash,step FROM descendant_checkpoints ORDER BY step,child_id LIMIT ?', (limit,)).fetchall()
        for cid,parent,birth,genotype,cp,signature,step in rows:
            state=json.loads(cp)
            if digest(state)!=signature:raise ValueError('descendant checkpoint tampered')
            ancestor={v.id:v for v in catalogue()}[parent]
            values=json.loads(genotype)
            child_variant=Variant(cid,*values,parent,'descendant')
            m=restore(child_variant,state)
            task=DOMAINS[(birth+step)%len(DOMAINS)]
            for x,y,c in tasks(800000+birth+step,task,32):m.learn(x,y,c,replay_policy='fixed')
            newer=export(m)
            with db:
                count=db.execute('UPDATE descendant_checkpoints SET checkpoint=?,checkpoint_hash=?,step=? WHERE child_id=? AND step=? AND checkpoint_hash=?',
                    (encode(newer),digest(newer),step+1,cid,step,signature)).rowcount
                if count!=1:raise RuntimeError('descendant concurrent update')
                record={'child_id':cid,'step':step+1,'domain':task,'checkpoint_hash':digest(newer)}
                db.execute('INSERT INTO descendant_learning VALUES (?,?,?,?,?)',
                    (cid,step+1,task,digest(newer),digest(record)))
    return {'advanced_descendants':len(rows),'descendant_progress':snapshot(path)['descendant_learning_steps']}
