"""Pre-registered mechanism ablations on matched streams, with sealed audit.

Mechanism ablations show sensitivity to components; they do NOT identify the
real-world causal source of an error. The Mother is a synthetic proxy.
"""
from __future__ import annotations
import copy
import hashlib
import json
import statistics
from pathlib import Path
from dataclasses import replace
from .relational_dendrites import RelationalLearner, Variant
from .twin_evolution import rows_for, evaluation_count
from .twin_backtest import bootstrap_interval, save

PROTOCOL = 'TW28_PREDECLARED_MECHANISM_ABLATION_V1'
PARENT = Variant('CAUSAL_ROOT', 'ring', 'context', 'three_factor', 'associative', 'forgetting', None, 'root')
# One factor only, immutable predeclared alternatives -- no search on sealed data.
INTERVENTIONS = {
    'disable_replay': {'memory':'none'},
    'fixed_plasticity': {'plasticity':'local_error'},
    'linear_branches': {'branch':'linear'},
    'fixed_meta_rule': {'meta':'fixed'},
    'chain_connections': {'topology':'chain'},
}
DOMAINS=('linear','context','interaction','relation')


def aligned_state(model, intervention, seed):
    """Copy the learned state; modify exactly one mechanism at the boundary.

    Topology intervention preserves common edge weights, initializes new edges
    explicitly, and records that structural surgery changes representational
    capacity as well as update behaviour.
    """
    from .relational_dendrites import edges
    altered=copy.deepcopy(model)
    altered.v=replace(model.v, id=f'{model.v.id}/{intervention}',
                      **INTERVENTIONS[intervention])
    if 'topology' in INTERVENTIONS[intervention]:
        altered.graph=edges(altered.v.topology)
        altered.syn={edge:model.syn.get(edge,0.09) for edge in altered.graph}
    if intervention=='disable_replay':
        altered.memory.clear()
    return altered


def trial(seed, count=36, audit_count=80):
    if not isinstance(seed,int) or seed<0 or seed>2**31-1 or min(count,audit_count)<8:
        raise ValueError('invalid seed or dataset size')
    parent=RelationalLearner(PARENT)
    for generation,kind in enumerate(DOMAINS):
        for x,y,c in rows_for(seed,generation,kind,'train',count):
            parent.learn(x,y,c)
    digest=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    # Audit task families are sealed. Run a fresh common stream AFTER every
    # intervention; otherwise replay/plasticity/meta edits would be invisible.
    followup=rows_for(seed,99,'relation','train',count)
    control=copy.deepcopy(parent)
    for x,y,c in followup: control.learn(x,y,c)
    results={}
    for name in INTERVENTIONS:
        changed=aligned_state(parent,name,seed)
        for x,y,c in followup: changed.learn(x,y,c)
        scores=[];baseline=[];costs=[]
        for generation,kind in enumerate(DOMAINS):
            holdout=rows_for(seed,generation,kind,'sealed_transfer',audit_count)
            a,n=evaluation_count(changed,holdout)
            b,_=evaluation_count(control,holdout)
            scores.append(a);baseline.append(b)
            costs.append(n)
        results[name]={'domain_deltas':dict(zip(DOMAINS,[round(a-b,8) for a,b in zip(scores,baseline)])),
                       'mean_delta':round(statistics.fmean(a-b for a,b in zip(scores,baseline)),8),
                       'audit_predictions_per_arm':sum(costs),
                       'learned_state_reset':False,
                       'control_updates':control.updates,'intervention_updates':changed.updates,
                       'same_new_samples':True,
                       'mechanism_changed':dict(INTERVENTIONS[name])}
    return {'protocol':PROTOCOL,'seed':seed,'parent_state_sha256':digest,
            'interventions':results,'sealed_audit_not_used_for_selection':True,
            'mother':'SYNTHETIC_PROXY_NOT_REAL_V3_MOTHER',
            'causal_scope':'MECHANISM_SENSITIVITY_NOT_ERROR_CAUSAL_IDENTIFICATION',
            'certified_ais':0}


def run(seeds=range(24),count=36,audit_count=80,report=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)):
        raise ValueError('need distinct paired seeds')
    records=[trial(int(s),count,audit_count) for s in ids]
    summary={}
    for name in INTERVENTIONS:
        deltas=[r['interventions'][name]['mean_delta'] for r in records]
        summary[name]={'mean_delta':round(statistics.fmean(deltas),6),
                       'bootstrap_95':bootstrap_interval(deltas,replicates=1200,seed=2800+list(INTERVENTIONS).index(name)),
                       'positive_seeds':sum(x>0 for x in deltas),
                       'negative_seeds':sum(x<0 for x in deltas)}
    payload={'protocol':PROTOCOL,'seeds':len(ids),'same_train_and_sealed_rows':True,
             'mutations_selected_using_sealed_data':False,
             'equal_compute_costs':False,
             'limitation':'Replay can change total update counts; this is mechanism sensitivity, not same-budget superiority.',
             'ablation_effects':summary,'records':records,
             'promotion':'BLOCKED_REQUIRES_REAL_MOTHER_AND_INDEPENDENT_TASKS',
             'certified_ais':0}
    if report is not None:save(Path(report),payload)
    return payload
