"""Offline research prototype: relational dendritic *algorithm programs*.

Six families of each of five operators define 7776 executable relational
learning programs. A novel seventh topology produces candidate 7777.
Not a model of a human dendrite; no distinct-behaviour/AI certification.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from collections import deque
from math import exp, sin, pi, tanh
import hashlib, json, random, statistics, time, sqlite3
from contextlib import closing
from pathlib import Path

PROTOCOL='TW23_RELATIONAL_DENDRITES_V1'
TOPO=('ring','chain','star','cross','cluster','skip')
BRANCH=('coincidence','linear','threshold','signed','context','saturating')
PLASTICITY=('local_error','hebb_error','oja_error','three_factor','error_trace','anti_correlation')
MEMORY=('none','recent','surprise','context','associative','consolidate')
META=('fixed','error_slope','surprise','forgetting','branch_switch','confidence')
AXES=(TOPO,BRANCH,PLASTICITY,MEMORY,META)
FIELDS=('topology','branch','plasticity','memory','meta')

@dataclass(frozen=True)
class Variant:
    id:str
    topology:str
    branch:str
    plasticity:str
    memory:str
    meta:str
    parent:str|None
    changed:str
    def genotype(self):return tuple(getattr(self,f) for f in FIELDS)

def catalogue():
    out=[]
    for idx,axes in enumerate(product(*AXES),1):
        digits=[AXES[i].index(op) for i,op in enumerate(axes)]
        changed=[k for k,v in enumerate(digits) if v]
        if changed:
            k=changed[-1];parent_digits=digits[:];parent_digits[k]=0
            parent='D%04d'%(1+sum(v*6**(4-i) for i,v in enumerate(parent_digits)))
            mutation=FIELDS[k]
        else:parent=None;mutation='root'
        out.append(Variant('D%04d'%idx,*axes,parent,mutation))
    # Only a structural addition, not an extra claimed distinct trajectory.
    out.append(Variant('D7777','reciprocal','context','three_factor','associative','forgetting','D%04d'%(1+5*6**4+4*6**3+3*6**2+4*6+3),'topology'))
    return out

def edges(topology):
    # Directed recurrent graph on 8 nodes; topology is executable, not a label.
    if topology=='ring':pairs=[(i,(i+1)%8) for i in range(8)]
    elif topology=='chain':pairs=[(i,i+1) for i in range(7)]
    elif topology=='star':pairs=[(0,i) for i in range(1,8)]
    elif topology=='cross':pairs=[(i,(i+4)%8) for i in range(8)]
    elif topology=='cluster':pairs=[(i,j) for a in (range(4),range(4,8)) for i in a for j in a if i!=j]
    elif topology=='skip':pairs=[(i,(i+2)%8) for i in range(8)]
    elif topology=='reciprocal':pairs=[(i,(i+1)%8) for i in range(8)]+[((i+1)%8,i) for i in range(8)]
    else:raise ValueError(topology)
    return tuple(sorted(set(pairs)))

def stimulus(a,b,context=0):
    return [a,b,a*b,a*a-b*b,sin(pi*a),sin(pi*b),float(a*b>0)*2-1,2*context-1]

def clip(x):return max(-4.,min(4.,x))

class RelationalLearner:
    def __init__(self,variant):
        self.v=variant;self.graph=edges(variant.topology)
        self.syn={e:0.09 for e in self.graph}
        self.readout=[0.]*8;self.error_trace=0.;self.errors=deque(maxlen=12)
        self.memory=deque(maxlen=8);self.experience=0;self.updates=0
        self.rule_changes=0;self.lr=.045;self.last_activation=[0.]*8
        self.last_context=0

    def activations(self,x,context=0):
        base=stimulus(*x,context)
        states=base[:]
        incoming=[[] for _ in range(8)]
        for (src,dst),w in self.syn.items():incoming[dst].append(w*base[src])
        for dst in range(8):
            vals=incoming[dst];total=sum(vals)
            f=self.v.branch
            if f=='coincidence':branch=total+(.4*sum(max(0,v) for v in vals) if len(vals)>1 else 0)
            elif f=='linear':branch=total
            elif f=='threshold':branch=max(0,total-.1)-max(0,-total-.1)
            elif f=='signed':branch=sum(v*abs(v) for v in vals)
            elif f=='context':branch=total*(1.4 if context else .6)
            elif f=='saturating':branch=tanh(2*total)
            else:raise ValueError(f)
            states[dst]=tanh(base[dst]+branch)
        return states

    def predict(self,x,context=0):
        a=self.activations(x,context)
        z=sum(w*h for w,h in zip(self.readout,a))
        return 1/(1+exp(-clip(z)))

    def _meta_adjust(self,error,old_accuracy=None):
        mode=self.v.meta
        old=self.lr
        if mode=='fixed':pass
        elif mode=='error_slope' and len(self.errors)>=3:
            self.lr*=1.12 if self.errors[-1]>statistics.fmean(list(self.errors)[:-1]) else .96
        elif mode=='surprise':self.lr*=1.14 if abs(error)>.65 else .98
        elif mode=='forgetting':self.lr*=.92 if len(self.errors)>=5 and statistics.fmean(list(self.errors)[-2:])>statistics.fmean(list(self.errors)[:2]) else 1.015
        elif mode=='branch_switch':self.lr*=1.09 if self.experience%5==0 else .99
        elif mode=='confidence':self.lr*=.97 if abs(error)<.25 else 1.06
        self.lr=max(.004,min(.15,self.lr))
        if abs(old-self.lr)>1e-12:self.rule_changes+=1

    def learn(self,x,y,context=0,replay=False,replay_policy="native"):
        act=self.activations(x,context)
        p=1/(1+exp(-clip(sum(w*h for w,h in zip(self.readout,act)))))
        error=y-p
        # Local error + postsynaptic activity, with explicit graph plasticity.
        for i in range(8):self.readout[i]=clip(self.readout[i]+self.lr*error*act[i])
        base=stimulus(*x,context)
        for src,dst in self.graph:
            local=base[src]*act[dst]
            mode=self.v.plasticity
            if mode=='local_error':d=error*local
            elif mode=='hebb_error':d=error*local+.05*local
            elif mode=='oja_error':d=error*local-.025*self.syn[(src,dst)]*act[dst]**2
            elif mode=='three_factor':d=error*local*(1.+.2*context)
            elif mode=='error_trace':d=(.65*self.error_trace+.35*error)*local
            elif mode=='anti_correlation':d=error*(base[src]-act[dst])*act[dst]
            else:raise ValueError(mode)
            self.syn[(src,dst)]=max(-1.,min(1.,self.syn[(src,dst)]+.18*self.lr*d))
        self.error_trace=.8*self.error_trace+.2*error
        self.updates+=1
        if not replay:
            self.experience+=1;self.errors.append(abs(error));self._meta_adjust(error)
            if self.v.memory!='none':
                row=(x,y,context,abs(error))
                if self.v.memory=='surprise' and abs(error)<.45:pass
                elif self.v.memory=='context' and not context:pass
                else:self.memory.append(row)
            if replay_policy not in ("native", "fixed"):
                raise ValueError("invalid replay policy")
            should_replay = (self.experience % 5 == 0 and
                             (replay_policy == "fixed" or (self.v.memory != "none" and bool(self.memory))))
            if should_replay:
                if self.memory:
                    if self.v.memory=='associative':best=max(self.memory,key=lambda r:abs(r[0][0]*x[0]+r[0][1]*x[1]))
                    elif self.v.memory=='consolidate':best=min(self.memory,key=lambda r:r[3])
                    else:best=max(self.memory,key=lambda r:r[3]) if self.v.memory=='surprise' else self.memory[-1]
                else:
                    best=(x,y,context,abs(error))
                self.learn(best[0],best[1],best[2],replay=True)
        return p

    def score(self,rows):
        return statistics.fmean((self.predict(x,c)>=.5)==y for x,y,c in rows)

    def state(self):
        return {'syn':sorted([(a,b,round(w,8)) for (a,b),w in self.syn.items()]),
                'readout':[round(x,8) for x in self.readout],'lr':round(self.lr,8),
                'experience':self.experience,'updates':self.updates,'rule_changes':self.rule_changes,
                'errors':list(self.errors),'memory':list(self.memory)}

def tasks(seed,kind,n):
    rng=random.Random('TW23|%s|%s'%(seed,kind));out=[]
    for _ in range(n):
        x=(rng.uniform(-1,1),rng.uniform(-1,1));a,b=x;c=int(rng.random()>.5)
        if kind=='linear':z=1.2*a-.8*b+.05
        elif kind=='interaction':z=a*b+.1*a
        elif kind=='context':z=(a+b if c else a-b)
        elif kind=='relation':z=(a*b if c else (a*a-b*b))
        else:raise ValueError(kind)
        out.append((x,int(z>0),c))
    return out

def behaviour_fingerprint(v):
    m=RelationalLearner(v);pred=[]
    for t,k in enumerate(('linear','interaction','context')):
        rows=tasks(100+t,k,16)
        for x,y,c in rows:m.learn(x,y,c)
        pred.extend(round(m.predict(x,c),5) for x,y,c in tasks(900+t,k,10))
    return hashlib.sha256(json.dumps({'pred':pred,'updates':m.updates,'lr':round(m.lr,5)},separators=(',',':')).encode()).hexdigest()

def paired_experiment(variants,seed=33):
    # Same experiences for every algorithm. Mother is a fixed baseline proxy.
    mother=RelationalLearner(Variant('MOTHER_PROXY','ring','linear','local_error','none','fixed',None,'root'))
    learners=[RelationalLearner(v) for v in variants]
    audit=[]
    for stage,kind in enumerate(('linear','interaction','context','relation')):
        training=tasks(seed*50+stage,kind,40)
        unseen=tasks(seed*50+stage+10000,kind,80)
        for x,y,c in training:
            mother.learn(x,y,c)
            for learner in learners:learner.learn(x,y,c)
        audit.append({'stage':kind,'mother_accuracy':mother.score(unseen),
                      'challenger_accuracies':[m.score(unseen) for m in learners]})
    old=tasks(seed*50+10000,'linear',80)
    return {'seed':seed,'variants':[v.id for v in variants], 'stages':audit,
            'mother_retention':mother.score(old),
            'challenger_retention':[m.score(old) for m in learners],
            'mother_updates':mother.updates,'challenger_updates':[m.updates for m in learners],
            'rule_changes':[m.rule_changes for m in learners],
            'mother_proxy':True,'scope':'SYNTHETIC_EXPLORATION_ONLY'}

def audit_catalogue():
    start=time.perf_counter();pool=catalogue()
    parent={v.id:v for v in pool};ok=True
    for v in pool[1:]:
        old=parent[v.parent];changes=sum(a!=b for a,b in zip(v.genotype(),old.genotype()))
        if changes!=1:ok=False;break
    # Sample fingerprints; do not assert every definition is behaviorally distinct.
    sample=[pool[i] for i in range(0,len(pool),53)]+[pool[-1]]
    hashes=[behaviour_fingerprint(v) for v in sample]
    return {'protocol':PROTOCOL,'registered_variants':len(pool),
            'unique_genotype_definitions':len({v.genotype() for v in pool}),
            'single_step_parent_mutations_valid':ok,
            'behaviour_probe_sample':len(sample),'distinct_sampled_trajectories':len(set(hashes)),
            'sample_collisions':len(sample)-len(set(hashes)),
            'elapsed_seconds':round(time.perf_counter()-start,3),
            'certified_distinct_behaviours':0,'certified_ais':0}
