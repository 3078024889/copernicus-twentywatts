"""TW37: second, independently specified challenge for collisions in a fixed probe.

A larger observed fingerprint set is not a proof of algorithm non-equivalence.
All probes use public synthetic task generators; no sealed audit is accessed.
"""
from __future__ import annotations
import hashlib
import json
import time
from collections import defaultdict
from .relational_dendrites import catalogue, behaviour_fingerprint, RelationalLearner, tasks

PROTOCOL = 'TW37_ADAPTIVE_BEHAVIOUR_DISTINCTION_V1'

def second_probe(v):
    learner=RelationalLearner(v)
    signatures=[]
    # A different order, including the relation family missing in the first probe.
    for stage,kind in enumerate(('relation','context','interaction','linear','relation')):
        for x,y,context in tasks(6000+stage,kind,21):
            learner.learn(x,y,context)
        holdout=tasks(9000+stage,kind,18)
        signatures.extend(round(learner.predict(x,context),7) for x,y,context in holdout)
        signatures.extend((round(learner.lr,7),learner.updates,learner.rule_changes))
    # Hash only behavior; variant identifiers and genotype never count as differences.
    return hashlib.sha256(json.dumps(signatures,separators=(',',':')).encode()).hexdigest()

def audit(limit=7777):
    if not 1<=limit<=7777:raise ValueError('limit must be 1..7777')
    begin=time.perf_counter();pool=catalogue()[:limit]
    groups=defaultdict(list)
    for v in pool:groups[behaviour_fingerprint(v)].append(v)
    old=len(groups)
    new_fingerprints=set();new_count=0;tested=0;still_colliding=0
    # Only run a second, costlier protocol on collided clusters.
    for first,vs in groups.items():
        if len(vs)==1:
            new_fingerprints.add((first,None));new_count+=1;continue
        sub=defaultdict(list)
        for v in vs:
            sub[second_probe(v)].append(v.id);tested+=1
        for second,members in sub.items():
            new_fingerprints.add((first,second));new_count+=1
            still_colliding+=len(members)-1
    return {'protocol':PROTOCOL,'candidate_count':len(pool),'first_probe_unique':old,
            'first_probe_collisions':len(pool)-old,'second_probe_candidates_tested':tested,
            'combined_unique_fingerprints':new_count,'combined_collisions':still_colliding,
            'newly_distinguished':new_count-old,
            'elapsed_seconds':round(time.perf_counter()-begin,3),
            'full_pool':limit==7777,'certified_independent_algorithms':0,
            'scope':'FIXED_SYNTHETIC_PROBES_ONLY',
            'limitations':'Fingerprint disagreement is observational, not a mathematical equivalence proof.'}
