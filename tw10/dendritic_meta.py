"""Controlled dendritic-inspired error-driven meta-learning experiment.

A *dendritic-inspired* variant here is a branch-wise feature learner with
nonlinear feature branch and an error-selected optimizer; it is NOT a biological
neuron simulation. Comparing to Mother is a paired experiment, not certification.
No train/selection examples are used to compute final test metrics.
"""
from __future__ import annotations
from dataclasses import dataclass
from contextlib import closing
from pathlib import Path
import copy, hashlib, json, math, random, sqlite3, statistics
from .algorithm_variants import Program, Learner, task

PROTOCOL='TW22_PAIRED_MOTHER_META_V1'
MOTHER=Program('MOTHER_FIXED','interaction','logistic','sgd','none','always',None,'root')
CHOICES=('sgd','adagrad','momentum','normalized','rmsprop','sign')

def dataset(seed,kind,n,partition):
    """Deterministic disjoint sets even when caller uses same seed."""
    if partition not in ('learn','choose','audit','old_audit'):raise ValueError(partition)
    offset={'learn':1000,'choose':2000,'audit':3000,'old_audit':4000}[partition]
    return task(seed*10000+offset,kind,n)

def accuracy(agent,rows):
    return statistics.fmean(int(agent.predict(x)>=.5)==y for x,y in rows)

def logloss(agent,rows):
    return statistics.fmean(-y*math.log(max(1e-8,agent.predict(x)))-(1-y)*math.log(max(1e-8,1-agent.predict(x))) for x,y in rows)

def train(agent,rows):
    start=agent.updates
    for x,y in rows:agent.update(x,y)
    return agent.updates-start

@dataclass
class Trial:
    seed:int
    change_from_error:bool
    mother_optimizer:str
    selected_optimizer:str
    mother_transfer:float
    challenger_transfer:float
    mother_retention:float
    challenger_retention:float
    mother_updates:int
    challenger_updates:int
    mother_loss:float
    challenger_loss:float
    mother_error_before:float
    selection_error_by_optimizer:dict
    def to_dict(self):return vars(self)

def paired_trial(seed,task_order=('linear','interaction','radial'),budget_ratio=1.5):
    """Three-task sequence: shared experience A, selection on B; untouched audit C.

    The challenger sees B selection examples to choose update algorithm, while
    Mother does not; this is NOT a matched sample access protocol. We therefore
    report this explicitly and never certify performance from this experiment.
    """
    if len(task_order)!=3:raise ValueError('Expected three tasks')
    a,b,c=task_order
    shared=dataset(seed,a,72,'learn')
    mother=Learner(MOTHER); challenger=Learner(MOTHER)
    train(mother,shared);train(challenger,shared)
    old=dataset(seed,a,128,'old_audit')
    # Attempt B, commit via separate, non-audit selection data.
    choose=dataset(seed,b,72,'choose'); learn=dataset(seed,b,72,'learn')
    mother_error_before=logloss(mother,choose)
    # Both models get *exactly* same B training examples and selection examples.
    # Mother uses fixed learning rule, challenger may select rule based on errors.
    # Selection consumes compute beyond Mother: count that explicitly as search cost.
    candidates={};candidate_cost=0
    for opt in CHOICES:
        probe=copy.deepcopy(challenger)
        probe.p=Program('PROBE','interaction','logistic',opt,'none','always',None,'probe')
        candidate_cost+=train(probe,choose)
        candidates[opt]=logloss(probe,choose)
    selected=min(CHOICES,key=lambda opt:(candidates[opt],CHOICES.index(opt)))
    challenger.p=Program('META','interaction','logistic',selected,'none','always',None,'error-rule-selection')
    mother_updates=train(mother,learn)
    challenger_updates=train(challenger,learn)
    # Evaluate on novel task C WITHOUT updating there: genuine zero-shot transfer.
    transfer=dataset(seed,c,160,'audit')
    return Trial(seed,selected!='sgd','sgd',selected,
                 accuracy(mother,transfer),accuracy(challenger,transfer),
                 accuracy(mother,old),accuracy(challenger,old),
                 mother.updates,challenger.updates+candidate_cost,
                 logloss(mother,transfer),logloss(challenger,transfer),
                 mother_error_before,candidates)

def bootstrap_ci(differences,resamples=2000,seed=23):
    rng=random.Random(seed);n=len(differences)
    if not n:return None
    means=sorted(statistics.fmean(rng.choice(differences) for _ in range(n)) for _ in range(resamples))
    return [round(means[int(.025*(resamples-1))],6),round(means[int(.975*(resamples-1))],6)]

def summarize(trials):
    diffs=[t.challenger_transfer-t.mother_transfer for t in trials]
    retain=[t.challenger_retention-t.mother_retention for t in trials]
    ratios=[t.challenger_updates/max(t.mother_updates,1) for t in trials]
    return {'protocol':PROTOCOL,'paired_seeds':len(trials),'mother':'FIXED_BASELINE','test_task':'NOVEL_UNSEEN_TASK_C',
            'mean_transfer_delta':round(statistics.fmean(diffs),6),
            'transfer_95pct_exploratory_bootstrap_ci':bootstrap_ci(diffs),
            'mean_retention_delta':round(statistics.fmean(retain),6),
            'retention_95pct_exploratory_bootstrap_ci':bootstrap_ci(retain),
            'mean_update_budget_ratio':round(statistics.fmean(ratios),3),
            'changed_learning_rule_count':sum(t.change_from_error for t in trials),
            'certified_better_than_mother':False,
            'limits':['Same training and selection examples, but candidate probing consumes extra update budget',
                      'Synthetic tasks; fixed task family; not a blinded independent task domain',
                      'Exploratory intervals without familywise correction or sealed test data']}

def run(db_path,seed_start=501,count=12):
    if count<1 or count>1000:raise ValueError(count)
    path=Path(db_path);path.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS paired_meta_trials(protocol TEXT NOT NULL, seed INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(protocol,seed))')
        for seed in range(seed_start,seed_start+count):
            if db.execute('SELECT 1 FROM paired_meta_trials WHERE protocol=? AND seed=?',(PROTOCOL,seed)).fetchone():continue
            with db:db.execute('INSERT INTO paired_meta_trials VALUES(?,?,?)',(PROTOCOL,seed,json.dumps(paired_trial(seed).to_dict(),sort_keys=True)))
        records=[Trial(**json.loads(row[0])) for row in db.execute('SELECT payload FROM paired_meta_trials WHERE protocol=? AND seed>=? AND seed<? ORDER BY seed',(PROTOCOL,seed_start,seed_start+count))]
        result=summarize(records);result['integrity']=db.execute('PRAGMA quick_check').fetchone()[0]
        return result
