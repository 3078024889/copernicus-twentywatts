"""TW42: pre-registered conflict-driven dendritic edge branching experiment.

Source motivation: Copernicus PDF pp.67,269,771. The branching operator is
an engineering hypothesis, NOT an algorithm published by the novel.

Controls: untouched learner, two-capacity random-route learner, and a
context-route learner; all see identical examples, and audit is never used
for edge or policy selection. The real V3 Mother is not accessed.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
import statistics
from dataclasses import dataclass
from .first_generation import split_rows
from .relational_dendrites import RelationalLearner, catalogue, stimulus
from .prospective_evolution import _bootstrap_ci

PROTOCOL = 'TW42_CONFLICT_BRANCHING_V1'


def conflict_edge(model, rows):
    """Choose edge with opposite contextual signed error-gradients.

    The result is a heuristic conflict *indicator*, not a causal proof.
    Uses training diagnostic labels only; audit remains sealed.
    """
    signed = {edge: [0., 0.] for edge in model.graph}
    mass = [0, 0]
    for x, y, context in rows:
        context = int(bool(context))
        err = y - model.predict(x, context)
        acts = model.activations(x, context)
        base = stimulus(*x, context)
        for src, dst in model.graph:
            signed[(src, dst)][context] += err * base[src] * acts[dst]
        mass[context] += 1
    if min(mass) == 0:
        return None, 0.
    ranked = []
    for edge, (a, b) in signed.items():
        ga, gb = a / mass[0], b / mass[1]
        if ga * gb < 0:
            ranked.append((min(abs(ga), abs(gb)), edge))
    if not ranked:
        return None, 0.
    strength, edge = max(ranked, key=lambda row: (row[0], row[1]))
    return edge, strength


class _RoutedModel(RelationalLearner):
    """Edge context is routed on *every* update, including nested replay."""
    def __init__(self, parent, edge, routing):
        self.__dict__ = copy.deepcopy(parent.__dict__)
        self.branch_edge = edge
        self.branch_routing = routing
        self.branch_weights = [self.syn[edge], self.syn[edge]]

    def gate(self, x, context):
        return int(bool(context)) if self.branch_routing == 'context' else int(x[0] >= 0.)

    def _routed(self, x, context, call):
        gate = self.gate(x, context)
        previous = self.syn[self.branch_edge]
        self.syn[self.branch_edge] = self.branch_weights[gate]
        try:
            result = call()
            self.branch_weights[gate] = self.syn[self.branch_edge]
            return result
        finally:
            self.syn[self.branch_edge] = previous

    def learn(self, x, y, context=0, replay=False, replay_policy='native'):
        return self._routed(x, context, lambda: super(_RoutedModel, self).learn(
            x, y, context, replay=replay, replay_policy=replay_policy))

    def predict(self, x, context=0):
        return self._routed(x, context, lambda: super(_RoutedModel, self).predict(x, context))


class EdgeBranchLearner:
    """Two routed edge weights, preserving context during nested memory replay."""
    def __init__(self, parent, edge, routing):
        if routing not in ('context','feature'):
            raise ValueError('invalid routing')
        if edge not in parent.syn:
            raise ValueError('edge missing from parent')
        self.model = _RoutedModel(parent,edge,routing)
        self.edge = edge
        self.routing = routing

    @property
    def weights(self):
        return self.model.branch_weights

    @weights.setter
    def weights(self, values):
        self.model.branch_weights = list(values)

    def gate(self, x, context):
        return self.model.gate(x, context)

    def learn(self,x,y,context):
        return self.model.learn(x,y,context,replay_policy='fixed')

    def predict(self,x,context):
        return self.model.predict(x,context)

    def score(self,rows):
        return statistics.fmean((self.predict(x,c)>=.5)==y for x,y,c in rows)

    @property
    def updates(self):
        return self.model.updates


@dataclass(frozen=True)
class Setup:
    seed: int
    variant_id: str
    edge: tuple[int,int]|None
    conflict_strength: float


def run_seed(seed, variant=None):
    variant = variant or catalogue()[120]
    # Explicitly disjoint training, diagnostics and sealed audit streams.
    warm = split_rows(seed+410000, 'linear', 'branch_warm', 32)
    diagnostics = split_rows(seed+420000, 'context', 'branch_diagnostics', 96)
    learn = split_rows(seed+430000, 'context', 'branch_train_context', 64)
    learn += split_rows(seed+440000, 'relation', 'branch_train_relation', 64)
    # Holdout families have different generators and independent seed streams.
    sealed = {d: split_rows(seed+450000, d, 'branch_sealed_holdout', 192)
              for d in ('linear', 'interaction', 'context', 'relation')}
    parent = RelationalLearner(variant)
    for x,y,c in warm:
        parent.learn(x,y,c,replay_policy='fixed')
    edge, strength = conflict_edge(parent, diagnostics)
    plain = copy.deepcopy(parent)
    if edge is None:
        return {'protocol':PROTOCOL,'seed':seed,'variant_id':variant.id,
                'branch_created':False,'conflict_strength':0.,'reason':'NO_OPPOSING_DIAGNOSTIC_GRADIENT',
                'certified':False,'mother':'PROXY_NOT_REAL_MOTHER'}
    routed = EdgeBranchLearner(parent, edge, 'context')
    capacity = EdgeBranchLearner(parent, edge, 'feature')
    for x,y,c in learn:
        plain.learn(x,y,c,replay_policy='fixed')
        routed.learn(x,y,c)
        capacity.learn(x,y,c)
    budgets = {'plain':plain.updates,'routed':routed.updates,'capacity':capacity.updates}
    audits = {d: {'plain':plain.score(rows), 'routed':routed.score(rows),
                  'capacity':capacity.score(rows)} for d,rows in sealed.items()}
    # Report the resource *difference*: branch learners store one extra edge
    # weight and routing logic; matching update counts is NOT equal CPU time.
    return {'protocol':PROTOCOL,'seed':seed,'variant_id':variant.id,
            'branch_created':True,'edge':list(edge),'conflict_strength':round(strength,10),
            'budget_updates':budgets,'updates_equal':len(set(budgets.values()))==1,
            'branch_extra_parameters':1,'capacity_matched':True,
            'audits':audits,'sealed_used_for_selection':False,
            'certified':False,'mother':'PROXY_NOT_REAL_MOTHER',
            'scope':'SYNTHETIC_EXPLORATORY_ONLY'}


def evaluate(seeds=48, first_seed=71000):
    if not 2 <= seeds <= 512: raise ValueError('seeds must be 2..512')
    trials = [run_seed(first_seed+i) for i in range(seeds)]
    valid = [r for r in trials if r['branch_created'] and r['updates_equal']]
    domains = ('linear','interaction','context','relation')
    comparison = {}
    for domain in domains:
        delta_plain = [r['audits'][domain]['routed']-r['audits'][domain]['plain'] for r in valid]
        delta_capacity = [r['audits'][domain]['routed']-r['audits'][domain]['capacity'] for r in valid]
        comparison[domain] = {
            'vs_plain_pp':round(100*statistics.fmean(delta_plain),5) if delta_plain else None,
            'vs_capacity_matched_pp':round(100*statistics.fmean(delta_capacity),5) if delta_capacity else None,
            'vs_plain_ci95_pp':_bootstrap_ci(delta_plain),
            'vs_capacity_ci95_pp':_bootstrap_ci(delta_capacity),
        }
    payload = {'protocol':PROTOCOL,'trials':len(trials),'branches_created':sum(r['branch_created'] for r in trials),
               'valid_equal_update_trials':len(valid),'results':comparison,
               'certified_ais':0,
               'limitations':'Synthetic fixed candidate, one extra parameter vs plain, no CPU/RAM parity, sealed audits reused for reporting only, real Mother unavailable.'}
    payload['trial_evidence_sha256'] = hashlib.sha256(json.dumps(trials,sort_keys=True).encode()).hexdigest()
    return payload
