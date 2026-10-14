"""TW32: experience-derived relational split proposals; sealed-audit research only.

A split is learned from error-history signal correlations, not chosen from a
fixed set of context/sign partitions. The candidate family is still constrained
(linear projections); this is NOT causal knowledge discovery or AI certification.
"""
from __future__ import annotations
import hashlib
import json
import math
import statistics
from pathlib import Path
from .association_partitions import trial as tw31_trial, DOMAINS
from .context_gate import GatedLearner
from .intervention_lab import PARENT
from .relational_dendrites import RelationalLearner, stimulus
from .twin_evolution import rows_for
from .twin_backtest import bootstrap_interval, save

PROTOCOL = 'TW32_EXPERIENCE_DERIVED_RELATIONAL_PARTITIONS_V1'
LEVELS = (1., .5, 0.)

def features(x,c):
    # Available at inference; no target/true domain supplied.
    return tuple(stimulus(*x,c))

def learn_boundary(rows, parent, edge):
    """Use calibration prediction error to learn a one-dimensional projection.

    Compare the effect of deleting an edge on erroneous predictions; the
    projection direction is estimated from examples with opposing edge effects.
    """
    if len(rows) < 12: raise ValueError('calibration too small')
    removed = GatedLearner(parent,edge,(0.,0.))
    weighted=[]
    for x,y,c in rows:
        p=parent.predict(x,c); off=removed.predict(x,c)
        # Signed improvement in Brier loss from removal, not hidden audit labels.
        advantage=(y-p)**2-(y-off)**2
        weighted.append((features(x,c),advantage))
    pos=[(f,a) for f,a in weighted if a>0]
    neg=[(f,-a) for f,a in weighted if a<0]
    if not pos or not neg:
        return None
    def centroid(group):
        scale=sum(w for _,w in group)
        return [sum(f[i]*w for f,w in group)/scale for i in range(8)]
    p,n=centroid(pos),centroid(neg)
    direction=tuple(a-b for a,b in zip(p,n))
    length=math.sqrt(sum(v*v for v in direction))
    if length<1e-12:return None
    direction=tuple(v/length for v in direction)
    # Boundary uses only calibration observations; no final audit information.
    threshold=sum((p[i]+n[i])*.5*direction[i] for i in range(8))
    return (direction,threshold)

class ExperiencePartition:
    def __init__(self,parent,edge,boundary,levels):
        if boundary is None or len(boundary[0])!=8 or len(levels)!=2 or any(v not in LEVELS for v in levels):
            raise ValueError('invalid learned split')
        if tuple(edge) not in parent.syn:raise ValueError('edge absent')
        self.parent=parent;self.edge=tuple(edge);self.direction,self.threshold=boundary
        self.levels=tuple(levels)
    def group(self,x,c):
        score=sum(a*b for a,b in zip(self.direction,features(x,c)))
        return int(score>=self.threshold)
    def predict(self,x,c=0):
        level=self.levels[self.group(x,c)]
        previous=self.parent.syn[self.edge]
        self.parent.syn[self.edge]=previous*level
        try:return self.parent.predict(x,c)
        finally:self.parent.syn[self.edge]=previous
    def score(self,rows):
        return sum((self.predict(x,c)>=.5)==y for x,y,c in rows)/len(rows)

def trial(seed,training_count=40,calibration_count=48,selection_count=60,audit_count=80):
    if type(seed)!=int or not 0<=seed<2**31 or min(training_count,calibration_count,selection_count,audit_count)<12:
        raise ValueError('invalid trial inputs')
    parent=RelationalLearner(PARENT)
    for i,kind in enumerate(DOMAINS):
        for x,y,c in rows_for(seed,i,kind,'train',training_count):parent.learn(x,y,c)
    frozen=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    calibration=[r for i,k in enumerate(DOMAINS) for r in rows_for(seed,i,k,'partition_calibration',calibration_count)]
    selection_by_domain=[rows_for(seed,i,k,'partition_selection',selection_count) for i,k in enumerate(DOMAINS)]
    selection=[r for group in selection_by_domain for r in group]
    # Same edge as TW31: fair comparison of learned versus hand-specified split.
    failures=[r for r in calibration if (parent.predict(r[0],r[2])>=.5)!=r[1]]
    subset=failures if failures else calibration
    edge=max(parent.graph,key=lambda e:(statistics.fmean(abs(parent.predict(x,c)-GatedLearner(parent,e,(0.,0.)).predict(x,c)) for x,y,c in subset),tuple(-v for v in e)))
    boundary=learn_boundary(calibration,parent,edge)
    candidates=[];guard_rejections=0
    if boundary is not None:
        # Only gate magnitudes are discrete; the splitting vector is learned.
        for a in LEVELS:
            for b in LEVELS:
                policy=ExperiencePartition(parent,edge,boundary,(a,b))
                gain=policy.score(selection)-parent.score(selection)
                if gain<1/len(selection)-1e-12:continue
                if any(policy.score(group)<parent.score(group)-1/len(group)-1e-12 for group in selection_by_domain):
                    guard_rejections+=1;continue
                candidates.append((gain,a,b))
    best=sorted(candidates,key=lambda z:(-z[0],-z[1],-z[2]))[0] if candidates else None
    chosen=ExperiencePartition(parent,edge,boundary,best[1:]) if best else None
    audit={}
    for i,kind in enumerate(DOMAINS):
        # Shared sealed rows with TW31: independent of both methods' selection.
        rows=rows_for(seed,i,kind,'sealed_partition_audit',audit_count)
        original=parent.score(rows)
        new=chosen.score(rows) if chosen else original
        audit[kind]={'original':round(original,8),'learned':round(new,8),
                     'learned_minus_original':round(new-original,8)}
    final=hashlib.sha256(json.dumps(parent.state(),sort_keys=True).encode()).hexdigest()
    if frozen!=final:raise AssertionError('parent changed during inference')
    return {'protocol':PROTOCOL,'seed':seed,'edge':list(edge),
            'learned_boundary':{'direction':[round(v,8) for v in boundary[0]],'threshold':round(boundary[1],8)} if boundary else None,
            'selection_levels':list(best[1:]) if best else None,'guard_rejections':guard_rejections,
            'parent_frozen_sha256':frozen,'parent_unchanged':True,'audit':audit,'certified_ais':0}

def run(seeds=range(24),report=None):
    ids=list(seeds)
    if len(ids)<2 or len(set(ids))!=len(ids) or any(type(i)!=int or not 0<=i<2**31 for i in ids):
        raise ValueError('invalid seed set')
    ours=[trial(i) for i in ids]
    # TW31 shared tasks, protocol, and sealed audit stream. For paired differences.
    previous=[tw31_trial(i) for i in ids]
    summary={}
    for j,kind in enumerate(DOMAINS):
        diff=[a['audit'][kind]['learned']-b['audit'][kind]['partition'] for a,b in zip(ours,previous)]
        versus=[a['audit'][kind]['learned_minus_original'] for a in ours]
        summary[kind]={'learned_vs_tw31_pp':round(statistics.fmean(diff)*100,4),
                       'learned_vs_original_pp':round(statistics.fmean(versus)*100,4),
                       'paired_bootstrap_95_pp':[round(v*100,4) for v in bootstrap_interval(diff,replicates=1000,seed=3200+j)]}
    output={'protocol':PROTOCOL,'seed_count':len(ids),
            'boundary_proposed':sum(r['learned_boundary'] is not None for r in ours),
            'selected':sum(r['selection_levels'] is not None for r in ours),
            'guard_rejections':sum(r['guard_rejections'] for r in ours),
            'summary':summary,'records':ours,'certified_ais':0,
            'limitations':'Synthetic data; learned linear boundary from supervised errors, not autonomous semantic discovery. Shared frozen parent and sealed rows; not CPU matched, not real V3 Mother; selected audit repeated across research iterations is exploratory, not new independent certification.'}
    if report:save(Path(report),output)
    return output
