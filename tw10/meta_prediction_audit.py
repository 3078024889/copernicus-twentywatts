"""TW36: locked, seed-disjoint audit of whether strategy history predicts mutation gains.

Uses TW35 *selection* observations only; sealed audit performance never appears
as model input or target. This is retrospective predictive validation, not a
proof of autonomous improvement and not a Mother certification.
"""
from __future__ import annotations
import json, sqlite3, statistics, math
from pathlib import Path
from collections import defaultdict
from contextlib import closing
from .first_generation import stable_hash
from .relational_dendrites import FIELDS, catalogue, behaviour_fingerprint

PROTOCOL='TW36_HISTORY_PREDICTION_AUDIT_V1'

def read_trials(path, start, stop):
    """Read immutable TW35 evidence and reject any corrupted row."""
    path=Path(path)
    if not path.is_file(): raise FileNotFoundError(path)
    out=[]
    with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True)) as con:
        rows=con.execute('SELECT evidence,evidence_hash FROM strategy_memory_trials WHERE protocol=?',('COPERNICUS_STRATEGY_MEMORY_V1',))
        for evidence,digest in rows:
            obj=json.loads(evidence)
            if stable_hash(obj)!=digest:raise ValueError('History evidence hash does not match')
            if start <= obj['seed'] < stop:
                if obj['sealed_used_for_selection'] is not False:raise ValueError('Sealed data leakage flag')
                out.append(obj)
    return sorted(out,key=lambda r:r['seed'])

def examples(records):
    result=[]
    for r in records:
        for step in r['strategy_memory']:
            if len(step['proposal_gains'])!=len(FIELDS): raise ValueError('Invalid proposal dimensions')
            for field,gain,ok in zip(FIELDS,step['proposal_gains'],step['proposal_comparable']):
                if ok:result.append((r['seed'],step['domain'],field,float(gain)))
    return result

def _fit(rows):
    by_domain=defaultdict(list); by_pair=defaultdict(list); global_values=[]
    for _,domain,field,gain in rows:
        global_values.append(gain);by_domain[domain].append(gain);by_pair[(domain,field)].append(gain)
    g=statistics.fmean(global_values) if global_values else 0.
    return g,{k:statistics.fmean(v) for k,v in by_domain.items()}, {k:(sum(v),len(v)) for k,v in by_pair.items()}

def predict(model,domain,field,prior=8):
    global_mean, domain_mean, pairs=model
    base=domain_mean.get(domain,global_mean)
    total,n=pairs.get((domain,field),(0.,0))
    return (total+prior*base)/(n+prior)

def evaluate(training,testing):
    tr=examples(training);te=examples(testing)
    if not tr or not te:raise ValueError('Insufficient train/holdout history')
    if {x[0] for x in tr}&{x[0] for x in te}:raise ValueError('Seed leakage')
    model=_fit(tr)
    pred=[predict(model,d,f) for _,d,f,_ in te]
    zero=[0.]*len(te)
    domain=[model[1].get(d,model[0]) for _,d,_,_ in te]
    mae=lambda p:statistics.fmean(abs(y-a) for a,(_,_,_,y) in zip(p,te))
    # Entire arm/generation is a decision; count only groups with all 5 eligible.
    # We also keep the exact observed eligible set rather than inferring it.
    decisions=[]
    for record in testing:
        for arm_step in record['strategy_memory']:
            eligible=[j for j,b in enumerate(arm_step['proposal_comparable']) if b]
            if len(eligible)<2:continue
            gains=arm_step['proposal_gains'];domain_key=arm_step['domain']
            pick=max(eligible,key=lambda j:(predict(model,domain_key,FIELDS[j]),-j))
            random_baseline=eligible[0] # predeclared fixed-field baseline, not stochastic.
            oracle=max(gains[j] for j in eligible)
            decisions.append((gains[pick],gains[random_baseline],oracle))
    return {
        'protocol':PROTOCOL,'training_seeds':len(training),'holdout_seeds':len(testing),
        'training_selection_observations':len(tr),'holdout_selection_observations':len(te),
        'training_and_holdout_seed_disjoint':True,
        'mean_absolute_error_meta':round(mae(pred),8),
        'mean_absolute_error_zero':round(mae(zero),8),
        'mean_absolute_error_domain_only':round(mae(domain),8),
        'prediction_skill_vs_domain_only':round(1-mae(pred)/mae(domain),6) if mae(domain)>0 else None,
        'holdout_decisions':len(decisions),
        'mean_selection_gain_meta':round(statistics.fmean(r[0] for r in decisions),8) if decisions else None,
        'mean_selection_gain_fixed_field':round(statistics.fmean(r[1] for r in decisions),8) if decisions else None,
        'mean_best_available_gain_oracle_not_deployable':round(statistics.fmean(r[2] for r in decisions),8) if decisions else None,
        'uses_sealed_audit_for_fit_or_selection':False,
        'certified':False,
        'limitations':'Retrospective synthetic selection scores only; no CPU/RAM parity, no causal attribution or real Mother.'
    }

def full_behaviour_registry():
    """All candidates receive same deterministic behavioral probes; collisions retained."""
    pool=catalogue()
    counts=defaultdict(int)
    for v in pool:counts[behaviour_fingerprint(v)]+=1
    unique=len(counts)
    return {'defined_algorithms':len(pool),'unique_structural_programs':len({v.genotype() for v in pool}),
            'distinct_behaviour_fingerprints':unique,'behaviour_collisions':len(pool)-unique,
            'probe_scope':'Three synthetic task families; same deterministic training and 30 predictions per candidate',
            'certified_independent_algorithms':0}

def run(db,train_start=15500,train_end=15572,test_start=25500,test_end=25572,do_fingerprints=False,report=None):
    a=read_trials(db,train_start,train_end);b=read_trials(db,test_start,test_end)
    result=evaluate(a,b)
    if do_fingerprints:result['full_behaviour_audit']=full_behaviour_registry()
    if report:
        target=Path(report);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result
