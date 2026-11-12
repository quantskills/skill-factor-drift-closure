# 输出契约

最小输出：

- `config.json`：冻结参数、时间边界、成本和动作定义；
- `arm_summary.csv`：基线、固定降权和动态动作的净收益、风险、换手和成本；
- `event_ledger.csv`：每个告警段的开始/结束、是否成熟、是否右删失、增量收益、误报成本和恢复延迟；
- `inference.json`：假设家族大小、bootstrap、BH、Reality Check 和 MDE；
- `run_record.json`：入口、版本、输入哈希、stdout/stderr、输出清单和状态；
- `decision.md`：改变了什么决策、作用多大、适用边界和负结果。

任何“有效”结论都必须同时提供点估计、区间、多重比较结果和样本边界。
