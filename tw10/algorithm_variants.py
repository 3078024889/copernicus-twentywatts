"""Algorithm-program variant laboratory inspired by Copernicus, chapter 41.

A variant changes executable operators, never only numeric hyperparameters.
7777 are distinct operator-program definitions, NOT certified unique behaviours.
Simulation scope: binary synthetic prediction, offline only, no production promotion.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import hashlib, json, math, random, sqlite3, statistics, time
from pathlib import Path
from contextlib import closing

PROTOCOL='TW21_OPERATOR_VARIANTS_V1'
REPRESENTATIONS=('linear','interaction','squares','radial','harmonic','threshold')
LOSSES=('logistic','squared','hinge','absolute','focal','margin')
OPTIMIZERS=('sgd','adagrad','momentum','sign','normalized','rmsprop')
MEMORIES=('none','last','fifo2','fifo4','mistakes','hard')
GATES=('always','every2','every3','uncertain','mistake','alternating')
AXES=(REPRESENTATIONS,LOSSES,OPTIMIZERS,MEMORIES,GATES)
@dataclass(frozen=True)
class Program:
    id:str
    representation:str
    loss:str
    optimizer:str
    memory:str
    gate:str
    parent:str|None
    mutation:str
    def definition(self):
        return {k:getattr(self,k) for k in ('id','representation','loss','optimizer','memory','gate','parent','mutation')}

def registry():
    # 6**5 = 7776 operation graphs. One extra distinct 2nd-order + harmonic representation.
    result=[]
    for i,ops in enumerate(product(*AXES),1):
        # Parent differs in exactly one operator: replace rightmost changed axis
        # with the baseline operator, preserving an auditable mutation graph.
        indices=[AXES[k].index(op) for k,op in enumerate(ops)]
        changed=[k for k,j in enumerate(indices) if j]
        if changed:
            axis=changed[-1]
            parent_index=indices.copy();parent_index[axis]=0
            # Canonical base-6 index of parent genotype (1-indexed).
            code=1+sum(d*6**(4-k) for k,d in enumerate(parent_index))
            parent=f'V{code:04d}'; mutation=('representation','loss','optimizer','memory','gate')[axis]
        else: parent=None;mutation='root'
        result.append(Program(f'V{i:04d}',*ops,parent,mutation))
    parent_id=1+sum((AXES[k].index(v))*6**(4-k) for k,v in enumerate(('harmonic','focal','rmsprop','fifo4','uncertain')))
    result.append(Program('V7777','hybrid_second_order','focal','rmsprop','fifo4','uncertain',f'V{parent_id:04d}','representation'))
    assert len(result)==7777
    return result

def features(mode,x):
    a,b=x
    common=(1.,a,b)
    if mode=='linear': return common
    if mode=='interaction': return common+(a*b,)
    if mode=='squares': return common+(a*a,b*b)
    if mode=='radial': return common+(a*a+b*b,math.hypot(a-.35,b+.25))
    if mode=='harmonic': return common+(math.sin(math.pi*a),math.cos(math.pi*b))
    if mode=='threshold': return common+(float(a>=0),float(b>=0),float(a*b>0))
    if mode=='hybrid_second_order': return common+(a*b,a*a,b*b,math.sin(math.pi*a))
    raise ValueError(mode)

class Learner:
    def __init__(self,p):
        self.p=p;self.w=[0.] * len(features(p.representation,(0.,0.)))
        self.acc=[1e-6]*len(self.w);self.velocity=[0.]*len(self.w)
        self.memory=[];self.t=0;self.updates=0
    def predict(self,x):
        z=sum(w*f for w,f in zip(self.w,features(self.p.representation,x)))
        return 1/(1+math.exp(-max(-25,min(25,z))))
    def _gradient(self,y,p):
        err=y-p
        if self.p.loss=='logistic':return err
        if self.p.loss=='squared':return 2*err*p*(1-p)
        if self.p.loss=='hinge':return (2*y-1) if (2*y-1)*math.log(max(1e-10,p)/max(1e-10,1-p))<1 else 0.
        if self.p.loss=='absolute':return (1. if err>0 else -1.)*p*(1-p)
        if self.p.loss=='focal':return err*abs(err)**2
        if self.p.loss=='margin':return (2*y-1)*max(.0,1.-(2*y-1)*(2*p-1))
        raise ValueError(self.p.loss)
    def _update(self,x,y):
        p=self.predict(x);g=self._gradient(y,p)
        f=features(self.p.representation,x)
        norm=math.sqrt(sum(v*v for v in f)) or 1.
        for j,v in enumerate(f):
            grad=g*v
            opt=self.p.optimizer
            if opt=='adagrad':
                self.acc[j]+=grad*grad;delta=.08*grad/math.sqrt(self.acc[j])
            elif opt=='momentum':
                self.velocity[j]=.8*self.velocity[j]+.10*grad;delta=self.velocity[j]
            elif opt=='sign':delta=.065*(1 if grad>0 else -1 if grad<0 else 0)
            elif opt=='normalized':delta=.14*grad/norm
            elif opt=='rmsprop':
                self.acc[j]=.94*self.acc[j]+.06*grad*grad;delta=.025*grad/math.sqrt(self.acc[j])
            else:delta=.14*grad
            self.w[j]=max(-20.,min(20.,self.w[j]+delta))
        self.updates+=1
    def update(self,x,y):
        self.t+=1;p=self.predict(x)
        gate=self.p.gate
        active=(gate=='always' or gate=='every2' and self.t%2==0 or
                gate=='every3' and self.t%3==0 or gate=='uncertain' and .25<=p<=.75 or
                gate=='mistake' and int(p>=.5)!=y or gate=='alternating' and self.t%4 in (0,1))
        if active:self._update(x,y)
        mode=self.p.memory
        if mode=='none':return
        self.memory.append((x,y,abs(y-p)))
        capacity={'last':1,'fifo2':2,'fifo4':4,'mistakes':4,'hard':4}[mode]
        if mode=='mistakes':self.memory=[row for row in self.memory if row[2]>=.5]
        if mode=='hard':self.memory=sorted(self.memory,key=lambda row:-row[2])[:capacity]
        self.memory=self.memory[-capacity:]
        if active and self.t%3==0 and self.memory:
            selected=self.memory[0] if mode in ('last','fifo2','fifo4') else self.memory[-1]
            self._update(selected[0],selected[1])
    def state(self):
        return {'w':self.w,'acc':self.acc,'velocity':self.velocity,'memory':self.memory,'t':self.t,'updates':self.updates}
    def accuracy(self,rows):
        return statistics.fmean(int(self.predict(x)>=.5)==y for x,y in rows)

def task(seed,kind,n):
    rng=random.Random(f'{PROTOCOL}:{seed}:{kind}')
    rows=[]
    for _ in range(n):
        x=(rng.uniform(-1,1),rng.uniform(-1,1));a,b=x
        z=1.2*a-.7*b+.1 if kind=='linear' else 1.4*a*b+.12*a-.04 if kind=='interaction' else a*a+b*b-.65
        rows.append((x,int(z>0)))
    return rows

def fingerprint(p):
    # Behavioural trajectory probe: independent of ID and parent metadata.
    agent=Learner(p)
    vals=[]
    for kind,seed in [('linear',87),('interaction',61),('radial',12)]:
        rows=task(seed,kind,24)
        for x,y in rows:agent.update(x,y)
        vals.extend(round(agent.predict(x),4) for x,_ in task(seed+100,kind,12))
    raw=json.dumps({'predictions':vals,'updates':agent.updates},separators=(',',':'))
    return hashlib.sha256(raw.encode()).hexdigest()

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS variant_registry(id TEXT PRIMARY KEY,definition TEXT NOT NULL, fingerprint TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS variant_trials(protocol TEXT,id TEXT,seed INTEGER,result TEXT NOT NULL,PRIMARY KEY(protocol,id,seed));''')

def register(db):
    init(db)
    program_list=registry()
    fingerprints=[]
    with db:
        for p in program_list:
            fp=fingerprint(p);fingerprints.append(fp)
            db.execute('INSERT OR IGNORE INTO variant_registry VALUES(?,?,?)',(p.id,json.dumps(p.definition(),sort_keys=True),fp))
    return {'program_definitions':len(program_list),'distinct_probe_trajectories':len(set(fingerprints)),
            'probe_collisions':len(program_list)-len(set(fingerprints))}

def trial(p,seed):
    # All variants see same examples under same task seed.
    agent=Learner(p)
    outcomes=[]
    for i,kind in enumerate(('linear','interaction','radial','linear')):
        rows=task(seed*100+i,kind,64)
        holdout=task(seed*100+i+900000,kind,128)
        before=agent.accuracy(holdout)
        for x,y in rows:agent.update(x,y)
        after=agent.accuracy(holdout)
        cold=Learner(p)
        for x,y in rows:cold.update(x,y)
        outcomes.append({'kind':kind,'before':round(before,6),'after':round(after,6),
                         'cold':round(cold.accuracy(holdout),6)})
    return {'stages':outcomes,'updates':agent.updates,'scope':'SYNTHETIC_EXPLORATION_ONLY'}

def run(db_path,limit=128,seed=131):
    if not (isinstance(limit,int) and 1<=limit<=7777):raise ValueError(limit)
    if not (isinstance(seed,int) and seed>0):raise ValueError(seed)
    path=Path(db_path);path.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    with closing(sqlite3.connect(path)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        overview=register(db)
        done=0
        for p in registry()[:limit]:
            if db.execute('SELECT 1 FROM variant_trials WHERE protocol=? AND id=? AND seed=?',(PROTOCOL,p.id,seed)).fetchone():continue
            evidence=trial(p,seed)
            with db:db.execute('INSERT INTO variant_trials VALUES(?,?,?,?)',(PROTOCOL,p.id,seed,json.dumps(evidence,sort_keys=True)))
            done+=1
        actual=db.execute('SELECT COUNT(*) FROM variant_trials WHERE protocol=? AND seed=?',(PROTOCOL,seed)).fetchone()[0]
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        return dict(overview,seed=seed,completed=actual,new_records=done,elapsed_seconds=round(time.perf_counter()-started,3),certified_ais=0,mother='LOCKED')
