# TW40 — Fixed Replay Budget; Prospective Evolution Validation

Date: 2026-10-12. Research only, synthetic tasks, not a certified AI system.

## Source-first constraint
《哥白尼》是研究目标的叙事参考：神经节点连接、记忆、自学习；大量学习算法变异体参加逐层知识挑战；后期出现改进学习算法的能力。原作没有给出固定回放公式。这次的固定回放制度是工程实验控制，不是小说原文。

## Root cause corrected
TW39 evaluated proposed mutations with differing actual replay updates. A preselection update-count check allowed individual proposals to be comparable, but inherited memory diverged between lineage arms over generations. Therefore only 65/96 past trajectories passed accumulated-budget comparison. TW40 uses a precommitted fixed replay update every fifth new sample for *all* memory configurations, including none-memory baselines (replays current sample), while allowing other memory policies to choose a stored example. This matches number of update operations, not CPU time, RAM or effective sample information. Default/native learner behavior is preserved outside TW40.

Protocol `TW40_FIXED_REPLAY_BUDGET_V1` is separated from TW39 evidence in new SQLite database. Selection-only historical priors; sealed audits are generated only after mutation selection.

## Tests and experiments
171/171 regression tests PASS. Fixed replay 48 learning events => 57 model updates independent of memory operator. Four generation prospective trials × 2 disjoint seed batches × 48 trials; 96/96 met update-count eligibility; 96 persisted rows and SQLite `integrity_check=ok`; rerun of first batch inserted 0 new rows and preserved summary results.

| Batch | Eligible | New task transfer: meta minus random (pp) | Bootstrap 95% (pp) | Old knowledge retention: meta minus random (pp) | Bootstrap 95% (pp) |
|---|---:|---:|---|---:|---|
| 53000–53047 | 48/48 | +0.40148 | [-0.49913, +1.46484] | -1.06337 | [-2.60417, +0.05425] |
| 54000–54047 | 48/48 | +1.13932 | [-0.05425, +2.57161] | -2.24609 | [-5.02387, -0.11936] |

Conclusion: Budget comparability improved, **no certified learning advantage**; second cohort shows retention loss. **0/12** certified. It is incorrect to interpret increased eligible count as improved intelligence.

## Remaining controls
CPU time, peak RAM, energy, model-specific replay information, equivalence of the real Mother, statistical control for 7777 candidate comparisons, and genuinely unseen task-family transfer all remain unverified. Do not promote meta arm. The research code is not deployed to Windows `28723` and not pushed to GitHub `main`.
