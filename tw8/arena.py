"""Deterministic 7777-candidate *configuration* registry and evidence-gated 12 seats.
Standalone research protocol. Does not touch Mother, V3, Blackbox, or production.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random, sqlite3, statistics, time
from dataclasses import dataclass
from pathlib import Path

PROTOCOL = 'TW8_7777_COMPETITION_V1'
FAMILIES = ('linear', 'interaction')
UPDATES = ('constant', 'decay')

@dataclass(frozen=True)
class Candidate:
    index: int
    family: str
    update: str
    rate: float
    decay: float
    @property
    def key(self): return f'G{self.index:04d}'
    def definition(self): return {'id': self.key,'family':self.family,'update':self.update,'rate':self.rate,'l2':self.decay}

def registry():
    # 2 families × 2 update rules × 45 actual learning rates × 44 real L2 strengths = 7920.
    # First 7777 in a deterministic round-robin mixing of families and updates.
    rates=[round(.015 + i*.009,6) for i in range(45)]
    penalties=[round(j*.00075,7) for j in range(44)]
    result=[]
    for j in range(44):
        for i in range(45):
            for u in UPDATES:
                for f in FAMILIES:
                    result.append(Candidate(len(result)+1,f,u,rates[i],penalties[j]))
                    if len(result)==7777:return result
    raise AssertionError('unreachable')

def dataset(seed, task, n):
    rng=random.Random(f'{PROTOCOL}/{seed}/{task}')
    out=[]
    for _ in range(n):
        a,b=rng.uniform(-1,1),rng.uniform(-1,1)
        if task=='linear': z=1.2*a-.65*b+.08
        elif task=='interaction': z=1.65*a*b+.25*a-.04
        elif task=='shift': z=.9*a-.85*b+.35
        else:raise ValueError(task)
        out.append(((a,b),int(z>0)))
    return out

class Learner:
    def __init__(self,c):
        self.c=c;self.w=[0.0]*(4 if c.family=='interaction' else 3);self.steps=0
    def features(self,x):return [1.0,x[0],x[1]]+([x[0]*x[1]] if self.c.family=='interaction' else [])
    def predict(self,x):
        z=sum(w*v for w,v in zip(self.w,self.features(x)))
        return 1/(1+math.exp(-max(-30,min(30,z))))
    def update(self,x,y):
        p=self.predict(x)
        r=self.c.rate/(1+self.steps/24)**.5 if self.c.update=='decay' else self.c.rate
        v=self.features(x)
        self.w=[w+r*((y-p)*a-self.c.decay*w) for w,a in zip(self.w,v)]
        self.steps+=1
    def accuracy(self,rows):return sum((self.predict(x)>=.5)==bool(y) for x,y in rows)/len(rows)

def trial(c,seed,task='linear',n=48):
    train=dataset(seed,task,n)
    test=dataset(seed+500000,task,64)
    learner=Learner(c)
    before=learner.accuracy(test)
    for x,y in train:learner.update(x,y)
    after=learner.accuracy(test)
    # Same train examples, labels deterministically randomized, negative control.
    negative=Learner(c);rr=random.Random(f'{PROTOCOL}/{seed}/{task}/negative')
    for x,_ in train:negative.update(x,rr.randint(0,1))
    neg_score=negative.accuracy(test)
    return {'improvement':after-before,'accuracy':after,'negative_accuracy':neg_score,
            'beats_negative':after-neg_score,'before':before}

def connect(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''CREATE TABLE IF NOT EXISTS registry(id TEXT PRIMARY KEY, definition TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS trials(protocol TEXT NOT NULL, candidate TEXT NOT NULL, phase TEXT NOT NULL,
    task TEXT NOT NULL, seed INTEGER NOT NULL, result TEXT NOT NULL,
    PRIMARY KEY(protocol,candidate,phase,task,seed));
    CREATE TABLE IF NOT EXISTS seats(protocol TEXT NOT NULL, slot INTEGER NOT NULL, candidate TEXT NOT NULL,
    status TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(protocol,slot));''')
    return db

def register(db):
    with db:db.executemany('INSERT OR IGNORE INTO registry VALUES (?,?)',[(c.key,json.dumps(c.definition(),sort_keys=True)) for c in registry()])
    return db.execute('SELECT count(*) FROM registry').fetchone()[0]

def screen(db,limit=7777,seeds=(1,2),tasks=('linear','interaction')):
    start=time.perf_counter();done=0
    for c in registry()[:limit]:
        rows=[]
        for task in tasks:
            for seed in seeds:
                if db.execute('SELECT 1 FROM trials WHERE protocol=? AND candidate=? AND phase=? AND task=? AND seed=?',(PROTOCOL,c.key,'screen',task,seed)).fetchone():continue
                rows.append((PROTOCOL,c.key,'screen',task,seed,json.dumps(trial(c,seed,task),sort_keys=True)))
        if rows:
            with db:db.executemany('INSERT OR IGNORE INTO trials VALUES (?,?,?,?,?,?)',rows)
            done+=len(rows)
    return {'inserted':done,'seconds':round(time.perf_counter()-start,3)}

def shortlist(db,size=60):
    # Exploration only. Mean improvement compared to own zero-step baseline and negative control.
    rows=db.execute("SELECT candidate,result FROM trials WHERE protocol=? AND phase='screen'",(PROTOCOL,)).fetchall()
    grouped={}
    for cid,res in rows:grouped.setdefault(cid,[]).append(json.loads(res))
    eligible=[]
    for cid,samples in grouped.items():
        if len(samples)<4:continue
        m=statistics.fmean(x['improvement'] for x in samples)
        n=statistics.fmean(x['beats_negative'] for x in samples)
        eligible.append((min(m,n),cid))
    eligible.sort(key=lambda x:(-x[0],x[1]))
    return [cid for _,cid in eligible[:size]]

def verify(db,shortlisted, seeds=range(101,111), tasks=('linear','interaction','shift')):
    by_key={c.key:c for c in registry()};inserted=0
    for cid in shortlisted:
        c=by_key[cid];rows=[]
        for task in tasks:
            for seed in seeds:
                if db.execute('SELECT 1 FROM trials WHERE protocol=? AND candidate=? AND phase=? AND task=? AND seed=?',(PROTOCOL,cid,'holdout',task,seed)).fetchone():continue
                rows.append((PROTOCOL,cid,'holdout',task,seed,json.dumps(trial(c,seed,task),sort_keys=True)))
        if rows:
            with db:db.executemany('INSERT OR IGNORE INTO trials VALUES (?,?,?,?,?,?)',rows)
            inserted+=len(rows)
    return inserted

def select(db, shortlist_ids, slots=12):
    # Research seat nominations only; one configuration per behaviorally meaningful family/update cell;
    # no fake promotion. Do not force-fill seats when evidence isn't sufficient.
    definitions={r[0]:json.loads(r[1]) for r in db.execute('SELECT id,definition FROM registry')}
    winners=[];used=set()
    for cid in shortlist_ids:
        rows=db.execute("SELECT task,result FROM trials WHERE protocol=? AND candidate=? AND phase='holdout'",(PROTOCOL,cid)).fetchall()
        if len(rows)<30:continue
        task_stats={}
        for task,result in rows:task_stats.setdefault(task,[]).append(json.loads(result))
        if set(task_stats)!={'linear','interaction','shift'}:continue
        # Conservative visible exploratory gate, not statistical certification.
        if not all(statistics.fmean(r['improvement'] for r in vals)>.01 and
                   statistics.fmean(r['beats_negative'] for r in vals)>.01 for vals in task_stats.values()):continue
        d=definitions[cid];group=(d['family'],d['update'])
        if group in used:continue
        used.add(group)
        winners.append({'candidate':cid,'group':group,'status':'PROVISIONAL_RESEARCH_ONLY','tasks':{t:{'mean_improvement':round(statistics.fmean(x['improvement'] for x in v),5),'mean_beats_negative':round(statistics.fmean(x['beats_negative'] for x in v),5)} for t,v in task_stats.items()}})
        if len(winners)==slots:break
    # No mutation of production identities, and never label them 12 independent AIs.
    with db:
        db.execute('DELETE FROM seats WHERE protocol=?',(PROTOCOL,))
        for i,w in enumerate(winners,1):
            db.execute('INSERT INTO seats VALUES (?,?,?,?,?)',(PROTOCOL,i,w['candidate'],w['status'],json.dumps(w,sort_keys=True)))
    return winners

def report(db):
    return {'protocol':PROTOCOL,'candidate_configurations':db.execute('SELECT count(*) FROM registry').fetchone()[0],
      'screen_records':db.execute("SELECT count(*) FROM trials WHERE protocol=? AND phase='screen'",(PROTOCOL,)).fetchone()[0],
      'holdout_records':db.execute("SELECT count(*) FROM trials WHERE protocol=? AND phase='holdout'",(PROTOCOL,)).fetchone()[0],
      'provisional_seats':db.execute('SELECT count(*) FROM seats WHERE protocol=?',(PROTOCOL,)).fetchone()[0],
      'certified_independent_ais':0,'mother_promotion':'LOCKED',
      'integrity':db.execute('PRAGMA integrity_check').fetchone()[0]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/tw8.sqlite');p.add_argument('--screen-limit',type=int,default=7777)
    p.add_argument('--output',default='reports/competition.json');a=p.parse_args()
    db=connect(a.db);register(db);timings=screen(db,a.screen_limit)
    ids=shortlist(db)
    if a.screen_limit==7777:
        timings['holdout_inserted']=verify(db,ids)
        winners=select(db,ids)
    else:winners=[]
    result=report(db);result['time']=timings;result['shortlist']=len(ids);result['seats']=winners
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='seats'},ensure_ascii=False,indent=2));db.close()
if __name__=='__main__':main()
