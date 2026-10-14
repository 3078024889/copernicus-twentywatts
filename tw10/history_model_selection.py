"""TW37: train-only selection of a shrinkage predictor for mutation gains.

Historical selection rewards, NOT sealed task audits. Strict seed separation.
This retrospective experiment cannot establish on-policy evolutionary advantage.
"""
from __future__ import annotations
import json
import statistics
from .meta_prediction_audit import read_trials,examples,_fit,predict

PROTOCOL='TW37_TRAIN_ONLY_META_MODEL_SELECTION_V1'

def _mae(records,model,scale):
    return statistics.fmean(abs(scale*predict(model,d,f)-gain) for _,d,f,gain in examples(records))

def compare(train,holdout):
    if not train or not holdout:raise ValueError('both training and holdout are required')
    train_ids={r['seed'] for r in train};test_ids={r['seed'] for r in holdout}
    if train_ids & test_ids:raise ValueError('seed overlap')
    ids=sorted(train_ids)
    if len(ids)<4:raise ValueError('too few historical seeds for internal validation')
    # Deterministic inner split, using only the historical cohort.
    inner_train=[r for r in train if r['seed'] in set(ids[::2])]
    inner_valid=[r for r in train if r['seed'] not in set(ids[::2])]
    model_inner=_fit(examples(inner_train))
    candidates=(0.0,0.25,0.5,1.0)
    training_errors={str(w):_mae(inner_valid,model_inner,w) for w in candidates}
    weight=min(candidates,key=lambda w:(training_errors[str(w)],w))
    model=_fit(examples(train));hold=examples(holdout)
    def error(w):return statistics.fmean(abs(w*predict(model,d,f)-gain) for _,d,f,gain in hold)
    return {'protocol':PROTOCOL,'train_seeds':len(train_ids),'holdout_seeds':len(test_ids),
            'train_only_inner_validation':True,'inner_validation_mae':training_errors,
            'selected_shrinkage':weight,'holdout_mae_selected':round(error(weight),9),
            'holdout_mae_zero':round(error(0),9),
            'holdout_mae_unshrunk':round(error(1),9),
            'holdout_improvement_vs_zero':round(error(0)-error(weight),9),
            'certified_predictive_advantage':False,
            'limitations':'Retrospective selection feedback, not unseen task-family or deployed causal benefit.'}

def run(path,report=None):
    train=read_trials(path,15500,15572);held=read_trials(path,25500,25572)
    result=compare(train,held)
    if report:
        from pathlib import Path
        p=Path(report);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
