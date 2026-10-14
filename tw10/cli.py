"""Single supported command-line entrypoint for guarded research operations.

This runner cannot write to Mother, V3 or Blackbox and never certifies winners.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import unittest
from pathlib import Path
from .operations import inspect
from .release_gate import assess
from .supervisor import supervise

ROOT = Path(__file__).resolve().parents[1]

def main(argv=None):
    ap = argparse.ArgumentParser(description='TwentyWatts verified research entrypoint')
    ap.add_argument('action', choices=('test', 'inspect', 'train', 'gate', 'benchmark', 'benchmark-repeat', 'challenge', 'architecture-audit', 'dendrite-audit', 'twin-evolution', 'twin-cross-validation', 'twin-backtest', 'twin-diagnostic', 'intervention-lab', 'edge-counterfactual', 'context-gate', 'association-partitions', 'learned-partitions', 'first-generation', 'recursive-lineage', 'strategy-memory', 'meta-prediction-audit', 'active-differentiation', 'history-model-selection', 'prospective-evolution', 'retention-guard', 'conflict-branching', 'cooperative-branches', 'adaptive-routing', 'inherited-routing', 'compute-backtest'))
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--source-db', type=Path)
    ap.add_argument('--state-db', type=Path)
    ap.add_argument('--batches', type=int, default=1)
    ap.add_argument('--cycles', type=int, default=1)
    ap.add_argument('--participants', type=int, default=12)
    ap.add_argument('--stop-file', type=Path)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--challenge-count', type=int, default=24)
    ap.add_argument('--challenge-seeds', type=int, default=3)
    ap.add_argument('--challenge-db', type=Path)
    ap.add_argument('--architecture-seeds', type=int, default=5)
    ap.add_argument('--architecture-db', type=Path)
    ap.add_argument('--dendrite-seeds', type=int, default=12)
    ap.add_argument('--twin-seeds', type=int, default=12)
    ap.add_argument('--twin-generations', type=int, default=4)
    ap.add_argument('--twin-db', type=Path)
    ap.add_argument('--generation-first', type=int, default=0)
    ap.add_argument('--generation-count', type=int, default=48)
    ap.add_argument('--generation-seed', type=int, default=1100)
    ap.add_argument('--generation-db', type=Path)
    ap.add_argument('--lineage-count', type=int, default=24)
    ap.add_argument('--lineage-seed', type=int, default=4100)
    ap.add_argument('--lineage-generations', type=int, default=4)
    ap.add_argument('--lineage-db', type=Path)
    a = ap.parse_args(argv)
    root = a.root.resolve()
    source = (a.source_db or root / 'data' / 'v8.sqlite').resolve()
    state = (a.state_db or root / 'data' / 'v11.sqlite').resolve()
    # Strong safety boundary: reject an older state target and the immutable V8 source.
    prohibited = {source, (root / 'data' / 'v9.sqlite').resolve(), (root / 'data' / 'tw8.sqlite').resolve()}
    if a.action != 'test' and state in prohibited:
        ap.error('State path collides with V8 source or legacy V9 database; refusing to modify')
    if a.action in ('benchmark', 'benchmark-repeat'):
        from .real_benchmark import evaluate, evaluate_repeated
        payload = evaluate_repeated() if a.action == 'benchmark-repeat' else evaluate()
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if a.action == 'active-differentiation':
        from .active_differentiation import audit
        payload=audit()
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
    if a.action == 'compute-backtest':
        from .compute_backtest import evaluate
        payload=evaluate(a.lineage_count,a.lineage_seed,a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2));return 0
    if a.action == 'inherited-routing':
        from .inherited_routing import evaluate
        payload=evaluate(a.lineage_count,a.lineage_seed,a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
    if a.action == 'adaptive-routing':
        from .adaptive_routing import evaluate
        payload=evaluate(a.lineage_count,a.lineage_seed)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
    if a.action == 'cooperative-branches':
        from .cooperative_branches import evaluate
        payload = evaluate(a.lineage_count, a.lineage_seed)
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
    if a.action == 'conflict-branching':
        from .conflict_branching import evaluate
        payload = evaluate(a.lineage_count, a.lineage_seed)
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
    if a.action == 'retention-guard':
        from .retention_guard import evaluate
        from .meta_prediction_audit import read_trials
        history = read_trials(a.source_db or root/'data'/'strategy_memory_tw35.sqlite',15500,15572)
        payload = evaluate(history, a.lineage_count, a.lineage_seed, a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False, indent=2));return 0
    if a.action == 'prospective-evolution':
        from .prospective_evolution import run
        payload=run(a.source_db or root/'data'/'strategy_memory_tw35.sqlite',
                    a.lineage_db or root/'data'/'prospective_evolution.sqlite',
                    a.lineage_count,a.lineage_seed,a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
    if a.action == 'history-model-selection':
        from .history_model_selection import run
        payload=run(a.lineage_db or root/'data'/'strategy_memory_tw35.sqlite',report=a.report)
        print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
    if a.action == 'meta-prediction-audit':
        from .meta_prediction_audit import run
        payload=run(a.lineage_db or root/'data'/'strategy_memory_tw35.sqlite', do_fingerprints=True, report=a.report)
        print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0
    if a.action == 'strategy-memory':
        from .strategy_memory import run
        payload = run(a.lineage_db or root/'data'/'strategy_memory.sqlite', a.lineage_count, a.lineage_seed, a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0
    if a.action == 'recursive-lineage':
        from .recursive_lineage import run
        payload = run(a.lineage_db or root/'data'/'recursive_lineage.sqlite', a.lineage_count, a.lineage_seed, a.lineage_generations)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0
    if a.action == 'first-generation':
        from .first_generation import run
        payload=run(a.generation_db or root/'data'/'first_generation.sqlite', a.generation_first, a.generation_count, a.generation_seed)
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0
    if a.action == 'learned-partitions':
        from .learned_partitions import run
        if not 2 <= a.twin_seeds <= 128:
            ap.error('learned partitions requires 2..128 seeds')
        payload=run(range(a.twin_seeds),report=a.report)
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'association-partitions':
        from .association_partitions import run
        if not 2 <= a.twin_seeds <= 128:
            ap.error('association partitions requires 2..128 seeds')
        payload=run(range(a.twin_seeds),report=a.report)
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'context-gate':
        from .context_gate import run
        if not 2 <= a.twin_seeds <= 128:
            ap.error('context gate requires 2..128 seeds')
        payload=run(range(a.twin_seeds),report=a.report)
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'edge-counterfactual':
        from .edge_counterfactual import run
        if not 2 <= a.twin_seeds <= 128:
            ap.error('edge counterfactual requires 2..128 seeds')
        payload=run(range(a.twin_seeds),report=a.report)
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'intervention-lab':
        from .intervention_lab import run
        if not 2 <= a.twin_seeds <= 128:
            ap.error('intervention lab requires 2..128 distinct seeds')
        payload=run(range(a.twin_seeds),report=a.report)
        print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'twin-diagnostic':
        from .twin_diagnostic_backtest import run, save
        if not 2 <= a.twin_seeds <= 128 or not 1 <= a.twin_generations <= 12:
            raise SystemExit('invalid diagnostic backtest bounds')
        payload = run(range(a.twin_seeds), a.twin_generations, db=a.twin_db)
        if a.report: save(a.report,payload)
        print(json.dumps({k:v for k,v in payload.items() if k!='paired'},ensure_ascii=False,indent=2))
        return 0
    if a.action == 'twin-backtest':
        from .twin_backtest import run, save
        if not 2 <= a.twin_seeds <= 128 or not 1 <= a.twin_generations <= 12:
            ap.error('Backtest seeds 2..128 and generations 1..12 required')
        payload = run(range(a.twin_seeds), a.twin_generations, db=a.twin_db)
        if a.report: save(a.report, payload)
        print(json.dumps({k:v for k,v in payload.items() if k != 'paired'}, ensure_ascii=False, indent=2))
        return 0
    if a.action in ('twin-evolution', 'twin-cross-validation'):
        from .twin_evolution import study
        if not 1 <= a.twin_seeds <= 128 or not 1 <= a.twin_generations <= 12:
            ap.error('Twin seeds 1..128 and generations 1..12 required')
        payload = study(range(a.twin_seeds), a.twin_generations, db=a.twin_db, selection_policy=('cross_domain' if a.action == 'twin-cross-validation' else 'current'))
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            temp = a.report.with_suffix(a.report.suffix + '.tmp')
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, a.report)
        print(json.dumps({k:v for k,v in payload.items() if k != 'details'}, ensure_ascii=False, indent=2))
        return 0
    if a.action == 'dendrite-audit':
        from .relational_dendrites import catalogue, audit_catalogue, paired_experiment
        import statistics
        if not 1 <= a.dendrite_seeds <= 100:
            ap.error('Dendritic paired seeds must be 1..100')
        pool=catalogue()
        sample=[pool[i] for i in (0,288,1296,1440,2592,2880,3888,4320,5184,5760,6912,7776)]
        experiments=[paired_experiment(sample,seed=20+i) for i in range(a.dendrite_seeds)]
        rows=[]
        for j,v in enumerate(sample):
            transfer=[e['stages'][-1]['challenger_accuracies'][j]-e['stages'][-1]['mother_accuracy'] for e in experiments]
            retention=[e['challenger_retention'][j]-e['mother_retention'] for e in experiments]
            rows.append({'id':v.id,'genotype':v.genotype(),
                'transfer_delta':round(statistics.fmean(transfer),6),
                'retention_delta':round(statistics.fmean(retention),6),
                'update_cost_ratio':round(statistics.fmean(e['challenger_updates'][j]/e['mother_updates'] for e in experiments),4),
                'meta_rule_changes':round(statistics.fmean(e['rule_changes'][j] for e in experiments),2)})
        payload={'catalogue':audit_catalogue(),'paired_seeds':a.dendrite_seeds,
                 'mother':'EXPERIMENTAL_FIXED_PROXY_NOT_REAL_V3_MOTHER',
                 'results':rows,'certified_winners':0,'scope':'SYNTHETIC_RESEARCH_ONLY',
                 'limitation':'Not same-compute across replay variants; no sealed real-world holdout.'}
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            temp=a.report.with_suffix(a.report.suffix+'.tmp')
            temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,a.report)
        print(json.dumps(payload,ensure_ascii=False,indent=2))
        return 0
    if a.action == 'test':
        tests = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root / 'tests'))
        result = unittest.TextTestRunner(verbosity=2).run(tests)
        return 0 if result.wasSuccessful() else 1
    if not source.is_file():
        ap.error(f'Missing verified V8 source: {source}. Never use synthetic fixture for training.')
    if a.action == 'architecture-audit':
        from .architecture_audit import run as architecture_run
        if not 1 <= a.architecture_seeds <= 30: ap.error('Invalid architecture seed count')
        destination=(a.architecture_db or root/'data'/'architecture_audit.sqlite').resolve()
        if destination in prohibited: ap.error('Architecture database path collision')
        payload=architecture_run(destination,range(201,201+a.architecture_seeds))
    elif a.action == 'challenge':
        import sqlite3
        from contextlib import closing
        from .staged_challenges import run as run_challenges
        from tw8.arena import registry
        from tw8.arena import PROTOCOL as SOURCE_PROTOCOL
        if not (1 <= a.challenge_count <= 7777 and 1 <= a.challenge_seeds <= 30):
            ap.error('Challenge count or seed count out of bounds')
        with closing(sqlite3.connect(f'file:{source.as_posix()}?mode=ro', uri=True)) as conn:
            count = conn.execute('SELECT COUNT(*) FROM registry').fetchone()[0]
            trials = conn.execute('SELECT COUNT(*) FROM trials WHERE protocol=?',(SOURCE_PROTOCOL,)).fetchone()[0]
            if (count, trials) != (7777,32908):ap.error('Unverified V8 source database')
        destination = (a.challenge_db or root/'data'/'staged_challenges.sqlite').resolve()
        if destination in prohibited or destination == source: ap.error('Challenge database path collision')
        pool=registry()
        stride=max(1,len(pool)//a.challenge_count)
        selected=[c.key for c in pool[::stride]][:a.challenge_count]
        payload=run_challenges(destination,selected,range(1,a.challenge_seeds+1))
    elif a.action == 'inspect':
        payload = inspect(source, state)
    elif a.action == 'gate':
        payload = assess(source, state)
    else:
        stop = a.stop_file if a.stop_file else root / 'data' / 'STOP_TW11'
        payload = supervise(source, state, batches=a.batches, cycles=a.cycles,
                            participants=a.participants, stop_file=stop, report=a.report)
    if a.report and a.action in ('inspect', 'gate'):
        a.report.parent.mkdir(parents=True, exist_ok=True)
        temp = a.report.with_suffix(a.report.suffix + '.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, a.report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
