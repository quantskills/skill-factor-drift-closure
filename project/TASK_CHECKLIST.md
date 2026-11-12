# v2 任务验收清单

这张表是审计索引，不是项目摘要。项目的目的、问题、结果和研究决策请先读 [README.md](README.md) 和 [report.md](report.md)。

“研究完成”指本地数据、代码、统计和证据链已经完成；“平台 GUI 未验证”单独列出，不能把本地 CLI 运行记录写成 QuantStudio 注册、调度或提交。

本包对应任务 `TS20261019645533`，仅声明一个官方选题。题目名额、每周申报上限及跨平台重复申报，需要以平台记录人工核对，本地验收不能替代。

| 任务要求 | 当前状态 | 证据 |
|---|---|---|
| QuantStudio 平台真实入口及输入输出 | **已完成会话执行与留痕**：QuantStudio profile/session 已运行本项目并保存输入、输出、测试和 manifest；平台未暴露独立 run ID，任务页提交/GUI 注册未执行 | `runs/quantstudio_platform_entry/status.json`、`platform_entry_record.json`、`docs/PLATFORM_EXECUTION_STATUS.md` |
| 不处理、固定降权和动态处置对照 | 已完成历史回看；属于回顾性修订 | `results/v2/trades.csv`、`metrics.json` |
| 冻结因子与预测 | 54 个因子沿用存档分数，不重新选择 | `data/provenance.json`、`backtest_audit.json` |
| 当时可见成熟标签 | 标签后移 5 个观测；重训 gap=6 | `label_availability.csv`、`runs/v2/refits/*/input.json` |
| 交易成本 | 买卖全并集、持仓漂移、借券费均计入 | `cost_decomposition.csv`、`tests/test_engine_v2.py` |
| 误报成本 | 按事件处置净盈亏记录，含未暴露和右删失 | `false_alarm.csv`、`episodes.csv` |
| 恢复延迟 | 已恢复与右删失分开报告 | `recovery.json` |
| 第三期基线 | 使用同一交易引擎比较 PSI 基线与动态动作 | `trades.csv`、`cost_decomposition.csv` |
| 统计可靠性 | 24 个假设、BH、循环块 bootstrap、Reality Check、50 seed 安慰剂 | `multiplicity.csv`、`inference.json`、`placebo.csv` |
| 本期漂移闭环增量 | drift CLI 的 `warning` 状态触发半仓、重训、换信号；`watch` 不触发 | `monitor.csv`、`metrics.json`、`false_alarm.csv`、`recovery.json` |
| 敏感性与适用边界 | 缺失标签和 27 组健康参数扰动均已报告 | `missing_return_sensitivity.json`、`health_robustness.json` |
| 本地运行完整性 | 本地完整 pipeline 为 `all_ok=true` 且 `full_run=true`；不等于平台完成 | `runs/_pipeline/run_log.json` |
| 每题限 1 人、每周最多 3 项 | 本包仅声明 1 个题；平台名额和跨任务去重未核验 | 需人工核对 QuantStudio 平台记录 |
