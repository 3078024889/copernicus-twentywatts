"""Paired, protocol-isolated backtest of predeclared error diagnosis.

Does not use sealed scores to select mutations. Reports paired uncertainty,
resource-accounting limits, and refuses to automatically promote variants.
"""
import statistics
from pathlib import Path
from .twin_evolution import study
from .twin_backtest import bootstrap_interval, save

def run(seeds=range(24), generations=4, proposals=3, db=None):
    ids=list(seeds)
    if len(ids)<2 or len(ids)!=len(set(ids)):
        raise ValueError('need independent unique paired seeds')
    baseline=study(ids,generations,proposals,db=db,selection_policy='cross_domain')
    diagnosis=study(ids,generations,proposals,db=db,selection_policy='diagnostic')
    reference={r['seed']:r for r in baseline['details']}
    paired=[]
    for d in diagnosis['details']:
        b=reference[d['seed']]
        bt=b['generations'][-1];dt=d['generations'][-1]
        paired.append({'seed':d['seed'],
                       'transfer':round(dt['sealed_transfer_delta']-bt['sealed_transfer_delta'],8),
                       'retention':round(dt['sealed_retention_delta']-bt['sealed_retention_delta'],8),
                       'accepted_diagnostic_mutations':d['selected_mutations'],
                       'diagnoses':[g['failure_diagnosis'] for g in d['generations']]})
    differences_t=[p['transfer'] for p in paired]
    differences_r=[p['retention'] for p in paired]
    # Both arms use identical selection sets and proposal count: better control
    # than old vs cross-domain policy comparison. Runtime / FLOPs not equated.
    budget_match=all(d['fixed_updates']==d['adaptive_updates'] and
                     d['search_updates']['fixed']==d['search_updates']['adaptive'] and
                     d['selection_predictions']['fixed']==d['selection_predictions']['adaptive']
                     for d in diagnosis['details'])
    cross_budget_match=all(d['selection_predictions']==reference[d['seed']]['selection_predictions']
                           and d['search_updates']==reference[d['seed']]['search_updates']
                           for d in diagnosis['details'])
    return {'protocol':'TW27_DIAGNOSTIC_VS_CROSS_PAIRED_V1',
            'seeds':len(ids),'generations':generations,
            'same_train_and_sealed_rows':True,'same_probe_and_update_counts':budget_match and cross_budget_match,
            'mean_transfer_difference':round(statistics.fmean(differences_t),6),
            'mean_retention_difference':round(statistics.fmean(differences_r),6),
            'transfer_95_bootstrap':bootstrap_interval(differences_t,seed=2701),
            'retention_95_bootstrap':bootstrap_interval(differences_r,seed=2702),
            'positive_transfer_seeds':sum(x>0 for x in differences_t),
            'negative_retention_seeds':sum(x<0 for x in differences_r),
            'selected_diagnostic_mutations':sum(d['selected_mutations'] for d in diagnosis['details']),
            'promotion':'BLOCKED_PENDING_INDEPENDENT_TRANSFER_AND_BUDGET_PROOF',
            'mother':'FROZEN_EXPERIMENTAL_PROXY_NOT_REAL_V3_MOTHER',
            'scope':'SYNTHETIC_EXPLORATION_ONLY', 'certified_ais':0, 'paired':paired}
