"""Bounded, recoverable foreground supervisor for research, not autonomous deployment.

No unattended promotion or Git operations. Every batch opens/closes SQLite via
operations.execute and uses its single-writer lock. Failures terminate the loop.
"""
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from .operations import execute,inspect

PROTOCOL='TW11_BOUNDED_SUPERVISOR_V1'

def supervise(v8db,v9db,*,batches=1,cycles=1,participants=12,interval=0,stop_file=None,report=None):
    if not (1<=batches<=100 and 1<=cycles<=25 and 1<=participants<=12 and 0<=interval<=86400):
        raise ValueError('Unsupported bounds')
    records=[]
    for i in range(batches):
        if stop_file and Path(stop_file).exists():
            break
        result=execute(v8db,v9db,cycles,participants)
        records.append({'batch':i+1,'advanced':result['advanced_this_run'],
                        'evidence_records':result['evidence_records'],
                        'guard':result.get('transfer_guard'),
                        'integrity':result['integrity']})
        payload={'protocol':PROTOCOL,'batches_completed':len(records),'batches_requested':batches,
                 'records':records,'certified_independent_ais':0,'promotion':'LOCKED',
                 'status':'STOP_REQUESTED' if stop_file and Path(stop_file).exists() else 'BOUNDED_RESEARCH'}
        if report:
            p=Path(report);p.parent.mkdir(parents=True,exist_ok=True)
            temp=p.with_suffix(p.suffix+'.tmp')
            temp.write_text(json.dumps(payload,indent=2),encoding='utf-8');os.replace(temp,p)
        if i+1<batches and interval:
            time.sleep(interval)
    return payload if records else {'protocol':PROTOCOL,'batches_completed':0,
            'status':'STOP_REQUESTED','certified_independent_ais':0,'promotion':'LOCKED'}
