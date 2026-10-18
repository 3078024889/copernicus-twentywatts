"""Source-inspired, offline staged learning challenges; exploratory evidence only.

No claim that the novel specifies these thresholds or task definitions.
The holdout is never used to select an update. Separate persistent state per contender.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import statistics
from tw8.arena import Learner, dataset, registry
from tw10.resource_meter import measured_evaluation

PROTOCOL = 'TW17_PAIRED_STAGED_CHALLENGES_V2'
STAGES = ('linear', 'interaction', 'shift', 'linear')


@measured_evaluation
def evaluate(candidate, seed):
    """Four experiences: task acquisition, non-linear challenge, transfer, retention.

    Each experience has disjoint training, selector, and final holdout streams.
    Selection of persistent-vs-cold state uses selector only; the holdout is scored
    afterward. The candidate's model is never allowed to read future holdout labels.
    """
    persistent = Learner(candidate)
    record = []
    for stage, task in enumerate(STAGES):
        prefix = 1000000 + seed * 100000 + stage * 17000
        train = dataset(prefix, task, 64)
        selector = dataset(prefix + 40000000, task, 64)
        holdout = dataset(prefix + 80000000, task, 128)
        old_state = list(persistent.w)
        acquired = Learner(candidate)
        acquired.w = old_state
        acquired.steps = persistent.steps
        cold = Learner(candidate)
        control = Learner(candidate)
        random_labels = random.Random(f'{PROTOCOL}/{seed}/{stage}')
        # Prequential stream: predict before revealing the next training label.
        prequential = []
        for features, label in train:
            prequential.append(int(acquired.predict(features) >= .5) == label)
            acquired.update(features, label)
            cold.update(features, label)
            control.update(features, random_labels.randrange(2))
        selector_persistent = acquired.accuracy(selector)
        selector_cold = cold.accuracy(selector)
        selected = acquired if selector_persistent >= selector_cold else cold
        persistent = selected
        record.append({
            'stage': stage + 1, 'task': task,
            'prequential_accuracy': round(statistics.fmean(prequential), 6),
            'selector_persistent': round(selector_persistent, 6),
            'selector_cold': round(selector_cold, 6),
            'policy': 'preserve' if selected is acquired else 'reset',
            'holdout_accuracy': round(selected.accuracy(holdout), 6),
            'holdout_cold': round(cold.accuracy(holdout), 6),
            'holdout_shuffled': round(control.accuracy(holdout), 6),
            'holdout_source': 'disjoint deterministic synthetic stream',
            'train_fingerprint': hashlib.sha256(repr(train).encode()).hexdigest()[:16],
            'selector_fingerprint': hashlib.sha256(repr(selector).encode()).hexdigest()[:16],
            'holdout_fingerprint': hashlib.sha256(repr(holdout).encode()).hexdigest()[:16],
        })
    return {'protocol': PROTOCOL, 'candidate': candidate.key, 'seed': seed,
            'stages': record, 'certified': False, 'scope': 'SYNTHETIC_RESEARCH_ONLY'}


def run(database, candidate_ids, seeds=(1,2,3)):
    dbpath = Path(database)
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    all_candidates = {c.key:c for c in registry()}
    if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)) or not all(x in all_candidates for x in candidate_ids):
        raise ValueError('Candidates must be distinct members of the 7777 registry')
    seeds = tuple(seeds)
    if not seeds or len(seeds) != len(set(seeds)) or any(not isinstance(x, int) or x < 1 for x in seeds):
        raise ValueError('Seeds must be distinct positive integers')
    with closing(sqlite3.connect(dbpath, timeout=30)) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('''CREATE TABLE IF NOT EXISTS staged_trials (
          protocol TEXT NOT NULL, candidate TEXT NOT NULL, seed INTEGER NOT NULL,
          evidence TEXT NOT NULL, PRIMARY KEY(protocol,candidate,seed))''')
        inserted = 0
        for cid in candidate_ids:
            for seed in seeds:
                if conn.execute('SELECT 1 FROM staged_trials WHERE protocol=? AND candidate=? AND seed=?',
                                (PROTOCOL,cid,seed)).fetchone():
                    continue
                evidence = evaluate(all_candidates[cid],seed)
                with conn:
                    conn.execute('INSERT OR IGNORE INTO staged_trials VALUES (?,?,?,?)',
                                 (PROTOCOL,cid,seed,json.dumps(evidence,sort_keys=True)))
                inserted += 1
        # Scope all statistics to the requested cohort, not unrelated prior experiments.
        trials = []
        for cid in candidate_ids:
            for seed in seeds:
                row = conn.execute('SELECT evidence FROM staged_trials WHERE protocol=? AND candidate=? AND seed=?',
                                   (PROTOCOL,cid,seed)).fetchone()
                if row is None: raise RuntimeError(f'Missing persisted evidence {cid}/{seed}')
                trials.append(json.loads(row[0]))
        stored_total = conn.execute('SELECT COUNT(*) FROM staged_trials WHERE protocol=?', (PROTOCOL,)).fetchone()[0]
        stages = []
        for i in range(4):
            a = [t['stages'][i] for t in trials]
            stages.append({'stage':i+1,'task':STAGES[i], 'observations':len(a),
                'holdout_mean':round(statistics.fmean(x['holdout_accuracy'] for x in a),5) if a else None,
                'cold_mean':round(statistics.fmean(x['holdout_cold'] for x in a),5) if a else None,
                'shuffled_mean':round(statistics.fmean(x['holdout_shuffled'] for x in a),5) if a else None,
                'resets':sum(x['policy']=='reset' for x in a)})
        return {'protocol':PROTOCOL,'new_trials':inserted,'total_trials':len(trials),
                'stored_trials_all_cohorts':stored_total,'requested_candidates':len(candidate_ids),
                'requested_seeds':len(seeds),
                'stage_results':stages,'integrity':conn.execute('PRAGMA quick_check').fetchone()[0],
                'certified_independent_ais':0,'mother_promotion':'LOCKED',
                'disclosure':'Candidate configurations; synthetic exploratory protocol; no discovery/AI certification'}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--count',type=int,default=24)
    p.add_argument('--seeds',type=int,default=3)
    a=p.parse_args(argv)
    if not (1 <= a.count <= 7777 and 1 <= a.seeds <= 30):p.error('Out of bounds')
    candidates=registry()
    # Stride samples across registry instead of selecting top-ranked settings.
    selected=list(dict.fromkeys(c.key for c in candidates[::max(1,len(candidates)//a.count)]))[:a.count]
    print(json.dumps(run(a.db,selected,range(1,a.seeds+1)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
