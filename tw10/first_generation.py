"""Copernicus first-generation registry and paired descendant trial.

A genotype is a program-composition hypothesis, not a verified independent
learning algorithm. Evaluation and sealed audit are different data splits.
This module never touches the legacy V3 Mother or production ports.
"""
from __future__ import annotations
import copy
from dataclasses import replace
import hashlib
import json
import random
import sqlite3
import statistics
from contextlib import closing
from pathlib import Path

from .relational_dendrites import (catalogue, Variant, RelationalLearner, tasks,
                                   AXES, FIELDS, behaviour_fingerprint)

PROTOCOL = 'COPERNICUS_FIRST_GENERATION_V1'


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def initialise(db: Path):
    """Idempotent insert; reject replacement of identities with changed programs."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    variants = catalogue()
    with closing(sqlite3.connect(db, timeout=30)) as conn:
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('CREATE TABLE IF NOT EXISTS first_generation (id TEXT PRIMARY KEY, genotype TEXT NOT NULL, structural_hash TEXT NOT NULL, parent TEXT, changed TEXT NOT NULL, protocol TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS descendants (trial_key TEXT PRIMARY KEY, seed INTEGER NOT NULL, ancestor TEXT NOT NULL, descendant TEXT NOT NULL, mutation TEXT NOT NULL, selection_gain REAL NOT NULL, sealed_transfer_gain REAL NOT NULL, sealed_retention_gain REAL NOT NULL, accepted INTEGER NOT NULL, baseline_updates INTEGER NOT NULL, challenger_updates INTEGER NOT NULL, baseline_probes INTEGER NOT NULL, challenger_probes INTEGER NOT NULL, evidence_hash TEXT NOT NULL, protocol TEXT NOT NULL)')
        for v in variants:
            genotype = json.dumps(v.genotype(), separators=(',', ':'))
            sh = stable_hash({'fields': FIELDS, 'genotype': v.genotype()})
            old = conn.execute('SELECT genotype,structural_hash,parent,changed,protocol FROM first_generation WHERE id=?',(v.id,)).fetchone()
            expected = (genotype, sh, v.parent, v.changed, PROTOCOL)
            if old is not None and old != expected:
                raise ValueError(f'candidate identity drift: {v.id}')
            if old is None:
                conn.execute('INSERT INTO first_generation VALUES (?,?,?,?,?,?)',(v.id,*expected))
        conn.commit()
        count, distinct = conn.execute('SELECT COUNT(*),COUNT(DISTINCT structural_hash) FROM first_generation WHERE protocol=?',(PROTOCOL,)).fetchone()
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
    return {'protocol':PROTOCOL,'registered':count,'unique_structural_programs':distinct,'integrity':integrity,'independent_learning_algorithms_certified':0}


def mutate(v: Variant, seed: int):
    """Change exactly one executable operator, never just a numeric knob."""
    rng = random.Random(f'{PROTOCOL}/mutation/{v.id}/{seed}')
    field_index = rng.randrange(len(FIELDS))
    field = FIELDS[field_index]
    alternatives = [item for item in AXES[field_index] if item != getattr(v, field)]
    # The seventh reciprocal topology is an executable special case.
    if field == 'topology' and v.topology == 'reciprocal':
        alternatives = list(AXES[0])
    successor = rng.choice(alternatives)
    return replace(v, id=f'{v.id}.child.{seed}', parent=v.id, changed=field,
                   **{field:successor})


def split_rows(seed, domain, split, n):
    key = int.from_bytes(hashlib.sha256(f'{PROTOCOL}/{seed}/{domain}/{split}'.encode()).digest()[:8],'big')
    return tasks(key,domain,n)


def trial(v: Variant, seed: int, db: Path | None = None):
    """Same parent state, examples and learner update count. Sealed sets never select.

    Selection compares a single mutated child against an identical unmodified
    control. To prevent unequal replay work, explicit update budget is recorded
    and variants with unequal updates are rejected before comparison.
    """
    parent = RelationalLearner(v)
    warm = split_rows(seed, 'linear', 'warm', 32)
    for x,y,c in warm: parent.learn(x,y,c)
    control = copy.deepcopy(parent)
    adaptive = copy.deepcopy(parent)
    child = mutate(v,seed)
    adaptive.v = child
    current = split_rows(seed, 'context', 'training', 48)
    for x,y,c in current:
        control.learn(x,y,c)
        adaptive.learn(x,y,c)
    select = split_rows(seed,'context','selection',80)
    selected_gain = adaptive.score(select)-control.score(select)
    # Rule proposal accepted on selection only, with equal-update safeguard.
    updates_equal = adaptive.updates == control.updates
    accepted = bool(selected_gain > 0 and updates_equal)
    held = split_rows(seed,'relation','sealed_unseen',128)
    retain = split_rows(seed,'linear','sealed_retention',128)
    sealed_transfer_gain = adaptive.score(held)-control.score(held)
    sealed_retention_gain = adaptive.score(retain)-control.score(retain)
    # Predictor calls: 80 selection + 128 transfer + 128 retention each.
    payload = {'protocol':PROTOCOL,'seed':seed,'ancestor':v.id,'descendant':child.id,
               'mutation':child.changed,'child_genotype':child.genotype(),
               'selection_gain':round(selected_gain,10),
               'sealed_transfer_gain':round(sealed_transfer_gain,10),
               'sealed_retention_gain':round(sealed_retention_gain,10),
               'accepted':accepted,'baseline_updates':control.updates,
               'challenger_updates':adaptive.updates,
               'baseline_probes':336,'challenger_probes':336,
               'mother_is_proxy':False,'comparison':'PARENT_CONTROL_ONLY',
               'certified':False}
    evidence = stable_hash(payload)
    payload['evidence_hash'] = evidence
    if db is not None:
        db = Path(db)
        with closing(sqlite3.connect(db,timeout=30)) as conn:
            row = (stable_hash([PROTOCOL,v.id,seed]),seed,v.id,child.id,child.changed,
                   selected_gain,sealed_transfer_gain,sealed_retention_gain,
                   int(accepted),control.updates,adaptive.updates,336,336,evidence,PROTOCOL)
            old = conn.execute('SELECT * FROM descendants WHERE trial_key=?',(row[0],)).fetchone()
            if old is not None and old != row:
                raise ValueError('Trial evidence conflict; do not overwrite')
            if old is None:
                conn.execute('INSERT INTO descendants VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',row)
            conn.commit()
    return payload


def run(db: Path, first=0, count=48, seed=1100):
    pool=catalogue()
    if not (0 <= first < len(pool) and 1 <= count <= len(pool)-first):
        raise ValueError('invalid candidate slice')
    inventory=initialise(db)
    results=[trial(v,seed,db) for v in pool[first:first+count]]
    eligible=[r for r in results if r['baseline_updates']==r['challenger_updates'] and r['baseline_probes']==r['challenger_probes']]
    return {'inventory':inventory,'trials':len(results),
            'mutations_accepted':sum(x['accepted'] for x in results),
            'budget_eligible_trials':len(eligible),
            'budget_ineligible_trials':len(results)-len(eligible),
            'mean_eligible_unseen_gain_pp':round(100*statistics.fmean(x['sealed_transfer_gain'] for x in eligible),4) if eligible else None,
            'mean_eligible_retention_gain_pp':round(100*statistics.fmean(x['sealed_retention_gain'] for x in eligible),4) if eligible else None,
            'budget_equal':all(x['baseline_updates']==x['challenger_updates'] and x['baseline_probes']==x['challenger_probes'] for x in results),
            'independent_ais_certified':0,'scope':'SYNTHETIC_PARENT_COMPARISON_NOT_REAL_MOTHER'}
