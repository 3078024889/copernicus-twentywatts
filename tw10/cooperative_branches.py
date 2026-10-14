"""TW43: source-first, multi-edge dendritic conflict branch ablation.

Research hypothesis, not a mechanism specified by Copernicus. Selection uses
only labelled diagnostics; sealed test streams never influence edge choice.
The identical-capacity feature gate tests whether contextual routing adds value.
"""
from __future__ import annotations
import copy
import hashlib
import json
import statistics
import time
from .conflict_branching import conflict_edge, EdgeBranchLearner
from .first_generation import split_rows
from .relational_dendrites import RelationalLearner, catalogue, stimulus
from .prospective_evolution import _bootstrap_ci

PROTOCOL = 'TW43_COOPERATIVE_BRANCHES_V1'
DOMAINS = ('linear','interaction','context','relation')


def rank_conflicts(model, rows, max_edges=3):
    """Rank opposing signed contextual gradients, no holdout observations."""
    if max_edges < 1: raise ValueError('max_edges must be positive')
    signed = {e:[0.,0.] for e in model.graph}
    counts=[0,0]
    for x,y,c in rows:
        c=int(bool(c)); err=y-model.predict(x,c)
        base=stimulus(*x,c); activations=model.activations(x,c)
        for e in model.graph:
            s,d=e; signed[e][c]+=err*base[s]*activations[d]
        counts[c]+=1
    if min(counts)==0: return []
    ranked=[]
    for e,(a,b) in signed.items():
        a/=counts[0]; b/=counts[1]
        if a*b<0: ranked.append((min(abs(a),abs(b)),e))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return ranked[:max_edges]


class _MultiRouted(RelationalLearner):
    def __init__(self, parent, edge_list, route):
        if route not in ('context','feature'):raise ValueError('invalid route')
        if not edge_list or len(set(edge_list))!=len(edge_list):raise ValueError('invalid edge list')
        if not all(e in parent.syn for e in edge_list):raise ValueError('missing edge')
        self.__dict__=copy.deepcopy(parent.__dict__)
        self.branch_edges=tuple(edge_list)
        self.branch_weights={e:[parent.syn[e],parent.syn[e]] for e in edge_list}
        self.route=route

    def gate(self,x,c):
        return int(bool(c)) if self.route=='context' else int(x[0]>=0)

    def _with_edges(self,x,c,action):
        g=self.gate(x,c)
        original={e:self.syn[e] for e in self.branch_edges}
        for e in self.branch_edges:self.syn[e]=self.branch_weights[e][g]
        try:
            result=action()
            for e in self.branch_edges:self.branch_weights[e][g]=self.syn[e]
            return result
        finally:
            for e,w in original.items():self.syn[e]=w

    def predict(self,x,context=0):
        return self._with_edges(x,context,lambda: super(_MultiRouted,self).predict(x,context))

    def learn(self,x,y,context=0,replay=False,replay_policy='fixed'):
        # RelationalLearner.learn invokes self.learn again for replay, so the
        # historical experience's own context routes its replay branch.
        return self._with_edges(x,context,lambda: super(_MultiRouted,self).learn(
            x,y,context,replay=replay,replay_policy=replay_policy))


def run_seed(seed, variant=None, max_edges=3):
    variant=variant or catalogue()[120]
    warm=split_rows(seed+510000,'linear','tw43_warm',32)
    diagnostic=split_rows(seed+520000,'context','tw43_diagnostics',96)
    training=split_rows(seed+530000,'context','tw43_train_context',64)
    training+=split_rows(seed+540000,'relation','tw43_train_relation',64)
    sealed={d:split_rows(seed+550000,d,'tw43_sealed',192) for d in DOMAINS}
    parent=RelationalLearner(variant)
    for x,y,c in warm:parent.learn(x,y,c,replay_policy='fixed')
    ranked=rank_conflicts(parent,diagnostic,max_edges)
    result={'protocol':PROTOCOL,'seed':seed,'variant':variant.id,
            'edges':[list(e) for _,e in ranked], 'sealed_used_for_selection':False,
            'certified':False,'mother':'PROXY_NOT_REAL_MOTHER'}
    if not ranked:
        return {**result,'comparable':False,'reason':'NO_OPPOSING_GRADIENTS'}
    edges=[e for _,e in ranked]
    plain=copy.deepcopy(parent)
    single=EdgeBranchLearner(parent,edges[0],'context')
    multi=_MultiRouted(parent,edges,'context')
    equal_capacity=_MultiRouted(parent,edges,'feature')
    t0=time.perf_counter()
    for x,y,c in training:
        plain.learn(x,y,c,replay_policy='fixed')
        single.learn(x,y,c)
        multi.learn(x,y,c,replay_policy='fixed')
        equal_capacity.learn(x,y,c,replay_policy='fixed')
    training_wall=time.perf_counter()-t0
    budgets={'plain':plain.updates,'single':single.updates,
             'multi':multi.updates,'capacity':equal_capacity.updates}
    audits={d:{'plain':plain.score(rows),'single':single.score(rows),
               'multi':multi.score(rows),'capacity':equal_capacity.score(rows)}
            for d,rows in sealed.items()}
    return {**result,'comparable':len(set(budgets.values()))==1,
            'budget_updates':budgets,'added_weights_single':1,
            'added_weights_multi':len(edges), 'capacity_matched':True,
            'training_wall_seconds_not_budget_matched':round(training_wall,7),
            'audits':audits,'scope':'SYNTHETIC_EXPLORATORY_ONLY'}


def evaluate(seeds=24,first_seed=81000,max_edges=3):
    if not 2<=seeds<=512:raise ValueError('seeds must be 2..512')
    trials=[run_seed(first_seed+i,max_edges=max_edges) for i in range(seeds)]
    valid=[t for t in trials if t['comparable']]
    results={}
    for domain in DOMAINS:
        results[domain]={}
        for control in ('plain','single','capacity'):
            delta=[100*(r['audits'][domain]['multi']-r['audits'][domain][control]) for r in valid]
            results[domain]['multi_vs_'+control+'_pp']=round(statistics.fmean(delta),5) if delta else None
            results[domain]['multi_vs_'+control+'_ci95_pp']=_bootstrap_ci([v/100 for v in delta]) if delta else None
    payload={'protocol':PROTOCOL,'trials':len(trials),'valid_equal_update_trials':len(valid),
             'branches_created':sum(bool(t['edges']) for t in trials),
             'results':results,'certified_ais':0,
             'limitations':'Fixed synthetic tasks, one candidate genotype, different parameter count vs plain/single, not CPU/RAM matched, Mother is proxy, sealed test not used for selection.'}
    payload['evidence_sha256']=hashlib.sha256(json.dumps(trials,sort_keys=True).encode()).hexdigest()
    return payload
