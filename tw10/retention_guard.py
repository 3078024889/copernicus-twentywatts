"""TW41: prospective, selection-only knowledge-retention veto.

Comparison is exploratory; no sealed audit participates in mutation selection.
A candidate is accepted only if it improves the current selection task and
avoids a predeclared loss on a disjoint old-task selection set.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
import statistics
from dataclasses import dataclass
from .first_generation import split_rows
from .recursive_lineage import DOMAINS, reprogram
from .relational_dendrites import RelationalLearner, catalogue, FIELDS
from .strategy_memory import mutations
from .prospective_evolution import learn_priors, _bootstrap_ci

PROTOCOL = 'TW41_RETENTION_GUARD_V1'
GUARD_MAX_LOSS = .015625  # one error on a 64-example preservation selection set


def choose(domain, priors, seed, eligible):
    """Freeze a meta proposal before inspecting the current selection answers."""
    eligible = list(eligible)
    if not eligible:
        return None
    supported = [(j, priors.get((domain, FIELDS[j]), (0.0, 0))) for j in eligible]
    supported = [(j, mean, count) for j, (mean, count) in supported if count >= 4]
    if supported:
        return max(supported, key=lambda x: (x[1] * x[2] / (x[2] + 12), -x[0]))[0]
    return random.Random(f'{PROTOCOL}/{seed}/{domain}').choice(eligible)


def run_seed(variant, seed, priors, generations=4):
    if not 2 <= generations <= 12:
        raise ValueError('invalid generations')
    learners = {a: RelationalLearner(variant) for a in ('control', 'protected')}
    traces = {a: [] for a in learners}
    for gen in range(generations):
        domain = DOMAINS[gen % len(DOMAINS)]
        current_rows = split_rows(seed + 170000 + gen, domain, 'train', 48)
        select = split_rows(seed + 170000 + gen, domain, 'selection', 64)
        # Old-task selection set is never used to update parameters. Distinct
        # from both the current selection set and the final sealed audit.
        preserve = split_rows(seed + 280000 + gen, 'linear', 'retention_selection', 64)
        for name in learners:
            current = learners[name]
            options = mutations(current.v, seed * 100 + gen)
            baseline = copy.deepcopy(current)
            candidates = [reprogram(copy.deepcopy(current), v) for v in options]
            for x, y, c in current_rows:
                baseline.learn(x, y, c, replay_policy='fixed')
                for candidate in candidates:
                    candidate.learn(x, y, c, replay_policy='fixed')
            # Both arms evaluate all six states on both selection sets, keeping
            # probe counts matched even when the veto rejects a proposal.
            score = baseline.score(select)
            candidate_scores = [m.score(select) for m in candidates]
            retain = baseline.score(preserve)
            candidate_retains = [m.score(preserve) for m in candidates]
            base_updates = baseline.updates - current.updates
            eligible = [i for i, m in enumerate(candidates)
                        if m.updates - current.updates == base_updates]
            proposal = choose(domain, priors, seed * 100 + gen, eligible)
            benefit = (candidate_scores[proposal] - score) if proposal is not None else 0.0
            damage = (retain - candidate_retains[proposal]) if proposal is not None else 0.0
            veto = (name == 'protected' and damage > GUARD_MAX_LOSS)
            accept = proposal is not None and benefit > 0 and not veto
            learners[name] = candidates[proposal] if accept else baseline
            traces[name].append({
                'generation': gen, 'domain': domain,
                'proposal': FIELDS[proposal] if proposal is not None else None,
                'benefit_selection': round(benefit, 8),
                'retention_loss_selection': round(damage, 8),
                'veto': bool(veto), 'accepted': bool(accept),
                'eligible': len(eligible),
                'update_budget': base_updates + sum(m.updates-current.updates for m in candidates),
                'probe_budget': (1+len(candidates))*(len(select)+len(preserve)),
                'sealed_used_in_selection': False,
            })
    # Only after the last decision is frozen do we reveal the audit tasks.
    audits = {}
    for domain in DOMAINS:
        rows = split_rows(seed + 240000, domain, 'sealed_audit', 192)
        audits[domain] = {a: round(m.score(rows), 8) for a, m in learners.items()}
    budget_ok = (sum(x['update_budget'] for x in traces['control']) ==
                 sum(x['update_budget'] for x in traces['protected']) and
                 sum(x['probe_budget'] for x in traces['control']) ==
                 sum(x['probe_budget'] for x in traces['protected']))
    return {'protocol': PROTOCOL, 'variant': variant.id, 'seed': seed,
            'traces': traces, 'audits': audits, 'budget_operations_equal': budget_ok,
            'selection_guard_threshold': GUARD_MAX_LOSS,
            'mother': 'NOT_REAL_V3_MOTHER', 'certified': False,
            'scope': 'SYNTHETIC_EXPLORATION_ONLY'}


def evaluate(history, count=48, seed=63000, generations=4):
    if not 1 <= count <= 7777:
        raise ValueError('invalid count')
    priors = learn_priors(history)
    pool = catalogue()
    trials = [run_seed(pool[(i*7777)//count], seed+i, priors, generations)
              for i in range(count)]
    equal = [r for r in trials if r['budget_operations_equal']]
    def delta(domain):
        return [r['audits'][domain]['protected'] - r['audits'][domain]['control']
                for r in equal]
    return {
        'protocol': PROTOCOL, 'trials': len(trials), 'budget_eligible': len(equal),
        'guard_vetoes': sum(step['veto'] for r in trials for step in r['traces']['protected']),
        'guard_changed_acceptance': sum(
            a['accepted'] != b['accepted'] for r in trials
            for a,b in zip(r['traces']['control'],r['traces']['protected'])),
        'transfer_delta_pp': round(100*statistics.fmean(delta('relation')),5) if equal else None,
        'retention_delta_pp': round(100*statistics.fmean(delta('linear')),5) if equal else None,
        'transfer_bootstrap_95_pp': _bootstrap_ci(delta('relation')),
        'retention_bootstrap_95_pp': _bootstrap_ci(delta('linear')),
        'trials_evidence_sha256': hashlib.sha256(json.dumps(trials, sort_keys=True).encode()).hexdigest(),
        'certified_ais': 0,
        'limitations': 'Synthetic tasks; matched update/probe calls, not CPU/RAM; historical selection priors; no real Mother; exploratory 64-sample preservation gate.'
    }
