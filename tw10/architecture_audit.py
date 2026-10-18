"""Paired, independently seeded architecture experiment; not AI certification.

Unlike the 7777 hyperparameter registry, these are four distinct update/inference
mechanisms: logistic regression, feature-interaction logistic regression,
Gaussian naive Bayes, and bounded k-nearest-neighbor memory.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import sqlite3
from contextlib import closing
import statistics
from tw8.arena import Candidate, Learner, dataset
from tw10.resource_meter import count_operation, measured_evaluation

PROTOCOL = 'TW18_ARCHITECTURE_PAIRED_V1'
STAGES = ('linear', 'interaction', 'shift', 'linear')
ARCHITECTURES = ('linear_sgd', 'interaction_sgd', 'gaussian_nb', 'bounded_knn')

class GaussianNB:
    def __init__(self):
        self.count = [0, 0]
        self.sums = [[0., 0.], [0., 0.]]
        self.squares = [[0., 0.], [0., 0.]]
    def update(self, x, y):
        count_operation()
        self.count[y] += 1
        for j in range(2):
            self.sums[y][j] += x[j]
            self.squares[y][j] += x[j]*x[j]
    def predict(self,x):
        count_operation()
        total = sum(self.count)
        scores=[]
        for c in (0,1):
            n=self.count[c]
            score=math.log((n+1)/(total+2))
            for j in range(2):
                avg=self.sums[c][j]/n if n else 0
                variance=max(0.015, self.squares[c][j]/n-avg*avg) if n else 0.35
                score-=0.5*(math.log(variance)+(x[j]-avg)**2/variance)
            scores.append(score)
        return 1/(1+math.exp(max(-35,min(35,scores[0]-scores[1]))))
    def accuracy(self, rows):
        return sum((self.predict(x)>=0.5)==bool(y) for x,y in rows)/len(rows)

class BoundedKNN:
    def __init__(self, limit=64, k=5):
        self.memory=[]; self.limit=limit; self.k=k
    def update(self,x,y):
        count_operation()
        self.memory.append((tuple(x),y))
        if len(self.memory)>self.limit:self.memory.pop(0)
    def predict(self,x):
        count_operation()
        if not self.memory:return 0.5
        nearest=sorted(self.memory,key=lambda a:(a[0][0]-x[0])**2+(a[0][1]-x[1])**2)[:self.k]
        return sum(y for _,y in nearest)/len(nearest)
    def accuracy(self, rows):
        return sum((self.predict(x)>=0.5)==bool(y) for x,y in rows)/len(rows)

def construct(name):
    if name=='linear_sgd':return Learner(Candidate(0,'linear','decay',0.18,0.00075))
    if name=='interaction_sgd':return Learner(Candidate(0,'interaction','decay',0.18,0.00075))
    if name=='gaussian_nb':return GaussianNB()
    if name=='bounded_knn':return BoundedKNN()
    raise ValueError(name)

@measured_evaluation
def evaluate(name,seed):
    if name not in ARCHITECTURES or not isinstance(seed,int) or seed<1:raise ValueError('invalid architecture or seed')
    learner=construct(name)
    evidence=[]
    for i,task in enumerate(STAGES):
        # Dataset seed never depends on algorithm identity.
        base=9000000+seed*100000+i*1200
        train=dataset(base,task,64)
        holdout=dataset(base+50000000,task,128)
        before=learner.accuracy(holdout)
        # Prequential: assess before every update; holdout stays out of training.
        preq=[]
        for x,y in train:
            preq.append(int(learner.predict(x)>=.5)==y)
            learner.update(x,y)
        after=learner.accuracy(holdout)
        cold=construct(name)
        for x,y in train:cold.update(x,y)
        cold_score=cold.accuracy(holdout)
        evidence.append({'stage':i+1,'task':task,'before':round(before,6),
                         'after':round(after,6),'cold':round(cold_score,6),
                         'transfer_minus_cold':round(after-cold_score,6),
                         'prequential':round(statistics.fmean(preq),6)})
    return {'protocol':PROTOCOL,'architecture':name,'seed':seed,'stages':evidence,
            'scope':'SYNTHETIC_RESEARCH_ONLY','certified':False}

def run(db_path,seeds=(201,202,203,204,205)):
    seeds=tuple(seeds)
    if not seeds or len(set(seeds))!=len(seeds) or any(not isinstance(s,int) or s<1 for s in seeds):raise ValueError('distinct positive seeds required')
    p=Path(db_path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(p)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS architecture_audit (protocol TEXT, architecture TEXT, seed INTEGER, evidence TEXT, PRIMARY KEY (protocol,architecture,seed))')
        added=0
        for seed in seeds:
            for arch in ARCHITECTURES:
                if db.execute('SELECT 1 FROM architecture_audit WHERE protocol=? AND architecture=? AND seed=?',(PROTOCOL,arch,seed)).fetchone():continue
                result=evaluate(arch,seed)
                with db:
                    db.execute('INSERT OR IGNORE INTO architecture_audit VALUES (?,?,?,?)',(PROTOCOL,arch,seed,json.dumps(result,sort_keys=True)))
                added+=1
        results={}
        for arch in ARCHITECTURES:
            rows=[json.loads(db.execute('SELECT evidence FROM architecture_audit WHERE protocol=? AND architecture=? AND seed=?',(PROTOCOL,arch,s)).fetchone()[0]) for s in seeds]
            results[arch]={
                'mean_accuracy_by_stage':[round(statistics.fmean(t['stages'][i]['after'] for t in rows),5) for i in range(4)],
                'mean_transfer_minus_cold':round(statistics.fmean(v['transfer_minus_cold'] for t in rows for v in t['stages']),5),
                'paired_seeds':len(seeds)}
        return {'protocol':PROTOCOL,'architectures':len(ARCHITECTURES),'seeds':list(seeds),
                'trials':len(ARCHITECTURES)*len(seeds),'new_trials':added,'results':results,
                'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
                'certified_independent_ais':0,'promotion':'LOCKED',
                'scope':'SYNTHETIC_RESEARCH_ONLY'}
