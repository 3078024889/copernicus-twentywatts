"""Pre-registered transfer safety experiment (synthetic tasks only).

Two learners see exactly the same current-task training examples.  A *selection*
probe decides whether to retain prior state or cold-restart; a disjoint *audit*
probe measures what that decision achieved. The audit labels NEVER choose a model.
This is a conservative anti-negative-transfer controller, not a winner certificate.
"""
from __future__ import annotations
from dataclasses import dataclass
from tw8.arena import Learner, dataset

PROTOCOL = 'TW11_TRANSFER_GUARD_V1'

@dataclass(frozen=True)
class GuardResult:
    selected: Learner
    action: str
    selection_continued: float
    selection_cold: float
    audit_continued: float
    audit_cold: float
    audit_selected: float
    def details(self):
        return {
            'protocol':PROTOCOL,'action':self.action,
            'selection_continued':self.selection_continued,
            'selection_cold':self.selection_cold,
            'audit_continued':self.audit_continued,
            'audit_cold':self.audit_cold,
            'audit_selected':self.audit_selected,
            'audit_gain_vs_cold':self.audit_selected-self.audit_cold,
            'certification':'NOT_ELIGIBLE_SYNTHETIC',
        }

def choose(continued: Learner, cold: Learner, *, seed: int, task: str, margin: float=0.0):
    if continued.c != cold.c:
        raise ValueError('Comparison requires identical algorithm configuration')
    if not 0 <= margin <= 0.5:
        raise ValueError('margin must be within [0,0.5]')
    # Separated deterministic seeds; deliberately never return selection labels.
    selection=dataset(seed+3100000,task,96)
    audit=dataset(seed+4300000,task,96)
    sc=continued.accuracy(selection)
    sn=cold.accuracy(selection)
    action='retain' if sc >= sn+margin else 'reset'
    selected=continued if action=='retain' else cold
    ac=continued.accuracy(audit)
    an=cold.accuracy(audit)
    return GuardResult(selected,action,sc,sn,ac,an,selected.accuracy(audit))
