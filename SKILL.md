---
name: skill-factor-drift-closure
description: Evaluate whether a factor-drift alert creates net value after the response action. Use for out-of-sample comparisons of no action, fixed de-risking, alert-triggered downweighting, retraining or signal switching, including false-alarm cost and recovery latency.
license: GPL-3.0-only
metadata:
  quantSkills:
    schema_version: 2.0.0
    organization: quantskills
    organization_url: https://github.com/quantskills
    repository: skill-factor-drift-closure
    repository_url: https://github.com/quantskills/skill-factor-drift-closure
    project_type: skill
    maintainer_type: community
    collection: factor-quality
    workflow: {primary_stage: evaluation, workflow_stages: [evaluation, audit]}
    tags: [factor-drift, closed-loop, false-alarm, recovery-latency, out-of-sample]
    summary_zh: 检验因子漂移预警后的降权、重训或换信号是否产生扣成本后的样本外增量。
    summary_en: Out-of-sample evaluation of net value after factor-drift response actions.
    status: community-project
    validation_level: runnable
    platforms: [cursor, claude-code, codex, hermes, openclaw]
    interface: {mode: file-based, inputs: [panel, alert-ledger, config], outputs: [arm-summary, event-ledger, inference, decision-report]}
---

# 漂移预警闭环评估

这个 Skill 检验“发现漂移以后采取动作是否真的有净收益”，而不是重复生成 PSI、KS 或 CUSUM 仪表盘。它把冻结预测、已成熟标签、交易成本、预警时点和处置动作放到同一套样本外对照中。

## 必须遵守的边界

1. 预测、因子和模型参数先冻结；测试期不能重新选参数。
2. 标签必须达到成熟门槛后才能进入预警，预警不能偷看未来收益。
3. 训练窗口、purge、embargo、持有期和交易成本必须显式记录。
4. 至少包含冻结基线、固定降权和漂移触发动作；固定降权用于识别机械暴露效应。
5. 单独记录误报成本、恢复延迟、右删失事件和未暴露事件。
6. 负结果可以是有效交付；不能把点估计写成普适收益。
7. 输出仅供量化研究、教育和方法论参考，不构成投资建议或交易授权。

## 标准流程

1. 读取 `references/data-contract.md`，核对面板、预测、成熟标签、成本和预警字段。
2. 固定校准期，只用当时可见信息生成阈值和动作规则。
3. 在测试期运行冻结基线、固定降权和漂移触发动作；必要时增加始终降权安慰剂。
4. 统一核算买入、卖出、持仓漂移、借券费、初始权益和回撤。
5. 生成事件表：告警开始/结束、是否成熟、是否误报、净增量、成本和恢复观测数。
6. 对完整假设家族做 bootstrap、BH 和 Reality Check；报告 MDE 与敏感性。
7. 输出决策清单、适用边界、平台运行记录和可复现命令。

## QuantStudio 运行要求

如果任务指定 QuantStudio，必须从 QuantStudio 真实入口执行，并保存 session/workspace、输入哈希、命令、stdout/stderr、结果文件和 manifest。EVO、普通本地 CLI 或未绑定平台的回测不能替代 QuantStudio 证据。

## 相关技能

- 漂移测量：<https://github.com/quantskills/skill-factor-drift-monitor>
- 因子健康度：<https://github.com/quantskills/skill-factor-health-monitor>
- 本 Skill 只消费它们产生的预警，不重复它们的仪表盘实现。
