"""Measure append cost at increasing ledger sizes; keeps all data in temp files."""
from __future__ import annotations
import hashlib, json, statistics, tempfile, time
from pathlib import Path
from performance.v3_ledger import FastLedger

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canonical(x).encode('utf-8')).hexdigest()

def legacy_append(path,event):
    prev='GENESIS'
    if path.exists():
        lines=[x for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
        if lines:prev=json.loads(lines[-1])['event_hash']
    e=dict(event);e['schema']='twentywatts-evolution-lab-v3-learning-algorithm';e['ts_ns']=time.time_ns();e['prev_hash']=prev;e['event_hash']=digest(e)
    with path.open('a',encoding='utf-8',newline='\n') as f:f.write(canonical(e)+'\n')

def measure(initial=3000,additional=50):
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);base=root/'base.jsonl'; fast=FastLedger(base,canonical,digest)
        for i in range(initial):fast.append({'type':'SEED','i':i})
        oldfile=root/'old.jsonl';newfile=root/'new.jsonl';content=base.read_bytes();oldfile.write_bytes(content);newfile.write_bytes(content)
        t=time.perf_counter()
        for i in range(additional):legacy_append(oldfile,{'type':'TEST','i':i})
        old=time.perf_counter()-t
        f=FastLedger(newfile,canonical,digest)
        t=time.perf_counter()
        for i in range(additional):f.append({'type':'TEST','i':i})
        new=time.perf_counter()-t
        return {'initial_records':initial,'additional':additional,'legacy_append_sec':round(old,5),'stream_verified_append_sec':round(new,5),'relative_speedup':round(old/new,2),'valid_chain':f.verify(),'bytes':newfile.stat().st_size,'qualification':'isolated Linux disk; not Windows 28720 throughput'}

if __name__=='__main__':print(json.dumps(measure(),ensure_ascii=False,indent=2))
