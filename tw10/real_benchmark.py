"""Reproducible *real-dataset* read-only challenge, not production AI certification.

Data: scikit-learn bundled UCI Wine and Wisconsin Breast Cancer samples.
The adapter deliberately constrains V8 learners to two train-standardized features;
train/selection/test stratification is deterministic and row-disjoint. Model
selection cannot inspect final test labels. Benchmark does not modify checkpoints.
"""
from __future__ import annotations
import hashlib, json, math, random, statistics
from pathlib import Path
from tw8.arena import Learner, registry
from tw10.resource_meter import measured_evaluation

PROTOCOL = 'TW12_REAL_DATA_BENCHMARK_V1'


def _datasets():
    try:
        from sklearn.datasets import load_wine, load_breast_cancer
    except ImportError as e:
        raise RuntimeError('Optional benchmark dependency unavailable: pip install scikit-learn') from e
    wine=load_wine()
    cancer=load_breast_cancer()
    # Binary wine classes 0, 1; dataset features 0 and 9 (alcohol/color intensity).
    w=[(i,(float(r[0]), float(r[9])),int(y)) for i,(r,y) in enumerate(zip(wine.data,wine.target)) if y in (0,1)]
    # Wisconsin diagnostic dataset: classes benign/malignant, features mean radius/texture.
    c=[(i,(float(r[0]), float(r[1])),int(y)) for i,(r,y) in enumerate(zip(cancer.data,cancer.target))]
    return {'uci_wine_01':w, 'wisconsin_diagnostic':c}


def _split(rows, seed):
    buckets={0:[],1:[]}
    for row in rows:
        if row[2] not in buckets: raise ValueError('Nonbinary dataset')
        buckets[row[2]].append(row)
    train=[];selection=[];test=[]
    for cls,bucket in buckets.items():
        rng=random.Random(f'{PROTOCOL}/{seed}/{cls}')
        shuffled=list(bucket);rng.shuffle(shuffled)
        a=int(len(shuffled)*.6); b=int(len(shuffled)*.8)
        train.extend(shuffled[:a]);selection.extend(shuffled[a:b]);test.extend(shuffled[b:])
    ids=[set(x[0] for x in p) for p in (train,selection,test)]
    if not train or not selection or not test or (ids[0]&ids[1]) or (ids[0]&ids[2]) or (ids[1]&ids[2]):
        raise AssertionError('Non-disjoint data partitions')
    return train,selection,test


def _normalize(train,other):
    means=[statistics.fmean(row[1][j] for row in train) for j in (0,1)]
    scales=[math.sqrt(statistics.fmean((r[1][j]-means[j])**2 for r in train)) or 1.0 for j in (0,1)]
    def transform(rows):
        return [(((r[1][0]-means[0])/scales[0],(r[1][1]-means[1])/scales[1]),r[2]) for r in rows]
    return transform(train),transform(other)


@measured_evaluation
def evaluate(seed=314159, candidate_cap=24):
    if not (1 <= candidate_cap <= 100):raise ValueError('candidate_cap must be 1..100')
    families={}
    for candidate in registry():
        group=(candidate.family,candidate.update)
        families.setdefault(group,[]).append(candidate)
    # Cover all family/update cells; select fixed candidates BEFORE any challenge metrics.
    chosen=[]
    for group in sorted(families):
        chosen.extend(families[group][:max(1,candidate_cap//len(families))])
    chosen=chosen[:candidate_cap]
    output=[]
    for name,rows in _datasets().items():
        tr,sel,te=_split(rows,seed)
        train, select = _normalize(tr,sel)
        _, test = _normalize(tr,te)
        alternatives=[]
        for c in chosen:
            learner=Learner(c)
            for x,y in train:learner.update(x,y)
            alternatives.append((learner.accuracy(select),c.key,c,learner))
        # Winner only by selection fold, never by test labels.
        alternatives.sort(key=lambda t:(-t[0],t[1]))
        select_score,cid,candidate,learner=alternatives[0]
        negative=Learner(candidate)
        rng=random.Random(f'{PROTOCOL}/{name}/{seed}/negative')
        for x,_ in train:negative.update(x,rng.randint(0,1))
        test_accuracy=learner.accuracy(test)
        neg_accuracy=negative.accuracy(test)
        baseline=max(statistics.fmean(y for _,y in test),1-statistics.fmean(y for _,y in test))
        output.append({'dataset':name,'samples':len(rows),'train':len(train),'selection':len(select),'holdout':len(test),
                       'selected_candidate':cid,'family':candidate.family,'update':candidate.update,
                       'selection_accuracy':round(select_score,5),'holdout_accuracy':round(test_accuracy,5),
                       'holdout_majority_baseline':round(baseline,5),'holdout_random_label_control':round(neg_accuracy,5),
                       'sample_id_sha256':hashlib.sha256(','.join(map(str,sorted(x[0] for x in te))).encode()).hexdigest(),
                       'source':'scikit-learn bundled UCI Wine / Wisconsin breast-cancer; see sklearn.datasets descriptions',
                       'scope':'OFFLINE_PUBLIC_DATA_RESEARCH_NOT_CERTIFICATION'})
    return {'protocol':PROTOCOL,'seed':seed,'candidate_configurations_tested':len(chosen),
            'checkpoint_mutation':False,'certified_independent_ais':0,'mother_promotion':'LOCKED',
            'scientific_certification':False,'results':output}



def evaluate_repeated(seeds=(314159, 271828, 161803, 141421, 173205), candidate_cap=24):
    """Repeated held-out studies: selection is performed independently for each split.

    This is a research robustness probe, NOT an untouched final certification set.
    Reusing these splits to tune the approach would invalidate that claim.
    """
    if not seeds or len(seeds) != len(set(seeds)) or any(not isinstance(x,int) for x in seeds):
        raise ValueError('seeds must be a nonempty set of unique integers')
    if len(seeds) > 30:
        raise ValueError('at most 30 repeated seeds')
    studies=[evaluate(seed,candidate_cap) for seed in seeds]
    names=[r['dataset'] for r in studies[0]['results']]
    results=[]
    for name in names:
        entries=[next(x for x in run['results'] if x['dataset']==name) for run in studies]
        advantages=[x['holdout_accuracy']-x['holdout_majority_baseline'] for x in entries]
        negative_diffs=[x['holdout_accuracy']-x['holdout_random_label_control'] for x in entries]
        test_hashes=[x['sample_id_sha256'] for x in entries]
        results.append({
            'dataset':name,
            'seed_count':len(entries),
            'mean_holdout_accuracy':round(statistics.fmean(x['holdout_accuracy'] for x in entries),5),
            'min_holdout_accuracy':min(x['holdout_accuracy'] for x in entries),
            'max_holdout_accuracy':max(x['holdout_accuracy'] for x in entries),
            'mean_gain_vs_majority':round(statistics.fmean(advantages),5),
            'min_gain_vs_majority':round(min(advantages),5),
            'mean_gain_vs_random_labels':round(statistics.fmean(negative_diffs),5),
            'min_gain_vs_random_labels':round(min(negative_diffs),5),
            'selected_candidate_ids':sorted(set(x['selected_candidate'] for x in entries)),
            'different_holdout_splits':len(set(test_hashes)),
            'all_splits_beat_majority':all(x>0 for x in advantages),
            'all_splits_beat_random_labels':all(x>0 for x in negative_diffs),
            'per_seed':[{'seed':seed,'holdout_accuracy':e['holdout_accuracy'],
                         'baseline':e['holdout_majority_baseline'],
                         'negative':e['holdout_random_label_control'],
                         'candidate':e['selected_candidate'],
                         'holdout_sha256':e['sample_id_sha256']}
                        for seed,e in zip(seeds,entries)]
        })
    return {'protocol':'TW13_REPEATED_PUBLIC_DATA_RESEARCH_V1',
            'research_only':True, 'seeds':list(seeds),
            'candidate_configurations_per_split':candidate_cap,
            'checkpoint_mutation':False,'candidate_selection_uses_holdout':False,
            'certified_independent_ais':0,'mother_promotion':'LOCKED',
            'eligible_for_production':False,
            'warning':'Repeated public dataset splits are research evidence, not a sealed external certification set.',
            'results':results}

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=314159)
    parser.add_argument('--candidate-cap',type=int,default=24)
    parser.add_argument('--output',type=Path,default=Path('reports/real_benchmark.json'))
    a=parser.parse_args(argv)
    report=evaluate(a.seed,a.candidate_cap)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=a.output.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(a.output)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
