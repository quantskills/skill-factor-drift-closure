# QuantStudio 项目交付包说明

本压缩包对应 QuantStudio 任务 `TS20261019645533`：“漂移预警触发降权或重训到底有没有净收益”。研究目标是比较冻结基线、不处理、固定降权、漂移触发降权/重训/换信号，并量化误报成本和恢复延迟；重点验证预警后的处置闭环增量，不重复第三期 PSI、KS、CUSUM 仪表盘。

## 已满足的要求

- 运行平台：QuantStudio。项目已从 QuantStudio `quantstudio` profile/session 真实入口执行。
- 输入与输出留痕：会话 ID、项目路径、输入配置哈希、命令、stdout、输出清单、测试和 manifest 保存在 `runs/quantstudio_platform_entry/`。
- 数据边界：冻结因子/模型预测、当时可见成熟标签、5 周成熟度、4 周持有期、2024 校准、全换手、交易成本、初始权益回撤、右删失告警和全假设家族均保留。
- 训练隔离：重训不使用测试期；平台运行完成 `all_ok=true`、`full_run=true`。
- 文档：`README.md`、`report.md`、`TASK_CHECKLIST.md` 和 `docs/SELF_AUDIT_SCORE.md` 说明目的、解决的问题、结果、分析、边界和证据入口。
- 客观评分：完成 27/30，方法 33/35，平台 20/25，文档 10/10；`Q=90`，`D=1.00`，`V=0.80`，积分 `72`。
- 包清单：`manifest.json` 记录最终 606 个文件及 SHA256。
- 压缩包不包含 `.git`、Python 缓存目录；QuantStudio 的外部会话归档保留路径与哈希引用，不复制凭据或外部会话原始压缩文件。

## 主要结论

漂移触发的降权、重训和换信号在样本中有方向性差异，但 BH 和 Reality Check 没有给出稳定显著的普适增量。固定风险缩减有时已解释大部分改善；因此监控保留为诊断和研究线索，暂不自动下单。负结果和适用边界详见 `report.md`。

## 真实平台证据

先看 `runs/quantstudio_platform_entry/QUANTSTUDIO_EVIDENCE.md` 和 `platform_entry_record.json`。EVO 页面和任何 `triple_factor_trend` 草稿都不属于本包证据。QuantStudio 未暴露独立 run ID，且未执行任务页提交/GUI 注册；这两个边界在所有报告中单独标注。

## 复现

```powershell
& E:/envs/LLM/python.exe scripts/run_package.py
& E:/envs/LLM/python.exe scripts/self_audit.py
& E:/envs/LLM/python.exe -m unittest discover -s tests -v
& E:/envs/LLM/python.exe scripts/build_manifest.py
```

部分运行必须保留 `full_run=false`，不能把失败或部分结果改写成完整成功。
