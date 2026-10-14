"""TW35: a falsifiable, selection-only strategy-memory twin experiment.

Memory learns *which operator family to mutate*, based solely on earlier
selection outcomes. Both arms execute the same number of proposals, learning
updates and selection probes. Neither accesses sealed audit during selection.
This is an exploratory synthetic protocol, NOT a real Mother comparison.
"""
from __future__ import annotations
import copy
import json
import math
import sqlite3
import statistics
import time
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from dataclasses import replace
from .first_generation import split_rows, stable_hash
from .recursive_lineage import reprogram, DOMAINS
from .relational_dendrites import AXES, FIELDS, RelationalLearner, catalogue

PROTOCOL = 'COPERNICUS_STRATEGY_MEMORY_V1'


def mutations(v, seed):
    """Exactly one deterministic executable-operator mutation per field."""
    import random
    out=[]
    for i, field in enumerate(FIELDS):
        options = [x for x in AXES[i] if x != getattr(v,field)]
        rng=random.Random(f'{PROTOCOL}/{seed}/{v.id}/{field}')
        next_op = rng.choice(options)
        out.append(replace(v,id=f'{v.id}.{field}.{seed}',parent=v.id,
                           changed=field,**{field:next_op}))
    return out


def choose(gains, memory, domain, use_history):
    """Reward observed gain; only history arm gets a past-domain prior."""
    if not use_history:
        return max(range(len(gains)), key=lambda j: (gains[j],-j))
    # Damped prior, uses *only prior selection scores* for matching domain.
    values=[]
    for j,gain in enumerate(gains):
        past=memory.get((domain,FIELDS[j]),())
        prior=statistics.fmean(past) if past else 0.
        values.append(gain + .35*min(1,len(past)/2)*prior)
    return max(range(len(values)),key=lambda j:(values[j],-j))


def _arm_step(current, domain, generation, seed, history, use_history):
    training=split_rows(seed+130000+generation,domain,'train',48)
    selection=split_rows(seed+130000+generation,domain,'selection',64)
    proposals=mutations(current.v,seed*100+generation)
    unchanged=copy.deepcopy(current)
    for x,y,c in training: unchanged.learn(x,y,c)
    candidates=[]; gains=[]; update_counts=[]
    for proposal in proposals:
        child=reprogram(copy.deepcopy(current),proposal)
        for x,y,c in training:child.learn(x,y,c)
        candidates.append(child)
        update_counts.append(child.updates-current.updates)
    base_score=unchanged.score(selection)
    scores=[m.score(selection) for m in candidates]
    gains=[s-base_score for s in scores]
    # All five proposals MUST match the unchanged learner's actual update budget.
    comparable=[u==(unchanged.updates-current.updates) for u in update_counts]
    eligible=[j for j,ok in enumerate(comparable) if ok]
    if eligible:
        selected=choose([gains[j] if j in eligible else -1e6 for j in range(5)],
                        history,domain,use_history)
        accepted=gains[selected] > 0
    else:
        selected=None;accepted=False
    next_state=candidates[selected] if accepted else unchanged
    # Update the memory AFTER choosing. Include all proposal feedback including
    # rejected proposals; the memory never has access to the sealed audit.
    for j in range(5):
        if comparable[j]:history[(domain,FIELDS[j])].append(gains[j])
    return next_state, {
        'generation':generation+1,'domain':domain,'baseline_score':round(base_score,8),
        'proposal_gains':[round(g,8) for g in gains],
        'proposal_comparable':comparable,'selected_field':FIELDS[selected] if selected is not None else None,
        'accepted':accepted,'state_hash':stable_hash(next_state.state()),
        'selection_probes':6*len(selection),
        'training_updates_per_proposal':update_counts,
        'baseline_training_updates':unchanged.updates-current.updates,
    }


def experiment(ancestor,seed,generations=8):
    if not 2 <= generations <= 16:raise ValueError('generations must be 2..16')
    if not isinstance(seed,int):raise ValueError('seed must be integer')
    fixed=RelationalLearner(ancestor)
    control=copy.deepcopy(fixed)
    adaptive=copy.deepcopy(fixed)
    histories=[defaultdict(list),defaultdict(list)]
    tracks=[[],[]]
    cpu=time.process_time_ns()
    for g in range(generations):
        domain=DOMAINS[g%len(DOMAINS)]
        control,row_c=_arm_step(control,domain,g,seed,histories[0],False)
        adaptive,row_m=_arm_step(adaptive,domain,g,seed,histories[1],True)
        tracks[0].append(row_c);tracks[1].append(row_m)
        # The baseline fixed learner has identical training exposures.
        training=split_rows(seed+130000+g,domain,'train',48)
        for x,y,c in training:fixed.learn(x,y,c)
    audits={}
    for domain in DOMAINS:
        rows=split_rows(seed+210000,domain,'sealed_audit',192)
        audits[domain]={
            'fixed':round(fixed.score(rows),8),'no_history':round(control.score(rows),8),
            'strategy_memory':round(adaptive.score(rows),8),
        }
    equal_probes=all(x['selection_probes']==y['selection_probes'] for x,y in zip(*tracks))
    equal_search_updates=all(x['training_updates_per_proposal']==y['training_updates_per_proposal']
                             and x['baseline_training_updates']==y['baseline_training_updates']
                             for x,y in zip(*tracks))
    out={
        'protocol':PROTOCOL,'seed':seed,'ancestor':ancestor.id,'generations':generations,
        'no_history':tracks[0],'strategy_memory':tracks[1], 'audits':audits,
        'equal_probes':equal_probes,'equal_candidate_training_updates':equal_search_updates,
        'survivor_updates':[control.updates,adaptive.updates],
        'strategy_memory_records':sum(map(len,histories[1].values())),
        'sealed_used_for_selection':False,
        'mother':'FIXED_PROXY_NOT_V3_MOTHER', 'certified':False,
        'limitations':'Same proposal count and prediction count; not equal CPU/RAM, no real Mother; synthetic tasks.'
    }
    out['evidence_hash']=stable_hash(out)
    out['cpu_process_ns_observed']=time.process_time_ns()-cpu
    return out


def run(db,count=24,seed=15000,generations=8):
    if not 1<=count<=7777:raise ValueError('count must be 1..7777')
    db=Path(db);db.parent.mkdir(parents=True,exist_ok=True)
    pool=catalogue();records=[];new=0
    with closing(sqlite3.connect(db,timeout=30)) as conn:
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('CREATE TABLE IF NOT EXISTS strategy_memory_trials (trial_key TEXT PRIMARY KEY, protocol TEXT NOT NULL, evidence TEXT NOT NULL, evidence_hash TEXT NOT NULL)')
        for i in range(count):
            ancestor=pool[(i*7777)//count];s=seed+i
            key=stable_hash((PROTOCOL,ancestor.id,s,generations))
            row=conn.execute('SELECT evidence,evidence_hash FROM strategy_memory_trials WHERE trial_key=?',(key,)).fetchone()
            if row:
                payload=json.loads(row[0]);
                if stable_hash(payload)!=row[1]:raise ValueError('Stored experiment tampered')
            else:
                payload=experiment(ancestor,s,generations)
                payload.pop('cpu_process_ns_observed',None)
                digest=payload.pop('evidence_hash')
                if stable_hash(payload)!=digest:raise ValueError('Evidence hash mismatch')
                conn.execute('INSERT INTO strategy_memory_trials VALUES (?,?,?,?)',(key,PROTOCOL,json.dumps(payload,sort_keys=True,separators=(',',':')),digest))
                conn.commit();new+=1
            records.append(payload)
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        total=conn.execute('SELECT COUNT(*) FROM strategy_memory_trials WHERE protocol=?',(PROTOCOL,)).fetchone()[0]
    eligible=[r for r in records if r['equal_probes'] and r['equal_candidate_training_updates']]
    def avg(domain,field):
        if not eligible:return None
        return round(100*statistics.fmean(r['audits'][domain]['strategy_memory']-r['audits'][domain][field] for r in eligible),5)
    return {
        'protocol':PROTOCOL,'trials':len(records),'new_trials':new,'persisted_trials':total,
        'generations':generations,'eligible_trials':len(eligible),
        'rejected_trials':len(records)-len(eligible),
        'mean_transfer_memory_minus_no_history_pp':avg('relation','no_history'),
        'mean_retention_memory_minus_no_history_pp':avg('linear','no_history'),
        'mean_transfer_memory_minus_fixed_pp':avg('relation','fixed'),
        'accepted_memory_mutations':sum(sum(step['accepted'] for step in r['strategy_memory']) for r in records),
        'sqlite_integrity':integrity,'certified_ais':0,
        'scope':'SYNTHETIC_SELECTION_HISTORY_ABLATION_NOT_REAL_MOTHER',
        'limitations':'Probe/update counts matched across search arms, but CPU/RAM not matched.'
    }
