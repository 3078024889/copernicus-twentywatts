"""TW31: error-history-conditioned, reusable relational partitions.

No task labels at inference. An association partition is a deterministic gate
policy learned from disjoint calibration/selection rows, not a causal discovery.
All comparisons share frozen parent weights and sealed audit data.
"""
from __future__ import annotations
import hashlib
import json
import statistics
from pathlib import Path
from .context_gate import GatedLearner, DOMAINS
from .intervention_lab import PARENT
from .relational_dendrites import RelationalLearner
from .twin_evolution import rows_for
from .twin_backtest import bootstrap_interval, save

PROTOCOL = 'TW31_ERROR_HISTORY_ASSOCIATION_PARTITIONS_V1'
LEVELS = (1., .5, 0.)
PARTITIONS = ('context', 'interaction_sign', 'input_sign')

def partition_key(x, context, axis):
    if axis == 'context': return int(bool(context))
    if axis == 'interaction_sign': return int(x[0] * x[1] >= 0)
    if axis == 'input_sign': return int(x[0] >= 0)
    raise ValueError('unknown partition axis')

class PartitionedLearner:
    def __init__(self, model, edge, axis, levels):
        if axis not in PARTITIONS or len(levels) != 2 or any(x not in LEVELS for x in levels):
            raise ValueError('invalid gate specification')
        if tuple(edge) not in model.syn: raise ValueError('edge absent from model')
        self.model, self.edge, self.axis = model, tuple(edge), axis
        self.levels = tuple(levels)

    def predict(self, x, context=0):
        gate = self.levels[partition_key(x, context, self.axis)]
        original = self.model.syn[self.edge]
        self.model.syn[self.edge] = original * gate
        try: return self.model.predict(x, context)
        finally: self.model.syn[self.edge] = original

    def score(self, rows):
        return sum((self.predict(x,c) >= .5) == y for x,y,c in rows) / len(rows)

def _accuracy(model, rows):
    return sum((model.predict(x,c) >= .5) == y for x,y,c in rows) / len(rows)

def trial(seed, training_count=40, calibration_count=48, selection_count=60, audit_count=80):
    if type(seed) != int or not 0 <= seed < 2**31 or min(training_count,calibration_count,selection_count,audit_count)<12:
        raise ValueError('invalid seed/sample counts')
    parent=RelationalLearner(PARENT)
    for i,kind in enumerate(DOMAINS):
        for x,y,c in rows_for(seed,i,kind,'train',training_count):
            parent.learn(x,y,c)
    frozen=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    # Error history is recorded from calibration rows (disjoint from both
    # selection and holdout), and determines which edge to investigate.
    calibration=[row for i,kind in enumerate(DOMAINS)
                 for row in rows_for(seed,i,kind,'partition_calibration',calibration_count)]
    baseline_errors=[abs(y-parent.predict(x,c)) for x,y,c in calibration]
    edge_impacts=[]
    for edge in parent.graph:
        removed=GatedLearner(parent,edge,(0.,0.))
        # Restrict attribution to actual mistakes. If none, score all samples.
        failures=[row for row in calibration if (parent.predict(row[0],row[2])>=.5)!=row[1]]
        subset=failures if failures else calibration
        advantage=statistics.fmean(abs(parent.predict(x,c)-removed.predict(x,c)) for x,y,c in subset)
        edge_impacts.append((advantage,edge))
    edge=sorted(edge_impacts,key=lambda r:(-r[0],r[1]))[0][1]
    selection=[row for i,kind in enumerate(DOMAINS)
               for row in rows_for(seed,i,kind,'partition_selection',selection_count)]
    # General, context-only and partitioned policies use the exact same
    # candidate gate levels and selection rows. No audit is opened here.
    def best_gate(axis):
        gates=[]
        for key in (0,1):
            rows=[r for r in selection if partition_key(r[0],r[2],axis)==key]
            if len(rows)<12: return None
            results=[(_accuracy(GatedLearner(parent,edge,(level,level)),rows),-idx,level)
                     for idx,level in enumerate(LEVELS)]
            gates.append(max(results)[2])
        return tuple(gates)
    # A common global deletion is a useful diagnostic baseline.
    global_deletion=GatedLearner(parent,edge,(0.,0.))
    # Determine policy using only selection accuracies, preferring unchanged
    # unless there is an explicit minimum improvement of one sample.
    policies=[]
    for axis in PARTITIONS:
        levels=best_gate(axis)
        if levels is None:continue
        policy=PartitionedLearner(parent,edge,axis,levels)
        benefit=policy.score(selection)-parent.score(selection)
        policies.append((benefit,axis,levels))
    # No-domain-sacrifice gate: candidate must improve aggregate selection
    # and must not lose more than a single selection example per domain.
    domain_selection=[[row for row in rows_for(seed,i,kind,'partition_selection',selection_count)]
                      for i,kind in enumerate(DOMAINS)]
    guard_rejected=0
    candidates=[]
    for p in policies:
        if p[0]<1/len(selection):continue
        candidate=PartitionedLearner(parent,edge,p[1],p[2])
        if any(candidate.score(rows)<parent.score(rows)-1/len(rows)-1e-10
               for rows in domain_selection):
            guard_rejected+=1
            continue
        candidates.append(p)
    selected=sorted(candidates,key=lambda p:(-p[0],PARTITIONS.index(p[1])))[0] if candidates else None
    partitioned=PartitionedLearner(parent,edge,selected[1],selected[2]) if selected else None
    # Context gate is a preregistered policy and serves as an independent
    # algorithm comparator on the same training and selection experiences.
    context_levels=best_gate('context')
    context_policy=PartitionedLearner(parent,edge,'context',context_levels)
    audit={}
    for i,kind in enumerate(DOMAINS):
        rows=rows_for(seed,i,kind,'sealed_partition_audit',audit_count)
        b=parent.score(rows)
        d=global_deletion.score(rows)
        c=context_policy.score(rows)
        p=partitioned.score(rows) if partitioned else b
        audit[kind]={'original':round(b,8),'deletion':round(d,8),'context_gate':round(c,8),
                     'partition':round(p,8),'partition_minus_original':round(p-b,8),
                     'partition_minus_context':round(p-c,8)}
    final=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    if frozen!=final:raise AssertionError('frozen learner was mutated')
    return {'protocol':PROTOCOL,'seed':seed,'edge':list(edge),
            'calibration_error_mean':round(statistics.fmean(baseline_errors),6),
            'calibration_mistakes':sum((parent.predict(x,c)>=.5)!=y for x,y,c in calibration),
            'selection_policy':{'axis':selected[1],'levels':list(selected[2]),'selection_delta':round(selected[0],8)} if selected else None,
            'context_levels':list(context_levels),'guard_rejected':guard_rejected,
            'frozen_state_sha256':frozen,
            'parent_unchanged':True,'audit':audit,'certified_ais':0}

def run(seeds=range(48),report=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)) or any(type(i)!=int or i<0 or i>=2**31 for i in ids):
        raise ValueError('require 2+ distinct valid seeds')
    records=[trial(seed) for seed in ids]
    summary={}
    for j,domain in enumerate(DOMAINS):
        old=[r['audit'][domain]['partition_minus_original'] for r in records]
        gate=[r['audit'][domain]['partition_minus_context'] for r in records]
        summary[domain]={'partition_vs_original_pp':round(statistics.fmean(old)*100,4),
                         'partition_vs_context_pp':round(statistics.fmean(gate)*100,4),
                         'bootstrap_original_95_pp':[round(x*100,4) for x in bootstrap_interval(old,replicates=1000,seed=410+j)],
                         'bootstrap_context_95_pp':[round(x*100,4) for x in bootstrap_interval(gate,replicates=1000,seed=510+j)]}
    result={'protocol':PROTOCOL,'seed_count':len(ids),'selected_partitions':sum(r['selection_policy'] is not None for r in records),
            'selection_guard_rejections':sum(r['guard_rejected'] for r in records),
            'axes':{axis:sum(r['selection_policy'] is not None and r['selection_policy']['axis']==axis for r in records) for axis in PARTITIONS},
            'summary':summary,'records':records,'certified_ais':0,
            'limitation':'Synthetic tasks; partition features and gates are predefined; no causal or Mother V3 verification. Search/calibration CPU is not compute-matched.'}
    if report: save(Path(report),result)
    return result
