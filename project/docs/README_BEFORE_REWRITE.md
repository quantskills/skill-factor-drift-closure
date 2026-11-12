# 漂移预警触发降权或重训到底有没有净收益

本包对应官方任务 TS20261019645533，当前验收版本为v2。研究问题：冻结预测出现预警后，降权或重训相对不处理、固定降权及第三期PSI基线，是否有扣成本后的增量；换信号为同题扩展。仅声明1个官方题，平台成员重复申报尚需人工核对。

## 当前状态

- 两个监控技能及原平台ML技能均在 `.agents/skills/`，专供项目使用，无全局副本依赖。
- 真实健康入口已进入 `C_health/D_health/F_health` 的闭环；主实验每次重训均执行原平台来源CLI并与快速实现比对。
- 本地数据快照在 `data/`；来源、版本与SHA256见 `data/provenance.json`。技能GPL许可文件保留；输入数据可否对外分发尚需按原数据许可确认。
- 当前样本 20250103—20260911，4个相位、每相位22期。当前结果见 [report.md](report.md)、[dashboard.html](dashboard.html)。
- v1存在校准混入2025、漏卖出成本、尾端未知标签、RC统计量和恢复计数等问题，完整历史在 `archive/legacy_v1/`。根目录旧CSV只属历史，当前权威数据为 `results/v2/`。
- 本次属于看过历史数据后的纠错研究；配置 `config/audit_v2.json` 是修订分析计划，不是真正事前预注册。`config/preregistration.json` 仅为旧版历史声明。

## 一键复现

```powershell
& E:/envs/LLM/python.exe scripts/run_package.py
```

或使用安装了 `requirements.txt` 的 Python 3.11+：`python scripts/run_package.py`。运行器默认使用当前Python，遇到失败立即停止；记录每步输入、输出哈希、退出码及完整运行状态。会重跑监控、真实重训、50seed安慰剂、统计、报告、验收与清单。

查看已有包而不重训：`python scripts/run_package.py --only report verify manifest`。只跑部分步骤时日志明确 `full_run=false`，不能冒充全流程通过。

## 证据入口

- `runs/r01_monitor_entry/`：监控CLI输入、命令、stdout、输出，标签成熟映射。
- `runs/v2/refits/`：逐次平台来源ML CLI、压缩输入切片、OOS分数及等价校验。
- `results/v2/`：逐日期/相位交易、净收益、成本、事件、恢复删失、bootstrap和安慰剂。
- `verification/ACCEPTANCE_V2.json`：代码及数据验收；`TASK_CHECKLIST.md`：任务逐条对照。
- `ARTIFACTS.md`：产物索引；`manifest.json`：当前文件哈希。

不将本地CLI执行等同于QuantStudio GUI注册或平台任务提交。完整研究边界、修正原因与决策影响见报告。
