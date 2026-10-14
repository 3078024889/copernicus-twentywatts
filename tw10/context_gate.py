"""TW30: context-conditional synaptic gating, tested on never-selected audits.

A single edge is selected using a diagnostic event. Gate values are learned
only on an independent selection split, conditioned on input context. Sealed
challenge labels are not used for edge/gate selection. Research, not causal proof.
"""
from __future__ import annotations
import copy, hashlib, json, statistics
from pathlib import Path
from .relational_dendrites import RelationalLearner
from .intervention_lab import PARENT
from .twin_evolution import rows_for
from .twin_backtest import bootstrap_interval,save

PROTOCOL='TW30_CONTEXTUAL_SYNAPTIC_GATE_V1'
DOMAINS=('linear','context','interaction','relation')

class GatedLearner:
    """Inference-only mask; no global mutation of the learned parent."""
    def __init__(self,model,edge,gates):
        self.model=model
        self.edge=tuple(edge)
        self.gates=tuple(gates)
        if len(self.gates)!=2 or any(g not in (0.,.5,1.) for g in self.gates):
            raise ValueError('only preregistered gate levels allowed')
        if self.edge not in model.syn:raise ValueError('edge absent from learned model')
    def predict(self,x,context=0):
        original=self.model.syn[self.edge]
        self.model.syn[self.edge]=original*self.gates[int(bool(context))]
        try:return self.model.predict(x,context)
        finally:self.model.syn[self.edge]=original
    def score(self,rows):
        return sum((self.predict(x,c)>=.5)==y for x,y,c in rows)/len(rows)

def trial(seed,training_count=40,selection_count=60,audit_count=80):
    if not isinstance(seed,int) or not 0<=seed<2**31 or min(training_count,selection_count,audit_count)<8:
        raise ValueError('invalid experiment inputs')
    parent=RelationalLearner(PARENT)
    for i,kind in enumerate(DOMAINS):
        for x,y,c in rows_for(seed,i,kind,'train',training_count):parent.learn(x,y,c)
    before=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    dx,dy,dc=rows_for(seed,82,'relation','diagnosis',8)[0]
    p=parent.predict(dx,dc)
    # Selection on diagnostic probability impact, not on sealed accuracy.
    impacts=[]
    for edge in parent.graph:
        check=GatedLearner(parent,edge,(0.,0.))
        impacts.append((abs(p-check.predict(dx,dc)),edge))
    edge=sorted(impacts,key=lambda a:(-a[0],a[1]))[0][1]
    # Identical selection data and context-specific optima; ties prefer 1 (no edit).
    selection=[row for i,kind in enumerate(DOMAINS)
               for row in rows_for(seed,i,kind,'gate_selection',selection_count)]
    choices=(1.,.5,0.)
    gate=[]
    for ctx in (0,1):
        subset=[row for row in selection if row[2]==ctx]
        if not subset:raise RuntimeError('selection missing context')
        quality=[(GatedLearner(parent,edge,(level,level)).score(subset),-i,level)
                 for i,level in enumerate(choices)]
        gate.append(max(quality)[2])
    gated=GatedLearner(parent,edge,tuple(gate))
    deleted=GatedLearner(parent,edge,(0.,0.))
    audit={}
    for i,kind in enumerate(DOMAINS):
        rows=rows_for(seed,i,kind,'sealed_gate_audit',audit_count)
        base=parent.score(rows);hard=deleted.score(rows);adapt=gated.score(rows)
        audit[kind]={'original':round(base,8),'deletion':round(hard,8),'conditional':round(adapt,8),
                     'conditional_minus_original':round(adapt-base,8),
                     'conditional_minus_deletion':round(adapt-hard,8)}
    after=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    if before!=after:raise AssertionError('gate mutated shared parent')
    return {'protocol':PROTOCOL,'seed':seed,'edge':list(edge),'context_gates':gate,
            'frozen_state_sha256':before,'parent_unchanged':True,
            'selection_count':len(selection),'audit':audit,
            'sealed_audit_unused_in_selection':True,'certified_ais':0}

def run(seeds=range(32),report=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)) or any(type(i)!=int or i<0 or i>=2**31 for i in ids):
        raise ValueError('expected unique valid seeds')
    records=[trial(s) for s in ids]
    summary={}
    for j,kind in enumerate(DOMAINS):
        values=[r['audit'][kind]['conditional_minus_original'] for r in records]
        other=[r['audit'][kind]['conditional_minus_deletion'] for r in records]
        summary[kind]={'versus_original_pp':round(statistics.fmean(values)*100,4),
                       'versus_deletion_pp':round(statistics.fmean(other)*100,4),
                       'bootstrap_original_95_pp':[round(v*100,4) for v in bootstrap_interval(values,replicates=1000,seed=3000+j)]}
    payload={'protocol':PROTOCOL,'seed_count':len(ids),'summaries':summary,
             'gate_usage':{'no_change':sum(r['context_gates']==[1.,1.] for r in records),
                           'changed':sum(r['context_gates']!=[1.,1.] for r in records)},
             'records':records,'certified_ais':0,
             'limitation':'Synthetic context-gating selection, no learned real-world causal associations; Mother V3 not connected.'}
    if report:save(Path(report),payload)
    return payload
