"""TW45: registered cross-generation routing-memory ablation (synthetic).

Two policies get identical learner starting states, training streams, capacity,
calibration budgets and learning updates. Only the acceptance rule differs:
reset chooses this generation's best calibration gate; inherited conservatively
retains the previous gate if within a pre-registered tolerance of the new best.
Sealed audit data are never used to select a gate.
"""
from __future__ import annotations
import copy, hashlib, json, statistics, time
from .adaptive_routing import LearnedRoute, POLICIES
from .cooperative_branches import rank_conflicts, DOMAINS
from .first_generation import split_rows
from .relational_dendrites import RelationalLearner, catalogue
from .prospective_evolution import _bootstrap_ci

PROTOCOL='TW45_INHERITED_ROUTING_V2'
TOLERANCE=0.015

def run_seed(seed:int, generations:int=3, max_edges:int=3, profile:bool=False):
    if not 2 <= generations <= 8: raise ValueError('generations must be 2..8')
    parent=RelationalLearner(catalogue()[120])
    for x,y,c in split_rows(seed+100000,'linear','tw45_warm',32):
        parent.learn(x,y,c,replay_policy='fixed')
    diagnostic=split_rows(seed+110000,'context','tw45_diagnostic',96)
    ranked=rank_conflicts(parent,diagnostic,max_edges)
    if not ranked:return {'protocol':PROTOCOL,'seed':seed,'comparable':False,'reason':'NO_CONFLICT'}
    edges=[edge for _,edge in ranked]
    arms={'reset':copy.deepcopy(parent),'inherit':copy.deepcopy(parent)}
    last_policy={'reset':None,'inherit':None}
    history=[]
    arm_cpu={"reset":0.0,"inherit":0.0}
    for gen in range(generations):
        training=(split_rows(seed+200000+gen*1000,'context','tw45_train',48)
                +split_rows(seed+201000+gen*1000,'relation','tw45_train',48))
        calibration=(split_rows(seed+300000+gen*1000,'context','tw45_calibration',48)
                   +split_rows(seed+301000+gen*1000,'relation','tw45_calibration',48))
        next_arms={}
        generation_row={'generation':gen+1,'policies':{},'selection_probes':{},'updates':{}}
        for arm_name,parent_state in arms.items():
            cpu_start=time.process_time()
            candidates={p:LearnedRoute(parent_state,edges,p) for p in POLICIES}
            # Preserve both learned dendritic branch weights across generations.
            # The base syn values are a temporary routing view, not the actual
            # weights of both branches. Reconstructing only from syn loses memory.
            if isinstance(parent_state,LearnedRoute):
                for learner in candidates.values():
                    learner.branch_weights=copy.deepcopy(parent_state.branch_weights)
            for x,y,c in training:
                for learner in candidates.values():learner.learn(x,y,c,replay_policy='fixed')
            scores={p:candidates[p].score(calibration) for p in POLICIES}
            best=max(POLICIES,key=lambda p:(scores[p],-POLICIES.index(p)))
            chosen=best
            prior=last_policy[arm_name]
            if arm_name=='inherit' and prior is not None and scores[prior]>=scores[best]-TOLERANCE:
                chosen=prior
            next_arms[arm_name]=candidates[chosen]
            last_policy[arm_name]=chosen
            generation_row['policies'][arm_name]=chosen
            generation_row['selection_probes'][arm_name]=len(POLICIES)*len(calibration)
            generation_row['updates'][arm_name]=next_arms[arm_name].updates
            arm_cpu[arm_name]+=time.process_time()-cpu_start
        history.append(generation_row)
        arms=next_arms
    sealed={domain:split_rows(seed+400000,domain,'tw45_sealed',192) for domain in DOMAINS}
    audits={}
    for d,rows in sealed.items():
        audits[d]={}
        for name,model in arms.items():
            cpu_start=time.process_time()
            audits[d][name]=model.score(rows)
            arm_cpu[name]+=time.process_time()-cpu_start
    equal_updates=all(r['updates']['reset']==r['updates']['inherit'] for r in history)
    equal_probes=all(r['selection_probes']['reset']==r['selection_probes']['inherit'] for r in history)
    resource_extra=({'arm_process_cpu_seconds':{k:round(v,6) for k,v in arm_cpu.items()},
                     'cpu_ratio_inherit_to_reset':round(arm_cpu['inherit']/max(arm_cpu['reset'],1e-9),6)} if profile else {})
    return {'protocol':PROTOCOL,'seed':seed,'generations':generations,'variant':'D0121',
            'edges':[list(e) for e in edges], 'history':history,'audits':audits,
            'equal_updates':equal_updates,'equal_selection_probes':equal_probes,
            **resource_extra,
            'comparable':equal_updates and equal_probes,'sealed_used_for_selection':False,
            'certified':False,'mother':'PROXY_NOT_REAL_MOTHER',
            'limitation':'Equal update and probe counts, not equal CPU time or energy; synthetic tasks; one candidate genotype.'}

def evaluate(seeds:int=24,first_seed:int=120000,generations:int=3):
    if not 2<=seeds<=512:raise ValueError('seeds must be 2..512')
    records=[run_seed(first_seed+i,generations) for i in range(seeds)]
    valid=[r for r in records if r['comparable']]
    results={}
    for domain in DOMAINS:
        delta=[100*(r['audits'][domain]['inherit']-r['audits'][domain]['reset']) for r in valid]
        results[domain]={'inherit_vs_reset_pp':round(statistics.fmean(delta),5) if delta else None,
                         'ci95_pp':_bootstrap_ci([v/100 for v in delta]) if delta else None}
    changed=sum(any(h['policies']['reset']!=h['policies']['inherit'] for h in r['history']) for r in valid)
    payload={'protocol':PROTOCOL,'seeds':seeds,'valid':len(valid),'generations':generations,
             'policy_divergent_seeds':changed,'results':results,'certified_ais':0,
             'limitations':'Synthetic tasks; one genotype; proxy Mother; equal updates/probes only, not compute or memory; no twelve-seat certification.'}
    payload['evidence_sha256']=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()
    return payload
