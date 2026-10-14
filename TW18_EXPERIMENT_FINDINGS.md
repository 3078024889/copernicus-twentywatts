# TW18 architecture audit — 2026-10-12

*Four distinct mechanisms* (versus 7777 hyperparameterized candidates): linear logistic SGD, interaction-feature logistic SGD, online Gaussian naive Bayes, bounded sample-memory k-NN.

Protocol `TW18_ARCHITECTURE_PAIRED_V1`; synthetic task sequence linear → interaction → shift → linear; 12 common held-out random seeds 201–212; 48 architecture/seed trajectories; four stages each. Results in `reports/architecture_audit.json`; evidence persisted separately at `data/architecture_audit.sqlite`.

| Architecture | linear accuracy | interaction accuracy | shift accuracy | return accuracy | mean transfer vs cold |
|---|---:|---:|---:|---:|---:|
| linear_sgd | 94.73% | 52.73% | 90.89% | 94.08% | +1.25 pp |
| interaction_sgd | 94.86% | 58.40% | 93.16% | 91.73% | -1.06 pp |
| gaussian_nb | 91.28% | 55.27% | 82.88% | 95.51% | -1.48 pp |
| bounded_knn | 95.83% | 92.06% | 94.73% | 94.53% | 0.00 pp |

**Interpretation:** k-NN has an advantage on this synthetic nonlinear manifold but has higher inference complexity. It is not evidence of autonomous code invention, broad knowledge discovery, or production certification. Fixed tasks and repeated synthetic distributions should not be used to allocate the 12 final independent AI seats. All promotion remains LOCKED.

**Integration:** `python -m tw10.cli architecture-audit --architecture-seeds 12`. The implementation and five new tests are in the unified code tree; 63/63 tests currently pass in the isolated environment. The current GitHub integration cannot write (403), and container DNS access to github.com is unavailable. Use the included Windows source-only sync script after local verification; it blocks push on test failures and excludes evidence databases and model artifacts.
