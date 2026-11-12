# QuantStudio 平台真实入口状态

本课题的硬性要求是：**必须从 QuantStudio 平台真实入口执行，并留下输入与输出记录**。

目前已核验到官方任务页 `TS20261019645533`，任务标题为“漂移预警触发降权或重训到底有没有净收益”，页面状态为“创作中”，并显示“尚未提交成果”。当前 QuantStudio 工作台中可见的是另一个 `triple_factor_trend` 商品期货策略草稿，与本项目的中证1000周频漂移闭环研究无关。

本次已从 QuantStudio 真实入口完成项目会话执行。会话 `session-764fd241-06f5-48f4-97e5-73986f72875f` 使用 `quantstudio` profile，确认项目路径为 `E:\period5_package\period5_package`，并按 AGENTS.md 执行 `python scripts/run_package.py`、自评、11 项回归测试和 manifest。输入哈希、命令、stdout、结果清单和输出哈希已写入 `runs/quantstudio_platform_entry/platform_entry_record.json`。

因此当前结论是：

- `runs/r01_monitor_entry/`、`runs/v2/refits/` 是本地项目和 QuantSkills 技能 CLI 的输入输出留痕；
- QuantStudio 会话记录和项目输入输出记录已取得；
- QuantStudio 没有向本会话暴露独立 run ID，也没有执行任务页 GUI 注册或外部提交；
- `runs/quantstudio_platform_entry/status.json` 保存了本次平台核验状态；
- 因此可以声称“已从 QuantStudio 真实入口执行并留痕”，但不能声称“已提交任务页”或“已获得平台独立 run ID”。

合格证据至少应包含：平台任务/工作区标识、运行编号或回测编号、冻结输入配置、平台生成的输出结果、运行时间和结果页/下载记录，并能与本目录的 `config/audit_v2.json`、`data/provenance.json` 和结果文件逐项对应。
