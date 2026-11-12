# QuantStudio 选题要求自查与评分

本包按用户给出的四项评分维度自查。漂移入口消费项目内真实 drift CLI 输出，`warning` 才触发动作，`watch` 只记录；第三期 PSI 作为冻结基线，本期新增仅计算漂移闭环增量。

| 维度 | 得分 | 满分 | 依据 |
|---|---:|---:|---|
| 完成 | 27 | 30 | QuantStudio 会话已从项目路径执行完整管线并保存输入、输出与测试记录；任务页提交仍未执行。 |
| 方法 | 33 | 35 | 成熟度、训练隔离、交易成本、BH、循环块 bootstrap、Reality Check 和敏感性齐全；上游发布时间与真实成交尚未独立重建。 |
| 平台 | 20 | 25 | QuantStudio profile/session 与项目工作区、输入哈希、stdout、结果和 manifest 已记录；平台未暴露独立 run ID，GUI 注册/提交未执行。 |
| 文档 | 10 | 10 | README、完整报告、验收清单和本评分均说明目的、结果、分析、边界和证据入口。 |

**Q = 90/100；D = 1.00；V = 0.80；积分 = round(90×1.00×0.80) = 72。**

QuantStudio profile/session 已从项目工作区执行完整管线，并保存平台会话、输入哈希、命令、stdout、结果清单、单元测试和 manifest。平台没有向会话暴露独立 run ID，且未执行任务页提交或 GUI 注册；这些边界见 `docs/PLATFORM_EXECUTION_STATUS.md` 和 `runs/quantstudio_platform_entry/status.json`。

详细结果见 [report.md](../report.md)、[TASK_CHECKLIST.md](../TASK_CHECKLIST.md)、[results/v2/inference.json](../results/v2/inference.json) 和 [runs/_pipeline/run_log.json](../runs/_pipeline/run_log.json)。