"""Controlled, offline structural mutation of a learned dendritic relation graph.

Research engineering hypothesis inspired by Copernicus (not an algorithm
specified by the novel). Validation selects changes; audit remains untouched.
"""
from __future__ import annotations
import copy
import random
import statistics
from dataclasses import dataclass
from .relational_dendrites import RelationalLearner, Variant, tasks

PROTOCOL = 'TW24_STRUCTURAL_MUTATION_SEALED_AUDIT_V1'


def changed_graph(parent: RelationalLearner, seed: int, count: int = 4):
    """Propose offspring via recurrent edge rewiring, preserving edge count."""
    rng = random.Random(seed)
    result = []
    for index in range(count):
        child = copy.deepcopy(parent)
        edges = list(child.syn)
        removed = rng.choice(edges)
        allowed = [(i, j) for i in range(8) for j in range(8)
                   if i != j and (i, j) not in child.syn]
        inserted = rng.choice(allowed)
        old_weight = child.syn.pop(removed)
        child.syn[inserted] = old_weight
        child.graph = tuple(sorted(child.syn))
        child.v = Variant(f'{parent.v.id}_offspring_{index+1}',
                          'adapted_graph', parent.v.branch,
                          parent.v.plasticity, parent.v.memory,
                          parent.v.meta, parent.v.id, 'topology')
        result.append((child, {'removed': removed, 'inserted': inserted}))
    return result


def run_pair(seed: int, parent_variant: Variant, *, offspring_count: int = 4):
    """Select offspring on predeclared selection data; evaluate only on holdout.

    No simulated Mother production comparison, no self-modifying Python files.
    Training samples and weight updates stay identical; searching costs extra
    inference and must be charged in later equal-compute certification.
    """
    parent = RelationalLearner(parent_variant)
    for x, y, context in tasks(seed * 31, 'linear', 48):
        parent.learn(x, y, context)
    old_audit = tasks(seed * 31 + 1000, 'linear', 128)
    base_retention = parent.score(old_audit)
    selection = tasks(seed * 31 + 2000, 'relation', 96)
    unseen = tasks(seed * 31 + 3000, 'relation', 128)
    # The novel-task holdout is not used in selection or mutation.
    parent_select = parent.score(selection)
    parent_unseen = parent.score(unseen)
    # Only attempt structural mutation after measurable errors on the selection task.
    failure_trigger = parent_select < 0.95
    children = changed_graph(parent, seed * 41 + 7, offspring_count) if failure_trigger else []
    choices = [(parent_select, 0, parent, None)]
    for i, (child, mutation) in enumerate(children, start=1):
        choices.append((child.score(selection), i, child, mutation))
    # Refuse offsprings unless selection score *strictly* improves.
    chosen = max(choices, key=lambda x: (x[0], -x[1]))
    winner = chosen[2]
    assert parent.updates == winner.updates
    return {
        'seed': seed, 'protocol': PROTOCOL,
        'parent_id': parent_variant.id,
        'failure_trigger': failure_trigger,
        'mutation_accepted': chosen[1] > 0,
        'mutation': chosen[3],
        'selection_gain': round(chosen[0] - parent_select, 6),
        'unseen_transfer_gain': round(winner.score(unseen) - parent_unseen, 6),
        'retention_gain': round(winner.score(old_audit) - base_retention, 6),
        'parent_updates': parent.updates,
        'offspring_updates': winner.updates,
        'extra_selection_predictions': len(children) * len(selection),
        'distinct_training_examples': 48,
        'audit_samples': len(unseen),
        'qualification': 'EXPLORATORY_SYNTHETIC_ONLY',
        'certified_ais': 0,
    }


def run_study(seeds=range(24)):
    variant = Variant('DENDRITE_PARENT', 'ring', 'context', 'three_factor',
                      'associative', 'error_slope', None, 'root')
    results = [run_pair(s, variant) for s in seeds]
    avg = lambda k: round(statistics.fmean(row[k] for row in results), 6)
    return {'protocol': PROTOCOL, 'runs': len(results),
            'mutations_accepted': sum(row['mutation_accepted'] for row in results),
            'mean_selection_gain': avg('selection_gain'),
            'mean_unseen_transfer_gain': avg('unseen_transfer_gain'),
            'mean_retention_gain': avg('retention_gain'),
            'total_extra_selection_predictions': sum(r['extra_selection_predictions'] for r in results),
            'certified_ais': 0, 'status': 'SYNTHETIC_EXPLORATION_ONLY',
            'trials': results}
