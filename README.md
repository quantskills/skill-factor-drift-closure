# skill-factor-drift-closure

简体中文 | [English](README.en.md)

> QuantSkills `skill-*` 项目：评估因子漂移预警后的降权、重训或换信号是否产生扣除交易成本后的样本外增量。

[![QuantSkills](https://img.shields.io/badge/QuantSkills-skill--factor--drift--closure-5b6ee1)](https://github.com/quantskills/skill-factor-drift-closure)
[![许可证](https://img.shields.io/badge/license-GPL--3.0--only-blue)](LICENSE)

## 项目概览

很多量化项目可以计算 PSI、KS、CUSUM、IC 或健康概率，却没有回答更重要的决策问题：**出现预警之后，采取什么动作，扣除换手和交易成本后是否真的比冻结基线更有价值？**

本项目将预警、处置动作、成熟标签、模型训练边界、交易成本、误报成本和恢复延迟放在同一套样本外评估中，比较以下方案：

- 不处理：继续使用冻结预测；
- 固定降权：全评估期固定降低暴露，用来识别机械风险缩减效果；
- 预警后降权：仅在预警期间降低暴露；
- 预警后重训：告警段开始时使用当时可见且已成熟的数据重新拟合；
- 预警后换信号：在告警期间切换到预先指定的备选信号；
- 始终换信号和随机时点对照：判断改善是否只是信号本身或动作时点的结果。

本仓库同时包含可复用的 Skill 声明和该项目的完整实现代码。根目录 `SKILL.md` 是 Skill 声明；`project/` 是可执行的研究实现、测试、配置、结果快照和 QuantStudio 证据包。

## 当前研究结论

项目当前是一个**回顾性纠错研究**，不是前瞻注册，也不是交易授权。使用 2024 年校准、2025 年起的评估窗口和至少 5 个周度观测的成熟标签门槛，收益标签持有 4 个周度观测后才可用于预警。

主要描述性结果如下，收益已扣交易费和借券费：

| 方案 | 多头累计净收益 | 对冲累计净收益 |
| --- | ---: | ---: |
| 不处理 Ridge | +23.65% | -9.79% |
| 固定半仓 | +12.16% | -4.81% |
| 成熟 IC → 重训 | +28.68% | -5.92% |
| 成熟 IC → 换信号 | +31.59% | -5.13% |
| 漂移入口 → 重训 | +35.28% | -1.95% |
| 健康入口 → 换信号 | +30.85% | -5.90% |

这些数字是历史样本中的描述性结果，不能直接解释为未来收益。24 个假设经多重比较后，保守 BH 最小值为 `0.5679`，BH ≤ 0.10 的结果数为 0；循环块 Reality Check 正向 p 值为 `0.3803`。因此本项目没有把某个动态动作宣布为稳定最优策略。

当前研究决策是保留监控和审计链路，继续做纸面验证，暂不自动下单；先解决缺失收益标签、上游发布时间、真实成交和参数稳定性问题。

## 适用场景

本 Skill 适用于：

- 因子漂移预警后的闭环处置评估；
- 因子健康恶化后的固定降权、动态降权和重训比较；
- 误报成本、恢复延迟、右删失事件和未暴露事件记录；
- 冻结模型与滚动重训的泄漏审计；
- 需要保留输入、输出、哈希、命令和清单的 QuantStudio 研究复现；
- 量化研究组件、报告复现工具和研究决策审计。

本 Skill 只消费上游漂移和健康监控产生的预警，不重新实现 PSI、KS、CUSUM 等监控仪表盘。相关上游组件见：

- [skill-factor-drift-monitor](https://github.com/quantskills/skill-factor-drift-monitor)
- [skill-factor-health-monitor](https://github.com/quantskills/skill-factor-health-monitor)

## 运行时入口

本项目按 [QuantSkills skill-template](https://github.com/quantskills/skill-template) 的 catalog-contract v2 组织：

| 运行时 | 入口或适配文件 |
| --- | --- |
| Codex | `SKILL.md` |
| Claude Code | `SKILL.md` |
| Cursor | `agents/cursor-rule.mdc` → `SKILL.md` |
| Hermes | `agents/portable-loader.md` → `SKILL.md` |
| OpenClaw | `agents/openai.yaml` → `SKILL.md` |
| 项目执行 | `project/scripts/run_package.py` |
| QuantStudio | `project/runs/quantstudio_platform_entry/` 中的真实入口证据 |

## 快速开始

### 1. 仅检查 Skill 输入形状

该适配器记录输入文件哈希和字段结构，不会假装完成完整回测：

```powershell
python scripts/closed_loop_evaluation.py `
  --panel data/panel.csv `
  --alerts data/alerts.csv `
  --output outputs/closure
```

### 2. 运行项目实现

进入 `project/` 后执行：

```powershell
cd project
python -m unittest discover -s tests -v
python scripts/run_package.py
```

项目要求 Python 3.11+，依赖见 `project/requirements.txt` 和 `project/requirements-lock.txt`。原项目的可复现解释器为 `E:/envs/LLM/python.exe`：

```powershell
cd project
& E:/envs/LLM/python.exe -m unittest discover -s tests -v
& E:/envs/LLM/python.exe scripts/run_package.py
```

如果只运行部分步骤，流水线必须保留 `full_run=false`，不能把部分结果改写成完整成功。

### 3. 准备输入数据

原始市场面板和模型文件不随本仓库发布。请按照 [`project/DATA_CONTRACT.md`](project/DATA_CONTRACT.md) 提供经过授权的本地快照，并保存：

- `(date, symbol)` 唯一键；
- 冻结预测和因子列；
- 当时可见的成熟标签；
- 交易成本、借券费和可交易过滤；
- 预警状态和动作账本；
- 数据来源、时间范围、文件大小和 SHA256。

不要根据未来收益是否缺失来筛选选股池；缺失标签必须按配置显式处理，并进行敏感性分析。

## 代码和结果目录

```text
.
├── SKILL.md                         # 根目录 Skill 声明和 QuantSkills 元数据
├── catalog.yaml                     # catalog-contract v2 清单
├── agents/                          # 各运行时的薄适配入口
├── references/                      # 数据、输出和来源边界约定
├── scripts/closed_loop_evaluation.py# 输入形状与哈希审计骨架
├── project/                         # 完整项目实现
│   ├── scripts/                     # 引擎、监控、重训、分析、报告和验收
│   ├── config/                      # 冻结分析计划和模型配置
│   ├── tests/                       # 泄漏、核算、边界和统计回归测试
│   ├── results/v2/                  # 紧凑结果快照
│   ├── runs/_pipeline/              # 每个步骤的命令、输入、日志和状态
│   └── runs/quantstudio_platform_entry/ # QuantStudio 真实入口证据
├── README.md                        # 本文件
├── README.en.md                     # 英文说明
└── LICENSE                           # GPL-3.0-only
```

核心实现包括：

- `project/scripts/engine_v2.py`：成熟标签门槛、滚动训练隔离、四相位账户、买卖和权重漂移换手、交易成本、回撤、动作臂和右删失事件；
- `project/scripts/run_monitor_entries.py`：调用项目内漂移和健康 Skill，并记录入口哈希、输入哈希和输出；
- `project/scripts/analyze_v2.py`：IID 与循环块 bootstrap、BH 多重比较和 White-style Reality Check；
- `project/scripts/health_robustness_v2.py`：健康参数扰动和稳定性报告；
- `project/scripts/report_v2.py`：结果报告和可视化页面；
- `project/scripts/verify_v2.py`、`project/scripts/self_audit.py`：验收检查和选题要求评分；
- `project/scripts/run_package.py`：可复现流水线入口，失败时保留失败状态。

## QuantStudio 真实入口证据

用户要求运行平台必须是 QuantStudio。本项目已从 QuantStudio 的 `quantstudio` profile/session、项目路径 `E:\period5_package\period5_package` 执行，并留下输入与输出记录。证据位于 [`project/runs/quantstudio_platform_entry/`](project/runs/quantstudio_platform_entry/)：

- `platform_entry_record.json`：会话、项目路径、输入文件哈希、命令、输出清单和输出哈希；
- `QUANTSTUDIO_EVIDENCE.md`：平台入口说明和执行摘要；
- `_entry_console.log`：完整流水线日志；
- `_unittest_console.log`：11 项回归测试日志；
- `status.json`：平台验证、`full_run`、Q/D/V 和 manifest 状态；
- `runs/_pipeline/`：各流水线步骤的 `cmd.txt`、`input.json`、`stdout.log` 和 `status.json`。

已记录的结果是：完整管线 `all_ok=true`、`full_run=true`，验收 77 项通过，回归测试 11 项通过，`Q=90`、`D=1.00`、`V=0.80`、积分 72。QuantStudio 没有暴露独立 run ID，也没有执行任务页 GUI 注册或外部提交，因此只能声称“已从 QuantStudio 真实入口执行并留痕”，不能声称“任务页已提交”。EVO 页面不作为本项目的平台证据。

## 方法边界和重要限制

本项目遵守以下研究边界：

1. 冻结因子、预测和模型参数，测试期不重新挑选策略参数；
2. 标签达到成熟门槛后才可参与预警，重训不读取测试期标签；
3. 保留不处理、固定降权和漂移触发动作，区分机械风险缩减和预警时机价值；
4. 买入、卖出、持仓漂移、借券费、初始权益和回撤统一核算；
5. 记录误报成本、恢复延迟、右删失和未暴露事件；
6. 保留完整假设家族并进行 bootstrap、BH、Reality Check 和 MDE 分析；
7. 2026 年样本已经被查看，本研究不能将其描述为未见确认集；
8. 缺失收益、冲击成本、借券可得性、真实成交和上游因子发布时间仍有未建模部分。

结果仅供量化研究、教育和方法论参考，不构成投资建议、交易授权或收益承诺。

## 验收与研究报告

- [完整研究报告](project/report.md)
- [任务要求清单](project/TASK_CHECKLIST.md)
- [自查评分](project/docs/SELF_AUDIT_SCORE.md)
- [平台执行状态](project/docs/PLATFORM_EXECUTION_STATUS.md)
- [数据契约](project/DATA_CONTRACT.md)
- [统计结果](project/results/v2/inference.json)
- [验收结果](project/verification/ACCEPTANCE_V2.json)

## 来源、许可证与贡献

本项目采用 `GPL-3.0-only`，见 [LICENSE](LICENSE)。项目内复制的上游监控 Skill 保留各自许可证和来源边界；改编上游策略、论文、数据或代码时，应在对应文件中注明来源并保留许可证要求。

请勿提交密钥、令牌、私人数据、机密材料、原始市场数据或本地会话凭据。提交代码或结果时，请同时说明数据来源、参数、假设、已知限制和是否来自 QuantStudio 真实入口。

QuantSkills 的最终收录、推荐、验证和官方认可由组织维护者审核。本仓库当前为 Private，社区规范符合性不等于官方收录。
