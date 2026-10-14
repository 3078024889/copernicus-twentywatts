# TW27 | 错误诊断驱动的树突学习规则变异：配对回测

## 工程实现

新增 `tw10/twin_diagnostic_backtest.py`、`tests/test_twin_diagnostic.py`，在 `tw10/twin_evolution.py` 添加诊断模式，在 `tw10/cli.py` 添加 `twin-diagnostic` 命令。研究协议 `TW27_TWIN_DIAGNOSTIC_SELECTION_V1` 与旧 `TW26_TWIN_CROSS_DOMAIN_SELECTION_V1` 独立存证，采用相同随机种子、训练题、密封审计题、三套选择集、训练和选择探针调用次数。

错误诊断只使用选择集数据：`memory_interference`、`transfer_failure`、`prediction_error`、`stability`，定向生成元学习、分支整合、局部可塑性算子的候选变异。不会使用最终密封审计集挑选规则。注意：诊断目前是预先定义的启发式规则，不是经过独立验证的真正因果错误诊断。

## 96 种子 × 4 代实际结果

- 协议：`TW27_DIAGNOSTIC_VS_CROSS_PAIRED_V1`
- 已选择的诊断变异：151 次
- 最终密封迁移相对旧策略：+0.004449（+0.4449 个百分点）
- 配对 bootstrap 95% 区间：[-0.007487, 0.016819]
- 最终密封旧任务保持相对旧策略：-0.009657（-0.9657 个百分点）
- 配对 bootstrap 95% 区间：[-0.028212, 0.007812]
- 严格配对的训练、搜索更新与预测计数：通过；CPU 时间/内存/FLOPs 尚未匹配
- SQLite: 192 条（两协议各 96 条）；完整性 `ok`
- **认证：0/12；不升级默认规则**。

结果为合成任务研究，Mother 为冻结代理，非 Windows V3 真实 Mother；还需真实知识库、可证伪的机制诊断、盲测和长期预算测量。
