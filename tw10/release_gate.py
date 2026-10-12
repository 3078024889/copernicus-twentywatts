"""Fail-closed production evidence gates; research never automatically promotes.

The report distinguishes *operational integrity* from *scientific certification*.
No synthetic research metric can satisfy real-world evidence requirements.
"""
from __future__ import annotations
import json,os
from pathlib import Path
from .operations import inspect

def assess(v8db, v9db, *, external_evidence=None):
    base=inspect(v8db,v9db)
    blockers=[]
    if base.get('source',{}).get('integrity')!='ok':
        blockers.append('V8_SOURCE_INTEGRITY')
    if base.get('continuity_integrity') not in (None,'ok'):
        blockers.append('LONGITUDINAL_DB_INTEGRITY')
    # This research pipeline has no audited external task adapter or scientific
    # winner certification pipeline. A JSON string from a caller cannot grant it.
    blockers.extend(['REAL_WORLD_HOLDOUT_NOT_VERIFIED',
                     'TWELVE_DISTINCT_ALGORITHMS_NOT_CERTIFIED',
                     'LONG_TERM_RETENTION_NOT_CERTIFIED',
                     'PRODUCTION_MIGRATION_NOT_VERIFIED'])
    return {'protocol':'TW11_RELEASE_GATE_V1','operational_integrity':
            base['source']['integrity']=='ok' and base.get('continuity_integrity','ok')=='ok',
            'eligible_for_production':False,'certified_independent_ais':0,
            'mother_promotion':'LOCKED','blockers':blockers,
            'evidence_scope':'SYNTHETIC_RESEARCH_ONLY'}
