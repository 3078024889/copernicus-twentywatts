"""Sealed-budget twin learner: a falsifiable meta-learning research experiment.

The twins share an identical learned parent. A fixed-rule clone and an
adaptive clone receive exactly the same new examples. Adaptive proposals
change the *learning operator* (plasticity/branch/meta), not just weights.
Both arms spend the same number of predictive evaluations and gradient updates;
unused search budget in the control is explicitly charged as placebo probes.
Selection data cannot overlap sealed transfer/retention data. This is synthetic
research, not an imported V3 Mother nor evidence for AI certification.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
import sqlite3
import statistics
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from .relational_dendrites import Variant, RelationalLearner, tasks, BRANCH, PLASTICITY, META

PROTOCOL = 'TW25_TWIN_META_EVOLUTION_V1'
BASE = Variant('TWIN_ROOT', 'ring', 'linear', 'local_error', 'none', 'fixed', None, 'root')
DOMAINS = ('linear', 'context', 'interaction', 'relation')


def rows_for(seed: int, generation: int, domain: str, split: str, count: int):
    # Explicit domain separation, no Python hash() randomness.
    key = hashlib.sha256(f'{PROTOCOL}/{seed}/{generation}/{domain}/{split}'.encode()).digest()
    return tasks(int.from_bytes(key[:8], 'big'), domain, count)


def variant_proposal(v: Variant, seed: int, generation: int, index: int) -> Variant:
    """A mutation acts on a learning rule, not a hyperparameter alone."""
    rng = random.Random(f'{PROTOCOL}/proposal/{seed}/{generation}/{index}')
    field = ('plasticity', 'branch', 'meta')[index % 3]
    choices = {'plasticity': PLASTICITY, 'branch': BRANCH, 'meta': META}[field]
    current = getattr(v, field)
    next_value = rng.choice([x for x in choices if x != current])
    return replace(v, id=f'{v.id}.g{generation}.p{index}', parent=v.id,
                   changed=field, **{field: next_value})


def diagnose(selection_accuracies, generation):
    """Decision from *selection* evidence only; no sealed split used.

    For each generation: [current, linear retention, next-domain proxy].
    Values are coarse and predeclared to avoid tuning on final audit.
    """
    if len(selection_accuracies) != 3:
        raise ValueError('diagnostic selection requires three observed domains')
    current, retention, transfer = selection_accuracies
    if retention + .04 < current:
        return 'memory_interference'
    if transfer + .04 < current:
        return 'transfer_failure'
    if current < .68:
        return 'prediction_error'
    return 'stability'


def diagnostic_proposal(v, seed, generation, index, failure):
    """Change actual operators according to the *type* of observed failure.

    This is a falsifiable heuristic, not an inferred biological mechanism.
    Each index modifies exactly one operator; the competing policy is still
    subject to the same evaluation and training budget.
    """
    field_orders = {
        'memory_interference': ('meta', 'plasticity', 'branch'),
        'transfer_failure': ('branch', 'plasticity', 'meta'),
        'prediction_error': ('plasticity', 'branch', 'meta'),
        'stability': ('meta', 'branch', 'plasticity'),
    }
    if failure not in field_orders:
        raise ValueError('unrecognized failure diagnosis')
    field = field_orders[failure][index % 3]
    choices = {'plasticity': PLASTICITY, 'branch': BRANCH, 'meta': META}[field]
    rng = random.Random(f'TW27/diagnose/{seed}/{generation}/{index}/{failure}')
    alternative = rng.choice([x for x in choices if x != getattr(v, field)])
    return replace(v, id=f'{v.id}.dg{generation}.p{index}', parent=v.id,
                   changed=field, **{field: alternative})


def evaluation_count(model: RelationalLearner, rows):
    correct = sum((model.predict(x, c) >= .5) == bool(y) for x, y, c in rows)
    return correct / len(rows), len(rows)


def one_trial(seed: int, generations: int = 4, proposals: int = 3,
              training_count: int = 40, validation_count: int = 48,
              audit_count: int = 96, selection_policy: str = 'current'):
    if not (0 <= seed <= 2**31 - 1 and 1 <= generations <= 12 and 1 <= proposals <= 8):
        raise ValueError('seed, generations, or proposals outside safe experimental bounds')
    if min(training_count, validation_count, audit_count) < 8:
        raise ValueError('insufficient examples')
    if selection_policy not in ('current', 'cross_domain', 'diagnostic'):
        raise ValueError('unknown selection policy')
    protocol = {'current': PROTOCOL, 'cross_domain': 'TW26_TWIN_CROSS_DOMAIN_SELECTION_V1', 'diagnostic': 'TW27_TWIN_DIAGNOSTIC_SELECTION_V1'}[selection_policy]
    initial = RelationalLearner(BASE)
    for x, y, c in rows_for(seed, -1, 'linear', 'pretrain', training_count):
        initial.learn(x, y, c)
    fixed = copy.deepcopy(initial)
    adaptive = copy.deepcopy(initial)
    initial_digest = hashlib.sha256(json.dumps(initial.state(), sort_keys=True).encode()).hexdigest()
    generations_data = []
    audit_predictions = {'fixed': 0, 'adaptive': 0}
    search_updates = {'fixed': 0, 'adaptive': 0}
    selection_predictions = {'fixed': 0, 'adaptive': 0}
    for generation in range(generations):
        domain = DOMAINS[generation % len(DOMAINS)]
        examples = rows_for(seed, generation, domain, 'train', training_count)
        # Learn exactly the same stream with equal number of updates (none of the
        # candidate algorithms in this experiment uses experience replay).
        for x, y, c in examples:
            fixed.learn(x, y, c)
            adaptive.learn(x, y, c)
        assert fixed.updates == adaptive.updates
        selection = rows_for(seed, generation, domain, 'selection', validation_count)
        # Both arms see the same extra selection probes. These are independent
        # of all sealed audit splits and never used as training examples.
        auxiliary = []
        if selection_policy in ('cross_domain', 'diagnostic'):
            auxiliary = [
                rows_for(seed, generation, 'linear', 'cross_retention', validation_count),
                rows_for(seed, generation, DOMAINS[(generation + 1) % len(DOMAINS)],
                         'cross_transfer', validation_count),
            ]
        selection_sets = [selection] + auxiliary
        def select_score(model):
            scores = [evaluation_count(model, rows)[0] for rows in selection_sets]
            # Maximize the worst of current, past and held-out-domain proxies.
            # Fixed weights would conceal regressions in one domain.
            return min(scores), len(selection_sets) * validation_count, scores

        # Fixed arm undergoes the same number of selection predictions; these
        # are *placebo* computations, not an artificially trained stronger arm.
        fixed_sel, count, _ = select_score(fixed)
        selection_predictions['fixed'] += count
        adaptive_sel, count, adaptive_scores = select_score(adaptive)
        selection_predictions['adaptive'] += count
        # Diagnosis uses only exposed selection probes. No sealed result can
        # influence mutation type, ordering or acceptance.
        observed = adaptive_scores  # Reuse already charged probes; no hidden diagnostic cost.
        if selection_policy == 'diagnostic':
            failure = diagnose(observed, generation)
        else:
            failure = 'unguided'
        choices = [(adaptive_sel, 0, adaptive, None)]
        adaptation = rows_for(seed, generation, domain, 'adaptation', training_count)
        for i in range(proposals):
            new_v = diagnostic_proposal(adaptive.v, seed, generation, i, failure) if selection_policy == 'diagnostic' else variant_proposal(adaptive.v, seed, generation, i)
            contender = copy.deepcopy(adaptive)
            contender.v = new_v
            placebo = copy.deepcopy(fixed)
            for x, y, c in adaptation:
                contender.learn(x, y, c)
                placebo.learn(x, y, c)
            search_updates['adaptive'] += len(adaptation)
            search_updates['fixed'] += len(adaptation)
            score, count, _ = select_score(contender)
            selection_predictions['adaptive'] += count
            # Equivalent selection computation charged to control twin.
            _, fixed_count, _ = select_score(fixed)
            selection_predictions['fixed'] += fixed_count
            choices.append((score, i + 1, contender, new_v.changed))
        chosen = max(choices, key=lambda z: (z[0], -z[1]))
        # Both active twins learn the same adaptation stream; candidate branches
        # were trained solely for selection, not allowed to gain extra updates
        # by becoming the deployed active twin. Only the chosen *rule* carries.
        selected_rule = chosen[2].v
        adaptive.v = selected_rule
        for x, y, c in adaptation:
            fixed.learn(x, y, c)
            adaptive.learn(x, y, c)
        assert fixed.updates == adaptive.updates
        sealed_transfer = rows_for(seed, generation, domain, 'sealed_transfer', audit_count)
        sealed_retention = rows_for(seed, generation, 'linear', 'sealed_retention', audit_count)
        ft, n1 = evaluation_count(fixed, sealed_transfer)
        at, n2 = evaluation_count(adaptive, sealed_transfer)
        fr, n3 = evaluation_count(fixed, sealed_retention)
        ar, n4 = evaluation_count(adaptive, sealed_retention)
        audit_predictions['fixed'] += n1 + n3
        audit_predictions['adaptive'] += n2 + n4
        generations_data.append({
            'generation': generation, 'domain': domain, **({'failure_diagnosis': failure} if selection_policy == 'diagnostic' else {}), 'parent_id': choices[0][2].v.parent if chosen[1] else adaptive.v.id,
            'chosen_variant': adaptive.v.id, 'mutation_selected': chosen[1] > 0,
            'selection_delta': round(chosen[0] - adaptive_sel, 8),
            'sealed_transfer_delta': round(at - ft, 8),
            'sealed_retention_delta': round(ar - fr, 8),
            'fixed_transfer': ft, 'adaptive_transfer': at,
            'fixed_retention': fr, 'adaptive_retention': ar,
            'updates': fixed.updates, 'search_update_budget': search_updates.copy(),
        })
    # Audit result cannot be used for selecting or accepting candidate mutations.
    return {'protocol': protocol, **({'selection_policy': selection_policy} if selection_policy != 'current' else {}), 'seed': seed, 'initial_state_sha256': initial_digest,
            'generations': generations_data, 'selected_mutations': sum(g['mutation_selected'] for g in generations_data),
            'fixed_updates': fixed.updates, 'adaptive_updates': adaptive.updates,
            'selection_predictions': selection_predictions, 'sealed_predictions': audit_predictions,
            'search_updates': search_updates,
            'compute_accounting': 'MATCHED_TRAINING_UPDATES_AND_PREDICTIONS_WITH_PLACEBO_SEARCH;OTHER_RUNTIME_COSTS_NOT_MATCHED',
            'mother': 'FROZEN_EXPERIMENTAL_PROXY_NOT_REAL_V3_MOTHER',
            'scope': 'SYNTHETIC_EXPLORATION_ONLY', 'certified_ais': 0}


def store(db: Path, trials):
    """Idempotent persisted evidence; disallow overwriting mismatched records."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db, timeout=15)) as con:
        con.execute('CREATE TABLE IF NOT EXISTS twin_trials (protocol TEXT NOT NULL, seed INTEGER NOT NULL, digest TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(protocol,seed))')
        for trial in trials:
            payload = json.dumps(trial, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            digest = hashlib.sha256(payload.encode()).hexdigest()
            prev = con.execute('SELECT digest FROM twin_trials WHERE protocol=? AND seed=?', (trial['protocol'], trial['seed'])).fetchone()
            if prev is not None and prev[0] != digest:
                raise ValueError('non-deterministic or altered twin evidence; refusing overwrite')
            con.execute('INSERT OR IGNORE INTO twin_trials VALUES (?,?,?,?)', (trial['protocol'], trial['seed'], digest, payload))
        con.commit()


def study(seeds=range(12), generations=4, proposals=3, db=None, selection_policy='current'):
    trials = [one_trial(int(seed), generations, proposals, selection_policy=selection_policy) for seed in seeds]
    if db is not None:
        store(Path(db), trials)
    deltas_t = [t['generations'][-1]['sealed_transfer_delta'] for t in trials]
    deltas_r = [t['generations'][-1]['sealed_retention_delta'] for t in trials]
    return {'protocol': trials[0]['protocol'] if trials else PROTOCOL, 'selection_policy': selection_policy, 'trials': len(trials), 'generations_each': generations,
            'accepted_mutations': sum(t['selected_mutations'] for t in trials),
            'final_transfer_delta': round(statistics.fmean(deltas_t), 6),
            'final_retention_delta': round(statistics.fmean(deltas_r), 6),
            'positive_final_transfer': sum(x > 0 for x in deltas_t),
            'negative_final_retention': sum(x < 0 for x in deltas_r),
            'equal_update_counts': all(t['fixed_updates'] == t['adaptive_updates'] and t['search_updates']['fixed'] == t['search_updates']['adaptive'] for t in trials),
            'equal_prediction_counts': all(t['selection_predictions']['fixed'] == t['selection_predictions']['adaptive'] and t['sealed_predictions']['fixed'] == t['sealed_predictions']['adaptive'] for t in trials),
            'certified_ais': 0, 'scope': 'SYNTHETIC_EXPLORATION_ONLY',
            'details': trials}
