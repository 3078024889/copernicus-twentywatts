"""TW29: local edge counterfactuals at the exact moment of a prediction error.

Ablates one synaptic edge at a time on an already learned, frozen state.
These are *sensitivity* probes, not causal identification or a learning benefit.
No sealed test labels are consulted when choosing which edge to probe.
"""
from __future__ import annotations
import copy
import hashlib
import json
import statistics
from pathlib import Path
from .intervention_lab import PARENT
from .relational_dendrites import RelationalLearner
from .twin_evolution import rows_for
from .twin_backtest import bootstrap_interval, save

PROTOCOL='TW29_EVENT_LOCAL_EDGE_COUNTERFACTUAL_V1'

def trial(seed:int, *, training_count:int=40, audit_count:int=80):
    if not isinstance(seed,int) or not (0<=seed<2**31) or min(training_count,audit_count)<8:
        raise ValueError('invalid experiment seed or sample counts')
    learner=RelationalLearner(PARENT)
    for phase,kind in enumerate(('linear','context','interaction','relation')):
        for x,y,c in rows_for(seed,phase,kind,'train',training_count):
            learner.learn(x,y,c)
    frozen_hash=hashlib.sha256(json.dumps(learner.state(),sort_keys=True).encode()).hexdigest()
    # The diagnostic event is observed ONCE, before opening sealed audit rows.
    x,y,c=rows_for(seed,82,'relation','diagnosis',8)[0]
    reference=learner.predict(x,c)
    error=abs(y-reference)
    edge_effects=[]
    for edge in learner.graph:
        ablated=copy.deepcopy(learner)
        ablated.syn[edge]=0.0
        p=ablated.predict(x,c)
        edge_effects.append({'edge':list(edge),'signed_probability_effect':round(reference-p,9),
                             'abs_probability_effect':round(abs(reference-p),9),
                             'diagnostic_loss_delta':round(abs(y-p)-error,9)})
    # Ranking is based ONLY on a diagnosis row, not audit samples.
    ranked=sorted(edge_effects,key=lambda e:(-e['abs_probability_effect'],e['edge']))
    chosen=tuple(ranked[0]['edge'])
    control=copy.deepcopy(learner)
    disabled=copy.deepcopy(learner)
    disabled.syn[chosen]=0.0
    audits={}
    for phase,kind in enumerate(('linear','context','interaction','relation')):
        audit=rows_for(seed,phase,kind,'sealed_transfer',audit_count)
        ca=control.score(audit)
        da=disabled.score(audit)
        audits[kind]={'control_accuracy':round(ca,8),'edge_disabled_accuracy':round(da,8),
                      'delta':round(da-ca,8)}
    # No training after intervention, so matched sample/update/prediction budget.
    return {'protocol':PROTOCOL,'seed':seed,'frozen_state_sha256':frozen_hash,
            'diagnostic_error':round(error,9),'edge_count':len(edge_effects),
            'chosen_edge':list(chosen),'edge_effects':edge_effects,'sealed_audit':audits,
            'same_training_and_frozen_state':True,'audit_unused_for_edge_choice':True,
            'no_post_intervention_training':True,'mother':'SYNTHETIC_PROXY_NOT_V3_MOTHER',
            'certified_ais':0}

def run(seeds=range(32), *, report=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)) or any(not isinstance(i,int) for i in ids):
        raise ValueError('requires at least two unique integer seeds')
    records=[trial(s) for s in ids]
    domains=('linear','context','interaction','relation')
    summaries={}
    for kind in domains:
        ds=[r['sealed_audit'][kind]['delta'] for r in records]
        summaries[kind]={'mean_delta':round(statistics.fmean(ds),7),
                         'bootstrap_95':bootstrap_interval(ds,replicates=1000,seed=2900+domains.index(kind)),
                         'improved':sum(d>0 for d in ds),'degraded':sum(d<0 for d in ds)}
    payload={'protocol':PROTOCOL,'seed_count':len(ids),'frozen_state_edge_ablation':True,
             'results':summaries,'records':records,'certified_ais':0,
             'limitation':'Single-edge local sensitivity; no causal error origin, no learning-rule improvement, no real Mother.'}
    if report is not None:save(Path(report),payload)
    return payload
