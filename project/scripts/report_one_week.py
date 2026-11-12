"""Write a compact comparison report for the one-week label branch."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "results" / "v2"
V3 = ROOT / "results" / "v3_one_week"
LABELS = {"A": "不处理 Ridge", "B": "固定半仓", "A_ew": "始终等权", "C_ic": "成熟 IC→半仓",
          "D_ic": "成熟 IC→重训", "F_ic": "成熟 IC→换信号", "C_health": "健康入口→半仓",
          "D_health": "健康入口→重训", "F_health": "健康入口→换信号", "C_psi": "第三期 PSI→半仓"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(x):
    return f"{x * 100:+.2f}%"


def pp(x):
    return f"{x * 100:+.2f} pp"


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join(lines)


def main():
    v2 = pd.DataFrame(load(V2 / "metrics.json")).set_index(["expression", "arm"])
    v3 = pd.DataFrame(load(V3 / "metrics.json")).set_index(["expression", "arm"])
    rows = []
    for arm, name in LABELS.items():
        rows.append([name, pct(v2.loc[("long", arm), "total"]), pct(v3.loc[("long", arm), "total"]),
                     pp(v3.loc[("long", arm), "total"] - v2.loc[("long", arm), "total"]),
                     pct(v2.loc[("hedge", arm), "total"]), pct(v3.loc[("hedge", arm), "total"]),
                     pp(v3.loc[("hedge", arm), "total"] - v2.loc[("hedge", arm), "total"])])
    inf2, inf3 = load(V2 / "inference.json"), load(V3 / "inference.json")
    p2 = load(ROOT / "data" / "one_week" / "provenance.json")
    a3 = load(V3 / "backtest_audit.json")
    h2 = pd.read_csv(ROOT / "runs" / "r01_monitor_entry" / "health" / "health_timeseries.csv")
    h3 = pd.read_csv(ROOT / "runs" / "v3_one_week_monitor" / "health" / "health_timeseries.csv")
    for h in (h2, h3): h["date"] = pd.to_datetime(h["date"]).dt.strftime("%Y%m%d")
    sh2 = h2[h2.date.between("20250103", "20260911")].assign(alarm=lambda x: x.decline_probability.ge(.8) | x.cusum_alarm.eq(True)).alarm.mean()
    sh3 = h3[h3.date.between("20250103", "20260911")].assign(alarm=lambda x: x.decline_probability.ge(.8) | x.cusum_alarm.eq(True)).alarm.mean()
    report = f"""# 一周标签对照实验：未来一周收益是否更有效？

> **实验结论：** 把标签从四周收益改成一周收益后，模型和动态动作的累计收益整体下降，多头不处理 Ridge 从 **{pct(v2.loc[('long','A'),'total'])}** 降到 **{pct(v3.loc[('long','A'),'total'])}**；但成熟 IC 换信号和对冲换信号的相对表现改善。18 项检验仍没有通过 BH，不能据此证明一周标签更好。

## 这次改了什么

v2 使用 `open(t+5)/open(t+1)-1`，代表信号后 4 个周度观测的收益；本次 v3 改为 `open(t+2)/open(t+1)-1`，代表信号后 1 个周度观测的收益。标签从历史周线开盘价重新构造，写入项目内 [one_week/weekly_slim.csv](../../data/one_week/weekly_slim.csv)。同时，v3 的基线 Ridge 也用一周标签重新滚动训练，不能把四周标签训练出的旧分数直接当作一周模型。

为了保持与 v2 的实验可比性，**成熟度仍固定为 5 个周度观测**，只改变收益持有期；v2 的 `results/v2/`、配置和报告没有覆盖。该分支是回顾性探索，不是新的前瞻确认集。

## 收益结果对比

| 处置方案 | v2 多头 | v3 一周多头 | 变化 | v2 对冲 | v3 一周对冲 | 变化 |
|---|---:|---:|---:|---:|---:|---:|
{table(['方案','v2 多头','v3 一周多头','变化','v2 对冲','v3 一周对冲','变化'], rows).split(chr(10), 2)[2]}

变化是 v3 减 v2 的百分点。收益均为四个相位独立账户终值的算术平均，已扣交易和借券成本，不是年化收益。

### 多头

不处理 Ridge 从 **{pct(v2.loc[('long','A'),'total'])}** 降到 **{pct(v3.loc[('long','A'),'total'])}**；始终等权从 **{pct(v2.loc[('long','A_ew'),'total'])}** 降到 **{pct(v3.loc[('long','A_ew'),'total'])}**。一周标签下，成熟 IC 换信号为 **{pct(v3.loc[('long','F_ic'),'total'])}**，高于不处理 **{pp(v3.loc[('long','F_ic'),'total']-v3.loc[('long','A'),'total'])}**；健康入口换信号为 **{pct(v3.loc[('long','F_health'),'total'])}**，改善只有 **{pp(v3.loc[('long','F_health'),'total']-v3.loc[('long','A'),'total'])}**。

### 对冲

不处理 Ridge 从 **{pct(v2.loc[('hedge','A'),'total'])}** 变为 **{pct(v3.loc[('hedge','A'),'total'])}**；固定半仓为 **{pct(v3.loc[('hedge','B'),'total'])}**。一周标签下，成熟 IC 换信号为 **{pct(v3.loc[('hedge','F_ic'),'total'])}**，比不处理改善 **{pp(v3.loc[('hedge','F_ic'),'total']-v3.loc[('hedge','A'),'total'])}**，高于固定半仓的改善 **{pp(v3.loc[('hedge','B'),'total']-v3.loc[('hedge','A'),'total'])}**。这是方向性变化，仍需新样本确认。

## 统计可靠性

| 指标 | v2 四周标签 | v3 一周标签 |
|---|---:|---:|
| 18 项假设最小保守 BH | {inf2['min_bh_conservative']:.4f} | {inf3['min_bh_conservative']:.4f} |
| BH ≤ 0.10 的数量 | {inf2['n_bh_10']} | {inf3['n_bh_10']} |
| 循环块 Reality Check 正向 p | {inf2['rc_positive_block']:.4f} | {inf3['rc_positive_block']:.4f} |
| 循环块 Reality Check 负向 p | {inf2['rc_negative_block']:.4f} | {inf3['rc_negative_block']:.4f} |

一周标签的最小保守 BH 反而升到 **{inf3['min_bh_conservative']:.4f}**，所有假设仍未通过。也就是说，一周标签在这个历史区间内没有显示出更强的统计证据。

## 监控变化

一周收益的健康监控告警占比约为 **{sh3 * 100:.1f}%**，四周标签约为 **{sh2 * 100:.1f}%**。一周标签的健康信号更少，因此健康入口半仓的平均暴露升到 **{v3.loc[('long','C_health'),'avg_exposure']:.3f}**；这不是模型更稳定的证明，而是告警路径改变后的直接结果。

## 一周标签的含义

- 优点：更贴近短周期调仓，标签更新快，潜在反馈延迟更短。
- 代价：单周收益噪声更大，预测分数更容易受短期行情影响；这次实验中 Ridge 的平均 Sharpe 和绝对净收益都下降。
- 现象：换信号在对冲表达中改善较明显，但统计检验没有支持“预警时机已被证明有价值”。
- 边界：健康监控仍按 5 个周度观测成熟，不能把一周标签简单理解成“只等一周就能训练和预警”。

## 当前决策

一周标签可以保留为研究分支，适合继续观察短周期预警和换信号；它不能替换当前 v2 四周标签作为权威结果，也不能直接用于自动下单。下一步应在冻结标签、成熟度和动作规则后，用新的未查看样本比较一周与四周标签，而不是根据本次历史区间挑选收益更高的标签。

## 复现

```powershell
& E:/envs/LLM/python.exe scripts/prepare_one_week.py
& E:/envs/LLM/python.exe scripts/engine_one_week.py
& E:/envs/LLM/python.exe scripts/analyze_one_week.py
& E:/envs/LLM/python.exe scripts/report_one_week.py
```

结果文件：`results/v3_one_week/`。v2 权威结果仍在 `results/v2/`。
"""
    (V3 / "report.md").write_text(report, encoding="utf-8")
    print(f"[one-week report] wrote {V3 / 'report.md'}")


if __name__ == "__main__":
    main()
