"""TW38: precommitted mutation-policy experiment using historical selection only.

Both arms face identical tasks, evaluate the same number of proposals and never
use sealed audits to select mutations. Not evidence of general intelligence.
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
from .first_generation import split_rows, stable_hash
from .strategy_memory import mutations
from .recursive_lineage import DOMAINS, reprogram
from .relational_dendrites import FIELDS, RelationalLearner, catalogue

PROTOCOL='TW40_FIXED_REPLAY_BUDGET_V1'

def learn_priors(history):
    """Only training cohort *selection* gains; no sealed outcomes allowed."""
    sums=defaultdict(list)
    for record in history:
        for step in record['no_history']:
            for j,(gain,ok) in enumerate(zip(step['proposal_gains'],step['proposal_comparable'])):
                if ok:sums[(step['domain'],FIELDS[j])].append(gain)
    return {k:(statistics.fmean(v),len(v)) for k,v in sums.items()}

def policy_choice(domain,priors,seed,arm,eligible=None):
    """Choose only update-budget eligible mutations before reading outcomes.

    Eligibility is determined from training computation, never from selection
    accuracy or sealed audits. Both arms evaluate the same five proposals.
    """
    import random
    eligible=list(range(len(FIELDS))) if eligible is None else list(eligible)
    if not eligible:
        return None
    if arm=='meta':
        vals=[priors.get((domain,FIELDS[j]),(0,0)) for j in range(len(FIELDS))]
        supported=[j for j in eligible if vals[j][1]>=4]
        if supported:
            return max(supported,key=lambda j:(vals[j][0]*vals[j][1]/(vals[j][1]+12),-j))
    rng=random.Random(f'{PROTOCOL}/{seed}/{domain}')
    return rng.choice(eligible)

def step(current,seed,generation,arm,priors):
    domain=DOMAINS[generation%4]
    train=split_rows(seed+170000+generation,domain,'train',48)
    select=split_rows(seed+170000+generation,domain,'selection',64)
    options=mutations(current.v,seed*100+generation)
    unchanged=copy.deepcopy(current)
    challenger=[reprogram(copy.deepcopy(current),v) for v in options]
    for x,y,c in train:
        unchanged.learn(x,y,c,replay_policy="fixed")
        for m in challenger:m.learn(x,y,c,replay_policy="fixed")
    baseline_updates=unchanged.updates-current.updates
    updates=[m.updates-current.updates for m in challenger]
    baseline_score=unchanged.score(select)
    scores=[m.score(select) for m in challenger]
    eligible=[j for j,u in enumerate(updates) if u==baseline_updates]
    proposal=policy_choice(domain,priors,seed*100+generation,arm,eligible)
    comparable=proposal is not None
    gain=scores[proposal]-baseline_score if comparable else 0.0
    accepted=comparable and gain>0
    resulting=challenger[proposal] if accepted else unchanged
    return resulting,{'domain':domain,'selected_field':FIELDS[proposal] if proposal is not None else None,
        'selection_gain':round(gain,8),'accepted':accepted,'eligible_fields':[FIELDS[j] for j in eligible], 'updates_per_proposal':updates,
        'baseline_updates':baseline_updates,'budget_comparable':comparable,
        'prediction_calls':(len(challenger)+1)*len(select),
        'selection_dataset_rows':len(select), 'replay_policy':'fixed', 'replay_updates':baseline_updates-len(train)}

def experiment(v,seed,priors,generations=4):
    if not 2<=generations<=12:raise ValueError('generations out of range')
    arms={name:RelationalLearner(v) for name in ('random','meta')}
    traces={name:[] for name in arms}
    for g in range(generations):
        for name in arms:
            arms[name],event=step(arms[name],seed,g,name,priors)
            traces[name].append(event)
    # Sealed audit is generated only after every mutation decision.
    audits={}
    for d in DOMAINS:
        data=split_rows(seed+240000,d,'sealed_audit',192)
        audits[d]={name:round(m.score(data),8) for name,m in arms.items()}
    budget_match=all(traces['random'][i]['prediction_calls']==traces['meta'][i]['prediction_calls'] for i in range(generations))
    all_comparable=all(e['budget_comparable'] for track in traces.values() for e in track)
    counts=[sum(e['baseline_updates']+sum(e['updates_per_proposal']) for e in traces[name]) for name in arms]
    out={'protocol':PROTOCOL,'seed':seed,'ancestor':v.id,'generations':generations,
         'traces':traces,'audits':audits,'probe_budget_equal':budget_match,
         'candidate_update_budget_equal':counts[0]==counts[1], 'replay_budget_policy':'FIXED_EVERY_FIVE_NEW_EXPERIENCES',
         'all_selected_proposals_comparable':all_comparable,
         'compute_updates':dict(zip(arms,counts)),
         'sealed_used_for_selection':False,'certified':False,
         'mother':'NOT_REAL_V3_MOTHER','scope':'SYNTHETIC_PROSPECTIVE_MUTATION_POLICY'}
    out['evidence_hash']=stable_hash(out)
    return out

def _bootstrap_ci(values,bootstraps=600):
    import random
    if not values:return None
    rng=random.Random(5137)
    means=sorted(statistics.fmean(rng.choices(values,k=len(values))) for _ in range(bootstraps))
    return [round(100*means[int(bootstraps*.025)],5),round(100*means[int(bootstraps*.975)-1],5)]

def run(source_db,output_db,count=24,seed=33000,generations=4):
    from .meta_prediction_audit import read_trials
    if not 1<=count<=7777:raise ValueError('invalid count')
    # Training cohort: historical selection feedback only, disjoint future seed range.
    train=read_trials(source_db,15500,15572)
    priors=learn_priors(train)
    pool=catalogue()
    db=Path(output_db);db.parent.mkdir(parents=True,exist_ok=True)
    historical_seeds={r['seed'] for r in train}
    rows=[];new=0
    with closing(sqlite3.connect(db,timeout=30)) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS prospective_trials (trial_key TEXT PRIMARY KEY, evidence TEXT NOT NULL, digest TEXT NOT NULL)')
        for i in range(count):
            v=pool[(i*7777)//count];s=seed+i
            if s in historical_seeds:raise ValueError('history/future seed overlap')
            key=stable_hash((PROTOCOL,v.id,s,generations,stable_hash(sorted([(str(k),val) for k,val in priors.items()]))))
            existing=conn.execute('SELECT evidence,digest FROM prospective_trials WHERE trial_key=?',(key,)).fetchone()
            if existing:
                r=json.loads(existing[0])
                if (stable_hash({k:v for k,v in r.items() if k!='evidence_hash'})!=existing[1]
                    or r.get('evidence_hash')!=existing[1]):
                    raise ValueError('corrupt persisted evidence')
            else:
                r=experiment(v,s,priors,generations)
                digest=stable_hash({k:v for k,v in r.items() if k!='evidence_hash'})
                conn.execute('INSERT INTO prospective_trials VALUES (?,?,?)',(key,json.dumps(r,sort_keys=True),digest));conn.commit();new+=1
            rows.append(r)
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
    eligible=[r for r in rows if r['probe_budget_equal'] and r['candidate_update_budget_equal'] and r['all_selected_proposals_comparable']]
    delta={d:[r['audits'][d]['meta']-r['audits'][d]['random'] for r in eligible] for d in DOMAINS}
    return {'protocol':PROTOCOL,'trials':len(rows),'new_trials':new,'eligible':len(eligible),
            'budget_rejected':len(rows)-len(eligible), 'replay_budget_policy':'FIXED_EVERY_FIVE_NEW_EXPERIENCES','history_trials':len(train),
            'history_selection_only':True,'prospective_seeds':[seed,seed+count-1],
            'mean_transfer_delta_pp':round(100*statistics.fmean(delta['relation']),5) if eligible else None,
            'transfer_bootstrap_95_pp':_bootstrap_ci(delta['relation']),
            'mean_retention_delta_pp':round(100*statistics.fmean(delta['linear']),5) if eligible else None,
            'retention_bootstrap_95_pp':_bootstrap_ci(delta['linear']),
            'sqlite_integrity':integrity,'certified_ais':0,
            'limitations':'Synthetic tasks; selectable candidates prefiltered by update budget; historical selection priors; matched operations not CPU/RAM; no real Mother.'}
