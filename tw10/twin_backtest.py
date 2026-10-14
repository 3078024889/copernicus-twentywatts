"""Reproducible paired backtest of alternative meta-rule selection policies.

Audit samples remain sealed from selection. This routine reports negative findings
rather than conferring any promotion or Mother certification.
"""
from __future__ import annotations
import json
import random
import statistics
from pathlib import Path
from .twin_evolution import study

def bootstrap_interval(values, replicates=4000, seed=20261012):
    if len(values) < 2:
        raise ValueError('at least two independent seeds required')
    rng = random.Random(seed)
    n=len(values)
    samples=sorted(statistics.fmean(values[rng.randrange(n)] for _ in range(n)) for _ in range(replicates))
    return [round(samples[int(.025*replicates)],6),round(samples[int(.975*replicates)],6)]

def run(seeds=range(48), generations=4, proposals=3, db=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)):
        raise ValueError('require >=2 independent unique seeds')
    current=study(ids,generations,proposals,db=db,selection_policy='current')
    cross=study(ids,generations,proposals,db=db,selection_policy='cross_domain')
    by_seed={x['seed']:x for x in current['details']}
    diffs_t=[];diffs_r=[];paired=[]
    for y in cross['details']:
        x=by_seed[y['seed']]
        old=x['generations'][-1]; new=y['generations'][-1]
        dt=new['sealed_transfer_delta']-old['sealed_transfer_delta']
        dr=new['sealed_retention_delta']-old['sealed_retention_delta']
        diffs_t.append(dt);diffs_r.append(dr)
        paired.append({'seed':y['seed'],'transfer_delta_cross_minus_current':round(dt,6),
                       'retention_delta_cross_minus_current':round(dr,6)})
    ci_t=bootstrap_interval(diffs_t,seed=101)
    ci_r=bootstrap_interval(diffs_r,seed=102)
    # Policies use different numbers of selection predictions; do not claim
    # cross-policy equal compute despite paired training streams.
    return {'protocol':'TW26_PAIRED_META_POLICY_BACKTEST_V1', 'seed_count':len(ids),
            'generations':generations,'same_task_rows':True,
            'within_policy_matched_training_and_probe_counts':bool(current['equal_update_counts'] and cross['equal_update_counts'] and current['equal_prediction_counts'] and cross['equal_prediction_counts']),
            'cross_policy_equal_selection_compute':False,
            'current_transfer_mean':current['final_transfer_delta'],
            'cross_transfer_mean':cross['final_transfer_delta'],
            'current_retention_mean':current['final_retention_delta'],
            'cross_retention_mean':cross['final_retention_delta'],
            'transfer_difference_mean':round(statistics.fmean(diffs_t),6),
            'retention_difference_mean':round(statistics.fmean(diffs_r),6),
            'transfer_difference_bootstrap_95':ci_t,
            'retention_difference_bootstrap_95':ci_r,
            'cross_policy_promotion':'REJECTED_NOT_PROVEN',
            'mother':'FROZEN_EXPERIMENTAL_PROXY_NOT_V3_MOTHER',
            'certified_ais':0,'scope':'SYNTHETIC_RESEARCH_ONLY',
            'paired':paired}

def save(path, report):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    temp.replace(path)
