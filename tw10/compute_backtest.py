"""TW46: paired compute/accuracy backtest of fixed versus inherited dendrite routes.

Evaluates arms independently in fresh child processes to avoid attribution of
whole-process CPU and RSS to interleaved branches of the same experiment.
A child is used for both arms to avoid interpreting system load as algorithmic
advantage. Results are exploratory, not an energy or Mother certification.
"""
from __future__ import annotations
import json
import statistics
import subprocess
import sys
from pathlib import Path
from .inherited_routing import run_seed, PROTOCOL as BASE
from .resource_meter import measure

PROTOCOL = 'TW47_CPU_FAIRNESS_GATE_V1'
CPU_TOLERANCE = 0.10

def evaluate(count=8, seed=180000, generations=3):
    if not 2 <= count <= 64 or not 2 <= generations <= 8:
        raise ValueError('bounded evaluation requires 2..64 seeds, 2..8 generations')
    records=[]
    for i in range(count):
        # Each seed is an isolated process so its CPU and RSS can be accounted.
        code = ('import json; from tw10.inherited_routing import run_seed; '
                'from tw10.resource_meter import measure; m={}; '
                'exec("with measure(m):\\n r=run_seed(%d,%d,profile=True)"); '
                'print("TW_RESOURCE_JSON="+json.dumps({"result":r,"resources":m}))') % (seed+i,generations)
        proc=subprocess.run([sys.executable,'-c',code],cwd=str(Path(__file__).resolve().parents[1]),
                            capture_output=True,text=True,timeout=120,check=False)
        if proc.returncode:
            raise RuntimeError(f'compute child {seed+i} failed: {proc.stderr[-1000:]}')
        lines=[line.split('TW_RESOURCE_JSON=',1)[1] for line in proc.stdout.splitlines() if line.startswith('TW_RESOURCE_JSON=')]
        if len(lines)!=1:raise RuntimeError('resource audit payload missing')
        row=json.loads(lines[0]); result=row['result']
        records.append({'seed':seed+i, 'comparable_updates':result['equal_updates'],
                        'comparable_probes':result['equal_selection_probes'],
                        'resources':row['resources'],
                        'transfer_pp':100*(result['audits']['relation']['inherit']-result['audits']['relation']['reset']),
                        'retention_pp':100*(result['audits']['linear']['inherit']-result['audits']['linear']['reset']),
                        'arm_process_cpu_seconds':result['arm_process_cpu_seconds'],
                        'cpu_ratio_inherit_to_reset':result['cpu_ratio_inherit_to_reset'],
                        'cpu_budget_matched':(1-CPU_TOLERANCE <= result['cpu_ratio_inherit_to_reset'] <= 1+CPU_TOLERANCE)})
    valid=[r for r in records if r['comparable_updates'] and r['comparable_probes']]
    fair=[r for r in valid if r['cpu_budget_matched']]
    # CPU gate must be decided without looking at sealed task scores.
    # Preserve non-matching records for the audit, never silently discard them.
    def mean(items,key):
        return statistics.fmean(r[key] for r in items) if items else None
    return {'protocol':PROTOCOL,'seeds':count,'valid':len(valid),
            'mean_transfer_pp':mean(valid,'transfer_pp'),
            'mean_retention_pp':mean(valid,'retention_pp'),
            'cpu_fair_pairs':len(fair),
            'cpu_mismatched_pairs':len(valid)-len(fair),
            'cpu_gate_tolerance_fraction':CPU_TOLERANCE,
            'cpu_fair_mean_transfer_pp':mean(fair,'transfer_pp'),
            'cpu_fair_mean_retention_pp':mean(fair,'retention_pp'),
            'cpu_fair_pair_fraction':len(fair)/len(records) if records else 0,
            'cpu_gate_scope':'observed process CPU for both independently instrumented arms; screening independent of sealed accuracy',
            'total_process_cpu_seconds':sum(r['resources']['process_cpu_seconds'] for r in records),
            'mean_cpu_ratio_inherit_to_reset':statistics.fmean(r['cpu_ratio_inherit_to_reset'] for r in valid) if valid else None,
            'cpu_within_10pct_count':sum(.9 <= r['cpu_ratio_inherit_to_reset'] <= 1.1 for r in valid),
            'total_wall_seconds':sum(r['resources']['wall_seconds'] for r in records),
            'max_observed_end_rss_bytes':max((r['resources']['rss_at_end_bytes'] or 0 for r in records),default=0),
            'records':records,'certified_ais':0,
            'limitations':'CPU-gated comparisons are observational, not forcibly equal CPU budgets. No exact CPU budget, no peak RSS or energy; synthetic tasks; proxy Mother; repeated-seed robustness needed.'}
