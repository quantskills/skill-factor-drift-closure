# skill-factor-drift-closure

简体中文 | [English](README.en.md)

**漂移预警闭环评估 Skill**：比较“不处理、固定降权、漂移触发降权/重训/换信号”的样本外净结果，量化误报成本和恢复延迟。

## 它解决什么问题

很多项目能计算漂移指标，却没有验证报警之后的动作是否值得。这个 Skill 将监控输出接到交易或研究决策，专门回答：报警是否有独立信息量、降暴露是否只是机械效果、重训是否增加不稳定性、以及误报和恢复延迟的代价。

## 快速开始

```powershell
python scripts/closed_loop_evaluation.py --panel data/panel.csv --alerts data/alerts.csv --output outputs/closure
```

运行前先阅读 `SKILL.md`、`references/data-contract.md` 和 `references/output-contract.md`。脚本只提供审计骨架；策略动作、标签成熟度和成本假设必须在输入配置中明确写出。

## QuantStudio

任务若要求 QuantStudio，必须保存真实平台入口的 session/workspace、输入和输出记录。EVO 页面、普通本地运行和未绑定平台的 CLI 不能作为替代证据。

## 许可与边界

本项目采用 GPL-3.0-only。不附带市场数据，也不包含任何凭据。所有结果都是历史数据和假设条件下的研究证据，不代表未来表现。

## 项目实现代码

完整项目实现位于 [`project/`](project/)，包括 `engine_v2.py` 闭环回测引擎、监控入口、重训与统计分析、报告生成、验收脚本、回归测试、冻结配置、QuantStudio 运行证据和紧凑结果快照。原始市场面板、滚动重训中间文件和凭据不随 Skill 发布；按 `project/DATA_CONTRACT.md` 提供本地授权数据即可复现。

```powershell
cd project
python -m unittest discover -s tests -v
python scripts/run_package.py
```
