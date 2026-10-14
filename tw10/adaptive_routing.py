"""TW44: learn a contextual edge-routing policy from *non-sealed* experiences.

Research hypothesis; Copernicus does not prescribe a routing formula.
All candidates use the same set of branch weights. The adaptive policy is
selected on separate calibration examples after candidate training; sealed
examples are evaluated once after the policy is frozen.
"""
from __future__ import annotations
import copy, hashlib, json, math, statistics, time
from .cooperative_branches import _MultiRouted, rank_conflicts, DOMAINS
from .first_generation import split_rows
from .relational_dendrites import RelationalLearner, catalogue
from .prospective_evolution import _bootstrap_ci

PROTOCOL='TW44_LEARNED_RELATIONAL_ROUTING_V1'
POLICIES=('context','a_sign','b_sign','product_sign','xor_sign')

class LearnedRoute(_MultiRouted):
    def __init__(self, parent, edge_list, policy):
        if policy not in POLICIES:raise ValueError('unsupported gate')
        super().__init__(parent,edge_list,'context')
        self.policy=policy
    def gate(self,x,c):
        a,b=x
        if self.policy=='context':return int(bool(c))
        if self.policy=='a_sign':return int(a>=0)
        if self.policy=='b_sign':return int(b>=0)
        if self.policy=='product_sign':return int(a*b>=0)
        return int((a>=0) != (b>=0))

def run_seed(seed, variant=None, max_edges=3):
    if max_edges<1:raise ValueError('max_edges must be positive')
    variant=variant or catalogue()[120]
    warm=split_rows(seed+610000,'linear','tw44_warm',32)
    diagnostic=split_rows(seed+620000,'context','tw44_diagnostic',96)
    training=(split_rows(seed+630000,'context','tw44_training',64)
             +split_rows(seed+640000,'relation','tw44_training',64))
    calibration=(split_rows(seed+650000,'context','tw44_calibration',64)
                 +split_rows(seed+660000,'relation','tw44_calibration',64))
    sealed={d:split_rows(seed+670000,d,'tw44_sealed',192) for d in DOMAINS}
    parent=RelationalLearner(variant)
    for x,y,c in warm:parent.learn(x,y,c,replay_policy='fixed')
    ranked=rank_conflicts(parent,diagnostic,max_edges)
    evidence={'protocol':PROTOCOL,'seed':seed,'variant':variant.id,
              'edge_selection':'DIAGNOSTIC_ONLY','routing_selection':'CALIBRATION_ONLY',
              'sealed_used_for_selection':False,'certified':False,
              'mother':'PROXY_NOT_REAL_MOTHER','edges':[list(e) for _,e in ranked]}
    if not ranked:return {**evidence,'comparable':False,'reason':'NO_OPPOSING_GRADIENTS'}
    edges=[e for _,e in ranked]
    start=time.perf_counter()
    base=copy.deepcopy(parent)
    controls={name:LearnedRoute(parent,edges,name) for name in POLICIES}
    for x,y,c in training:
        base.learn(x,y,c,replay_policy='fixed')
        for model in controls.values():model.learn(x,y,c,replay_policy='fixed')
    # The policy search is not compute-equivalent to the fixed baseline: account
    # for all calibration probes, and forbid claiming an equal-compute win.
    cal_scores={name:model.score(calibration) for name,model in controls.items()}
    selected=max(POLICIES,key=lambda name:(cal_scores[name],-POLICIES.index(name)))
    budget={name:m.updates for name,m in controls.items()}
    budget['plain']=base.updates
    duration=time.perf_counter()-start
    audits={d:{**{name:model.score(rows) for name,model in controls.items()},
               'plain':base.score(rows)} for d,rows in sealed.items()}
    return {**evidence,'comparable':len(set(budget.values()))==1,
            'selected':selected,'calibration_scores':cal_scores,
            'selection_probes':len(calibration)*len(POLICIES),
            'budget_updates':budget,'added_weights':len(edges),
            'wall_seconds_unmatched':round(duration,6),
            'audits':audits,'scope':'SYNTHETIC_EXPLORATORY_ONLY'}

def evaluate(seeds=24,first_seed=91000,max_edges=3):
    if not 2<=seeds<=512:raise ValueError('seeds must be 2..512')
    trials=[run_seed(first_seed+i,max_edges=max_edges) for i in range(seeds)]
    good=[t for t in trials if t['comparable']]
    metrics={}
    for domain in DOMAINS:
        metrics[domain]={}
        for comparison in ('context','a_sign','plain'):
            diffs=[100*(r['audits'][domain][r['selected']]-r['audits'][domain][comparison]) for r in good]
            metrics[domain][f'learned_vs_{comparison}_pp']=round(statistics.fmean(diffs),5) if diffs else None
            metrics[domain][f'learned_vs_{comparison}_ci95_pp']=_bootstrap_ci([d/100 for d in diffs]) if diffs else None
    report={'protocol':PROTOCOL,'trials':len(trials),'valid':len(good),
            'policy_choices':{p:sum(r.get('selected')==p for r in good) for p in POLICIES},
            'metrics':metrics,'extra_calibration_probes_per_trial':len(POLICIES)*128,
            'certified_ais':0,'limitations':'One genotype; synthetic tasks; sealed untouched; routing policy search costs extra probes; CPU/RAM and real Mother not matched.'}
    report['evidence_sha256']=hashlib.sha256(json.dumps([{k:v for k,v in t.items() if k!='wall_seconds_unmatched'} for t in trials],sort_keys=True).encode()).hexdigest()
    return report
