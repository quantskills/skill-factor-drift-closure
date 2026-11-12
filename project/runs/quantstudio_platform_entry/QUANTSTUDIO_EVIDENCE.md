# QuantStudio 真实入口证据

## 入口身份

- 平台：**QuantStudio**
- profile：`quantstudio`
- 本地入口：`http://127.0.0.1:3097/`
- QuantStudio 页面标题：`QuantSkills`
- QuantStudio 会话 ID：`session-764fd241-06f5-48f4-97e5-73986f72875f`
- QuantStudio 会话归档：`E:\QuantStudio-Data\sessions\--C-Users-DELL-Documents-QuantSkills--\session-764fd241-06f5-48f4-97e5-73986f72875f\session.jsonl.zstd`
- 会话归档大小：5,726,194 bytes；SHA256 由 `platform_entry_record.json` 的外部会话路径核对。

这次证据只来自 QuantStudio。EVO 页面、商品期货 `triple_factor_trend` 草稿和其他产品入口均未用于本项目验证。

## 项目绑定与输入

QuantStudio 会话确认项目路径为 `E:\period5_package\period5_package`，并以该路径作为每条命令的 `workdir`。输入配置和数据快照的字节数、SHA256 记录在 `platform_entry_record.json`：

- `config/audit_v2.json`
- `config/preregistration.json`
- `data/provenance.json`
- `data/panel_for_platform.csv`
- `data/weekly_slim.csv`
- `data/validation_2026_signal.csv`
- `data/third_period_psi.csv`

## QuantStudio 会话中实际执行的命令

```powershell
E:/envs/LLM/python.exe -u scripts/run_package.py
E:/envs/LLM/python.exe scripts/self_audit.py
E:/envs/LLM/python.exe -m unittest discover -s tests -v
E:/envs/LLM/python.exe scripts/build_manifest.py
```

平台会话返回并落盘的记录：

- `runs/quantstudio_platform_entry/_entry_console.log`
- `runs/quantstudio_platform_entry/_self_audit_console.log`
- `runs/quantstudio_platform_entry/_unittest_console.log`
- `runs/quantstudio_platform_entry/_build_manifest_console.log`
- `runs/quantstudio_platform_entry/platform_entry_record.json`
- `runs/quantstudio_platform_entry/status.json`

## 平台输出

- 管线：`all_ok=true`、`full_run=true`、7 个步骤完成。
- 验收：77 项通过。
- 回归测试：11 项通过。
- 自评：`Q=90`、`D=1.00`、`V=0.80`、积分 `72`。
- manifest：最终 606 个文件已生成并记录 SHA256。
- 结果文件、验证文件、报告文件及每个管线步骤的 `cmd.txt`、`input.json`、`status.json`、`stdout.log` 均在 `platform_entry_record.json` 的 `outputs` 中列出。

## 平台边界

QuantStudio 没有向本会话暴露独立 run ID，也没有执行任务页 GUI 注册或外部提交。因此本包可以证明“从 QuantStudio 真实入口执行并留下输入/输出记录”，但不声称“任务页已提交”或“存在独立平台 run ID”。
