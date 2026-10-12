# TwentyWatts V8 | 7777 → 12 Learning Competition (Research)

Goal: register 7,777 **algorithm configurations**, test real weight changes, compare with a label-shuffled negative control, reserve unseen-seed verification, and nominate **up to 12** distinct qualified learners. It must never manufacture 12 winners.

## Verified result (2026-10-12)
- 7,777 unique configurations, from 2 actually implemented structural families × 2 update rules × 45 learning rates × 44 regularization settings; first 7,777 of 7,920 deterministic combinations.
- 31,108 paired preliminary experiments (2 seeds × 2 task families for each of 7,777).
- 60 shortlisted configs; 1,800 independent holdout trials (10 seeds × 3 tasks).
- 1 **provisional research seat** under current exploratory gates; **zero independently certified AIs**.
- Algorithm distinction remains underdetermined: 7,777 parameterizations are **not** 7,777 fundamentally independent algorithm inventions.
- Any claim of 12 winners requires future diverse models, real datasets, disjoint test corpora, independent replication, robust statistical testing, and human approval.

## Design
- Candidate IDs G0001–G7777; persistent registry. Same data is used for matched comparisons.
- Training induces actual parameter changes; there is an identical-feature randomized-label negative control.
- Holdout seeds (101–110) never enter preliminary screening (1–2).
- Distinct-family/update grouping prevents near-identical parameter variations from taking 12 seats.
- All seats are `PROVISIONAL_RESEARCH_ONLY`; no deploy, Mother promotion, Oracle integration or V3 changes.
- Uses Python standard library and SQLite, no cloud or third-party runtime.

## Run
```powershell
cd TWENTYWATTS_V8_7777_TO_12
py -3 -m unittest discover -s tests -v
py -3 -m tw8.arena --db data/tw8.sqlite --output reports/competition.json
```
Runs are idempotent; existing records are not duplicated. Run using an isolated directory, not the V3 live folder. The SQLite file is a research checkpoint, not production telemetry.

## Next gate to truly produce 12 independent learners
Implement and separately validate at least 12 meaningfully different architectures/training methods, including online linear and nonlinear learners, prototype/memory learners, replay-based continual learning, contextual predictors, bandit learners and symbolic hypothesis learners. Validate on at least three non-synthetic task domains, balanced compute budget, pre-registered acceptance thresholds, blinded holdouts, multiple-seed confidence intervals and behavior fingerprints. Admit only those that pass; remain below 12 if insufficient.
