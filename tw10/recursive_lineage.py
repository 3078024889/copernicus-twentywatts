"""TW34: reproducible multigeneration lineage / fixed-rule twin experiment.

A candidate is a compositional algorithm hypothesis, not a certified AI.
The sealed audit must not influence mutation or promotion.
"""
from __future__ import annotations
import copy
import json
import sqlite3
import statistics
import time
from contextlib import closing
from pathlib import Path
from .first_generation import mutate, split_rows, stable_hash
from .relational_dendrites import catalogue, RelationalLearner, edges

PROTOCOL = 'COPERNICUS_RECURSIVE_LINEAGE_V1'
DOMAINS = ('linear', 'context', 'interaction', 'relation')


def reprogram(learner, variant):
    """Apply a new executable program including its *actual* edge graph.

    Previously learned edge weights survive wherever an edge is preserved.
    """
    current = learner.syn
    learner.v = variant
    learner.graph = edges(variant.topology)
    learner.syn = {edge: current.get(edge, .09) for edge in learner.graph}
    if set(learner.syn) != set(learner.graph):
        raise AssertionError('Topology mutation not applied')
    return learner


def experiment(ancestor, seed, generations=4):
    if not 1 <= generations <= 12:
        raise ValueError('generations must be 1..12')
    fixed = RelationalLearner(ancestor)
    evolved = copy.deepcopy(fixed)
    lineage = []
    total_start = time.process_time_ns()
    for generation in range(generations):
        domain = DOMAINS[generation % len(DOMAINS)]
        # Same experience, state per individual persisted across generations.
        training = split_rows(seed + 130000 + generation, domain, 'train', 48)
        proposal = mutate(evolved.v, seed * 100 + generation)
        challenger = reprogram(copy.deepcopy(evolved), proposal)
        baseline = copy.deepcopy(evolved)
        fixed_pre = fixed.updates
        for x, y, context in training:
            fixed.learn(x, y, context)
            baseline.learn(x, y, context)
            challenger.learn(x, y, context)
        selection = split_rows(seed + 130000 + generation, domain, 'selection', 64)
        original_score = baseline.score(selection)
        mutant_score = challenger.score(selection)
        # Distinct variants can execute replay at different rates. Reject an
        # unfair comparison rather than silently rewarding extra computation.
        comparable = baseline.updates == challenger.updates
        adopt = comparable and mutant_score > original_score
        evolved = challenger if adopt else baseline
        lineage.append({
            'generation':generation + 1,'domain':domain,
            'ancestor':baseline.v.id,'proposal':proposal.id,
            'changed':proposal.changed,
            'topology_changed':baseline.graph != challenger.graph,
            'baseline_score':round(original_score, 6),
            'proposal_score':round(mutant_score, 6),
            'accepted':adopt,'proposal_comparable':comparable,
            'fixed_training_updates':fixed.updates - fixed_pre,
            'baseline_updates':baseline.updates,
            'proposal_updates':challenger.updates,
            'survivor':evolved.v.id,
            'survivor_state_hash':stable_hash(evolved.state()),
        })
    # These audit datasets are never referenced inside the selection loop.
    audit = {}
    for kind in DOMAINS:
        rows = split_rows(seed + 210000, kind, 'sealed_audit', 192)
        audit[kind] = {'fixed':fixed.score(rows), 'evolved':evolved.score(rows)}
    elapsed = time.process_time_ns() - total_start
    transfer_delta = audit['relation']['evolved'] - audit['relation']['fixed']
    retention_delta = audit['linear']['evolved'] - audit['linear']['fixed']
    evidence = {
        'protocol':PROTOCOL, 'seed':seed, 'ancestor':ancestor.id,
        'generations':generations,'lineage':lineage,'audit':audit,
        'transfer_delta':round(transfer_delta,8),
        'retention_delta':round(retention_delta,8),
        'accepted_generations':sum(x['accepted'] for x in lineage),
        'rejected_unequal_replay':sum(not x['proposal_comparable'] for x in lineage),
        'survivor':evolved.v.id,
        'fixed_total_updates':fixed.updates,
        'evolved_total_updates':evolved.updates,
        'update_budget_equal':fixed.updates == evolved.updates,
        'sealed_used_for_selection':False,
        'mother_baseline':'FROZEN_TWIN_PROXY_NOT_REAL_V3_MOTHER',
        'certified':False,
    }
    evidence['evidence_hash'] = stable_hash(evidence)
    # Timing is instrumentation only; it is not part of deterministic evidence.
    evidence['cpu_process_ns_observed'] = elapsed
    return evidence


def run(db, count=24, seed=4100, generations=4):
    if not 1 <= count <= 7777:
        raise ValueError('count outside registry')
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    pool = catalogue()
    with closing(sqlite3.connect(db,timeout=30)) as conn:
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('CREATE TABLE IF NOT EXISTS recursive_trials (trial_key TEXT PRIMARY KEY, protocol TEXT NOT NULL, ancestor TEXT NOT NULL, seed INTEGER NOT NULL, generations INTEGER NOT NULL, evidence TEXT NOT NULL, evidence_hash TEXT NOT NULL)')
        conn.commit()
        records=[]
        for i in range(count):
            # Deterministic sampling spans the genotype catalogue.
            variant=pool[(i * 7777)//count]
            key = stable_hash([PROTOCOL,variant.id,seed+i,generations])
            current=conn.execute('SELECT evidence,evidence_hash FROM recursive_trials WHERE trial_key=?',(key,)).fetchone()
            if current:
                content,digest=current
                if stable_hash(json.loads(content)) != digest:
                    raise ValueError('Existing lineage evidence corrupted')
                result=json.loads(content)
            else:
                result=experiment(variant,seed+i,generations)
                result.pop('cpu_process_ns_observed',None)
                digest=result.pop('evidence_hash')
                # Hash only immutable payload (without evidence_hash).
                content=json.dumps(result,sort_keys=True,separators=(',',':'))
                if stable_hash(result) != digest:
                    raise ValueError('Experiment evidence digest mismatch')
                conn.execute('INSERT INTO recursive_trials VALUES (?,?,?,?,?,?,?)',(key,PROTOCOL,variant.id,seed+i,generations,content,digest))
                conn.commit()
            records.append(result)
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        total=conn.execute('SELECT COUNT(*) FROM recursive_trials WHERE protocol=?',(PROTOCOL,)).fetchone()[0]
    equal=[r for r in records if r['update_budget_equal']]
    return {'protocol':PROTOCOL,'trials':len(records),'generations':generations,
            'persisted_protocol_trials':total,
            'adopted_proposals':sum(r['accepted_generations'] for r in records),
            'rejected_replay_comparisons':sum(r['rejected_unequal_replay'] for r in records),
            'equal_update_budget_trials':len(equal),
            'unequal_update_budget_trials':len(records)-len(equal),
            'mean_transfer_gain_pp':round(100*statistics.fmean(r['transfer_delta'] for r in equal),4) if equal else None,
            'mean_retention_gain_pp':round(100*statistics.fmean(r['retention_delta'] for r in equal),4) if equal else None,
            'sqlite_integrity':integrity,'certified_ais':0,
            'scope':'SYNTHETIC_MULTIGENERATION_FROZEN_TWIN_PROXY',
            'limitations':'No real Mother; matching update counts does not match wall time or RAM; sealed tasks are synthetic.'}
