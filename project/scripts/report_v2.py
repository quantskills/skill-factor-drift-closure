"""Build the reader-facing v2 report and dashboard from the frozen results."""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v2"
CFG = json.loads((ROOT / "config/audit_v2.json").read_text(encoding="utf-8"))
V3 = ROOT / "results" / "v3_one_week"

LABELS = {
    "A": "不处理 Ridge",
    "B": "固定半仓",
    "A_ew": "始终等权信号",
    "C_ic": "成熟 IC → 半仓",
    "D_ic": "成熟 IC → 重训",
    "F_ic": "成熟 IC → 换信号",
    "C_health": "健康入口 → 半仓",
    "D_health": "健康入口 → 重训",
    "F_health": "健康入口 → 换信号",
    "C_psi": "第三期 PSI → 半仓",
    "C_drift": "漂移入口 → 半仓",
    "D_drift": "漂移入口 → 重训",
    "F_drift": "漂移入口 → 换信号",
}


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def load_from(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(x: float, digits: int = 2) -> str:
    return f"{x * 100:+.{digits}f}%"


def pp(x: float, digits: int = 2) -> str:
    return f"{x * 100:+.{digits}f} pp"


def maybe_num(x, digits: int = 2) -> str:
    return "NA（未完成）" if x is None or pd.isna(x) else f"{x:.{digits}f}"


def markdown_table(frame: pd.DataFrame) -> str:
    """Small dependency-free Markdown table renderer."""
    cols = list(frame.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def table(headers, rows) -> str:
    return markdown_table(pd.DataFrame(rows, columns=headers))


def date_label(date: str) -> str:
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


def evidence_appendix(metrics: pd.DataFrame) -> str:
    """Keep every contrast and the main diagnostic results visible to reviewers."""
    tests = pd.read_csv(OUT / "multiplicity.csv")
    test_rows = [["多头" if r.expression == "long" else "对冲", LABELS[r.arm],
                  f"{r.delta_mean*100:+.3f}", f"{r.p_bh_conservative:.4f}",
                  f"[{r.ci_block_lo*100:+.3f}, {r.ci_block_hi*100:+.3f}]",
                  f"{r.mde80_per_cycle*100:.3f}"] for r in tests.itertuples()]
    false = pd.read_csv(OUT / "false_alarm.csv")
    false_rows = [["多头" if r.expression == "long" else "对冲", LABELS[r.arm],
                   f"{r.episodes}/{r.exposed_episodes}/{r.unexposed_episodes}",
                   f"{r.hits}/{r.losses}/{r.neutral}", f"{r.gain_sum*100:.2f}",
                   f"{r.false_alarm_cost*100:.2f}", f"{r.precision_descriptive*100:.1f}%"]
                  for r in false.itertuples()]
    recovery = [r for r in load("recovery.json")
                if r["expression"] == "long" and r["arm"] in ("C_ic", "C_health", "C_psi", "C_drift")]
    recovery_rows = [[LABELS[r["arm"]], r["episodes"], r["completed"], r["right_censored"],
                      maybe_num(r['completed_mean_observations']),
                      maybe_num(r['observed_mean_including_lower_bounds']),
                      "0" if r["extra_latch_observations"] == 0 else "未作此估计"] for r in recovery]
    placebo = pd.read_csv(OUT / "placebo.csv")
    base = metrics.set_index(["expression", "arm"])
    placebo_rows = []
    for (expr, arm), group in placebo.groupby(["expression", "arm"]):
        actual = base.loc[(expr, arm), "total"]
        placebo_rows.append(["多头" if expr == "long" else "对冲", LABELS[arm], pct(actual),
                             pct(group.total.mean()),
                             f"{pct(group.total.quantile(.05))} 至 {pct(group.total.quantile(.95))}",
                             "是" if actual > group.total.quantile(.95) else "否"])
    return f"""
## 附录：完整结果与审计明细

### A. 全部收益与风险结果

{markdown_table(metrics[['expression', '策略', '净收益', '平均 Sharpe', '最差相位回撤']])}

Sharpe 为各相位按每年 13 个持有周期年化后的均值；回撤为包含初始权益 1 的最差相位回撤。`long` 是多头，`hedge` 是多头减同池等权组合，后者没有估计 beta。

### B. 完整 {len(tests)} 项统计比较

全部相对同表达下的 A。增量、区间、MDE 的单位均为“百分点/四周周期”，与累计复利净收益差不同。区间是未经家族校正的 95% 循环块 bootstrap 区间；显著性以保守 BH 列及家族 Reality Check 判断。

{table(['表达', '动作', '每周期增量', '保守 BH', '块 bootstrap 区间', '80% MDE'], test_rows)}

MDE 是 `2.8 × bootstrap 标准误` 的近似功效尺度，不是因果效应，也不是未来样本量保证。完整 IID、块检验原始 p 值见 [multiplicity.csv](results/v2/multiplicity.csv)。

### C. 事件盈亏与恢复

盈利或亏损按告警窗口内相对 A 的净收益增量记账。“误报成本”是亏损事件增量绝对值之和，不是另收取的一项费用。以下数值按四相位算术增量口径统计，不与累计复利收益差混用。

{table(['表达', '动作', '事件/暴露/未暴露', '盈利/亏损/中性', '盈利合计pp', '误报成本pp', '描述性盈利占比'], false_rows)}

同一预警规则在两种表达、三种动作下共享告警时间，因此恢复表只列一份规则级结果：

{table(['规则', '告警段', '已结束', '右删失', '已结束段均值', '含删失下限的观测均值', '额外锁存观测数'], recovery_rows)}

单位是周度观测数，节假日缺周时不等于日历周。右删失表示截至样本末端仍未解除；含删失下限的均值也不是真实平均恢复时间。成熟 IC 进入和退出使用相同阈值，额外锁存延迟为 0；旧版“多耗 2.7 周”已撤回。重训在告警解除后继续生效，窗口外盈亏另见 [episode_reconciliation.csv](results/v2/episode_reconciliation.csv)。

### D. 50 组随机动作对照

{table(['表达', '动作', '主实验净收益', '随机均值', '随机p5—p95', '主实验超过p95'], placebo_rows)}

随机降权/切换匹配成熟 IC 的告警观测数量，随机重训匹配更新次数；没有匹配告警持续时间或行情状态，属于离线对照。分位数不是校正后的显著性，也不替代新样本验证。
"""


def metrics_frame() -> pd.DataFrame:
    frame = pd.DataFrame(load("metrics.json"))
    frame["策略"] = frame["arm"].map(LABELS)
    frame["净收益"] = frame["total"].map(pct)
    frame["最差相位回撤"] = frame["worst_phase_mdd"].map(pct)
    frame["平均 Sharpe"] = frame["sharpe_mean"].map(lambda x: f"{x:.2f}")
    return frame


def markdown_report() -> str:
    metrics = metrics_frame()
    inf = load("inference.json")
    audit = load("backtest_audit.json")
    health = load("health_robustness.json")
    calibration = load("calibration.json")
    refits = load("platform_refits.json")["records"]
    sensitivity = pd.DataFrame(load("missing_return_sensitivity.json"))
    long = metrics[metrics.expression == "long"].set_index("arm")
    hedge = metrics[metrics.expression == "hedge"].set_index("arm")
    hedge_gain_refit = hedge.loc["D_ic", "total"] - hedge.loc["A", "total"]
    hedge_gain_switch = hedge.loc["F_ic", "total"] - hedge.loc["A", "total"]
    hedge_gain_half = hedge.loc["B", "total"] - hedge.loc["A", "total"]
    key_rows = [[LABELS[a], pct(long.loc[a, "total"]), pct(hedge.loc[a, "total"])]
                for a in LABELS]
    key_table = table(["处置方案", "多头累计净收益", "对冲累计净收益"], key_rows)
    stress = sensitivity.set_index(["expression", "arm"])
    stress_rows = [["多头" if r.expression == "long" else "对冲", LABELS[r.arm],
                    pct(r.total), pct(stress.loc[(r.expression, r.arm), "total"]), r.missing_long]
                   for r in metrics.itertuples() if r.arm in ("A", "B", "D_ic", "F_ic", "F_health")]
    stress_table = table(["表达", "方案", "缺失填0", "缺失填−100%", "所选多头缺失标签次数"], stress_rows)
    costs = pd.read_csv(OUT / "cost_decomposition.csv")
    cost_table = table(["表达", "方案", "Δ毛收益pp", "Δ成本pp", "Δ净收益pp"], [
        ["多头" if r.expression == "long" else "对冲", LABELS[r.arm],
         f"{r.delta_gross*100:+.2f}", f"{r.delta_cost*100:+.2f}", f"{r.delta_net*100:+.2f}"]
        for r in costs.itertuples() if r.arm in ("B", "C_ic", "C_health", "D_ic", "F_ic", "C_drift", "D_drift", "F_drift")])
    appendix = evidence_appendix(metrics)
    one_week_note = ""
    if (V3 / "metrics.json").is_file() and (V3 / "inference.json").is_file():
        m1 = pd.DataFrame(load_from(V3 / "metrics.json")).set_index(["expression", "arm"])
        i1 = load_from(V3 / "inference.json")
        one_week_note = f"""
## 附加探索：一周标签

项目另有不覆盖 v2 的一周标签分支，标签为 `open(t+2)/open(t+1)-1`，成熟度仍保持 5 个周度观测。多头不处理 Ridge 为 **{pct(m1.loc[('long','A'),'total'])}**，对冲成熟 IC 换信号为 **{pct(m1.loc[('hedge','F_ic'),'total'])}**；{i1['family_size']} 项检验最小保守 BH 为 **{i1['min_bh_conservative']:.4f}**，仍不足以证明一周标签更优。完整结果见 [results/v3_one_week/report.md](results/v3_one_week/report.md)，v2 四周标签仍是本项目权威结果。
"""

    return f"""# 动态因子预警后的处置是否有增量价值？

> **一句话结论：** 项目已经把“监控到预警后该怎么做”做成了可复现的纸面实验。结果显示，重训或换信号在部分场景有方向性改善，但没有通过多重比较和 Reality Check，也没有稳定超过最简单的固定半仓；因此当前成果是诊断与验证闭环，尚不足以自动下单。

## 1. 项目目的

这个项目研究一个具体的决策问题：当冻结的因子预测出现健康恶化、漂移或成熟标签的 IC 下降时，应该继续持有、降低仓位、重训模型，还是换用备选信号？

背景是量化选股模型可能随市场环境变化而失效。仅发现“预测效果下降”还不够：降低仓位可能避开亏损，也可能错过上涨；重训和换信号可能修复预测，也可能增加换手和误判。因此项目把“能否发现变化”和“采取动作是否划算”分开检验。

把预警、动作、交易成本、恢复和统计检验放到同一套流程中，才能回答“预警是否值得触发动作、哪种动作可能有用、证据有多可靠”。项目沿用已有因子和预测，重点检验处置带来的增量。

## 2. 项目解决了什么问题

本项目解决两个问题。第一，监控提示“因子可能变差”后，需要比较不同动作扣成本后的得失，才能决定是否干预。第二，旧版实验存在校准混入评估期、交易核算和统计口径等问题，必须先修正这些问题，才能可信地比较动作。

当前版本解决了这些可审计问题：

- **监控入口**：健康监控和漂移监控都从项目内 `.agents/skills/` 调用，保留 CLI 输入、输出、版本和哈希；主实验的 {len(refits)} 个独立重训日期均调用平台来源 ML CLI，和快速实现分数的 Spearman 约为 1，最大绝对误差为 `{max(r['max_abs_diff'] for r in refits):.2g}`。QuantStudio `quantstudio` profile/session 已从项目路径执行完整管线，并保存平台会话、输入哈希、stdout、结果清单与测试记录；任务页 GUI 注册/提交仍未执行。
- **时间边界**：阈值只用 2024 年校准；评估从 2025-01-03 开始；成熟标签至少等待 5 个周度观测，实际收益持有 4 个周度观测。
- **交易核算**：买入、卖出和旧仓漂移全部计入换手；成本、借券费、初始权益和回撤都进入同一账户核算。
    - **统计审计**：{inf['family_size']} 个假设同时做 IID 与循环块 bootstrap、BH 多重比较、White-style Reality Check，并加入 50 组随机动作/重训安慰剂。
- **异常和边界**：单独记录误报、未暴露事件、右删失恢复事件、缺失收益标签敏感性和健康参数扰动。

## 3. 研究设计

评估的决策日期为 **{date_label(audit['eval_dates'][0])}—{date_label(audit['eval_dates'][-1])}**，共 4 个相位，每个相位 {audit['phase_cycles']} 个四周周期。2026-09-18、09-25、10-02 虽已成熟，因保持四相位期数一致而排除；2026-10-09 至 11-06 因标签尚未成熟排除。2026 年样本此前已被查看，本次属于回顾性纠错；`config/audit_v2.json` 是修订计划，旧 `preregistration.json` 不构成前瞻性注册。

沿用冻结的 {audit['factor_count']} 个上游因子及存档预测，不在本次实验重新选因子。每个时点在相同的可观察股票池内按分数选前 50 只。分别计算**多头**（`long`）和**多头减同池等权组合**（`hedge`）；后者没有估计 beta，不能称为严格市场中性。

为避免术语影响理解，各方案的操作定义如下：

| 名称 | 在本项目中怎么做 |
|---|---|
| Ridge / A | 沿用已有的岭回归预测分数，始终按原暴露持有，作为不处理基线 |
| 固定半仓 / B | 全评估期的暴露固定为原来的 50%，用于检验简单缩减风险是否已经足够 |
| 成熟 IC 预警 | IC 是分数与未来收益的截面 Spearman 相关；只用当时已成熟标签，最近 13 个观测的 IC 均值低于 2024 校准阈值时预警 |
| 健康入口预警 | 项目内健康 CLI 的衰退概率 ≥ 0.8，或累积和（CUSUM）报警时预警 |
| 半仓 / C | 预警期间将暴露降到 50%，解除后恢复原暴露 |
| 重训 / D | 每个告警段开始时重新拟合 Ridge；新模型持续使用，直到下一次重训，告警解除不切回旧模型 |
| 换信号 / F | 预警期间改用 54 个上游处理后因子列直接均值组成的等权信号，解除后恢复原 Ridge 分数 |
| 始终等权 / A_ew | 全期使用同一等权信号，用于判断换信号的收益是否来自预警时机 |
| 第三期 PSI / C_psi | 复用冻结的 PSI 分布漂移告警，触发半仓；不重新挑选 PSI 参数 |
| 本期漂移闭环 / C_drift、D_drift、F_drift | 直接消费项目内 drift CLI 的季度 `warning` 状态，分别触发半仓、重训、换信号；`watch` 只记录，不触发动作 |

IC 阈值只用 {date_label(calibration['start'])} 至 {date_label(calibration['end'])} 的 {calibration['observations']} 个监控观测校准，阈值为 {calibration['theta']:.6f}；健康基线截至 {date_label(calibration['health_baseline_end'])}。收益标签是 `open(t+5)/open(t+1)−1`：**持有 4 个周度观测，在信号后第 5 个观测才能成熟**。重训末个训练日期距预测日期为 6 个观测，保留额外隔离。

四个相位从相邻周错开启动，每相位每隔 4 个观测调仓。报告的累计收益是四个独立账户终值收益的算术平均，**不是年化收益，也不是同步实盘组合净值**。统计检验则先将四相位的同周期增量配对平均，得到 {audit['phase_cycles']} 个周期；不把 88 个相位交易当作 88 个独立样本。

## 4. 关键结果

以下列出全部方案的累计净收益，已扣模型中的交易费和借券费；风险指标和完整统计明细在附录。

{key_table}

### 4.1 多头表达

不处理 Ridge 的净收益为 **{pct(long.loc['A','total'])}**。成熟 IC 重训为 **{pct(long.loc['D_ic','total'])}**，换信号为 **{pct(long.loc['F_ic','total'])}**，分别高出 {pp(long.loc['D_ic','total']-long.loc['A','total'])} 和 {pp(long.loc['F_ic','total']-long.loc['A','total'])}。但成熟 IC 半仓为 **{pct(long.loc['C_ic','total'])}**，健康入口半仓为 **{pct(long.loc['C_health','total'])}**，都低于不处理。降权减少了一些回撤，也牺牲了该样本的上涨收益，不能只按收益或回撤中的一项判断优劣。

### 4.2 对冲表达

不处理 Ridge 为 **{pct(hedge.loc['A','total'])}**，固定半仓为 **{pct(hedge.loc['B','total'])}**。相对不处理，成熟 IC 重训改善 **{pp(hedge_gain_refit)}**，成熟 IC 换信号改善 **{pp(hedge_gain_switch)}**，但固定半仓改善 **{pp(hedge_gain_half)}**，反而更高。因此动态处置有方向性改善，却没有证明提供超过固定风险缩减的稳定增量价值。

### 4.3 统计可靠性

- {inf['family_size']} 个假设中，保守 BH 最小 p 值为 **{inf['min_bh_conservative']:.4f}**，BH ≤ 0.10 的结果数为 **{inf['n_bh_10']}**。
- 循环块 Reality Check 正向 p = **{inf['rc_positive_block']:.4f}**，负向 p = **{inf['rc_negative_block']:.4f}**。
- 因此不能把单个策略的正向净收益写成已经被统计证明的普适效果。

这里的 {inf['family_size']} 个假设是 {inf['family_size'] // 2} 个非 A 方案 × 2 种表达，均相对同表达下 A 比较；使用 {inf['bootstrap_draws']} 次重采样、循环块长 {inf['circular_block_cycles']} 个周期，BH 分别计算后取两种方法中的较大值。“没有通过”表示证据不足，不能进一步推断为“任何动态动作一定无效”。固定半仓与动态方案的差异在本文是描述性比较，未另增经过校正的直接检验。

## 5. 结果分析

重训和换信号的收益改善是本样本的观察结果。它们可能改变了持仓排序，捕捉到部分较好的阶段收益，但本实验没有证明这种改善由“预警准确识别失效”造成。附录的随机时点对照、统计检验和缺失标签敏感性共同限制了这种解释。

始终等权的多头净收益已有 **{pct(long.loc['A_ew','total'])}**；成熟 IC 换信号比它仅高 {pp(long.loc['F_ic','total']-long.loc['A_ew','total'])}，健康入口换信号比它高 {pp(long.loc['F_health','total']-long.loc['A_ew','total'])}。因此换信号相对 Ridge 的提升不能全部归功于预警时机。相对第三期 PSI 半仓，成熟 IC 半仓的多头差为 {pp(long.loc['C_ic','total']-long.loc['C_psi','total'])}，对冲差为 {pp(hedge.loc['C_ic','total']-hedge.loc['C_psi','total'])}，同样未显示一致改善。

健康参数扰动 {health['parameter_sets']} 组时，评估期告警占比从 **{health['evaluation_alarm_share_min'] * 100:.1f}%** 到 **{health['evaluation_alarm_share_max'] * 100:.1f}%**，与默认路径的最大分歧约 **{health['max_disagreement_with_default'] * 100:.1f}%**，路径稳定性判定为 false。这说明动作时间对规则设定敏感，削弱了健康入口的可迁移性。默认参数保持不变，不能根据评估期敏感性表反向挑选收益最高的参数。

误报表里的 precision 是“告警窗口内动作相对 A 的盈亏为正”的描述性比例。没有人工独立标注的失效事件，因此它不是漂移检测准确率。健康规则共 5 段告警，其中 1 段右删失；成熟 IC 共 7 段，其中 1 段右删失。只看已结束事件会低估长期未解除告警的影响；附录同时列出删失标记和观测下限。

50 组随机时点对照中，降权/切换匹配告警观测数量，重训匹配更新次数，用来观察随机选择动作时间是否也能得到类似结果。成熟 IC 的三种动作在两种表达下均未超过各自随机分布的 95% 分位，进一步限制了“预警时机有独立价值”的解释。

## 6. 成本、缺失标签与敏感性

交易费为单边 {CFG['one_way_cost']*10000:.0f} bp，对冲短腿借券年费率为 {CFG['borrow_annual']*100:.0f}%。换手计入旧持仓卖出、新持仓买入及收益导致的权重漂移。下表按四相位平均的**逐期算术和**拆解相对 A 的变化，满足 `Δ净收益 = Δ毛收益 − Δ成本`；与上面的累计复利终值差不是同一口径。

{cost_table}

固定半仓在对冲中的改善很大一部分来自成本减少；健康半仓则在毛收益减少的同时节省成本。重训和换信号的算术增量主要来自毛收益变化，成本没有明显下降。这个拆分解释了账面差异，但不是对 alpha 修复或 beta 择时的因果证明。

部分个股收益标签在成熟日历内仍然缺失；选股池不根据未来收益是否缺失来筛选。基准将缺失填 0，敏感性将同一标签填为 `−100%`：

{stress_table}

缺失次数是各相位决策中所选多头的累计次数，不是独立股票数。仅多头 A 就从 **{pct(long.loc['A','total'])}** 变为 **{pct(stress.loc[('long','A'),'total'])}**；健康换信号的多头由 **{pct(long.loc['F_health','total'])}** 变为 **{pct(stress.loc[('long','F_health'),'total'])}**，相对排序也会改变。因此绝对收益和部分方案排序都依赖缺失假设，不能据此确定实盘盈利能力。`−100%` 是敏感性情景，尤其对包含短腿的组合并非严格最坏界。

## 7. 研究决策

当前建议是：

1. **保留监控入口和诊断链路**，继续记录健康、漂移、IC、误报和恢复事件；
2. **纸面验证可以继续**，重点观察动态动作是否在新的、明确冻结的样本上超过固定半仓；
3. **暂不自动下单，也不把某个动作设为默认最优策略**；
4. QuantStudio 会话执行已核验；若要进入平台 GUI 注册、调度或提交，需要另行人工核验，本地会话执行不等于任务页已提交。

继续研究的优先顺序是：先查清缺失收益的来源并补足真实退出记录，再在新数据到来前冻结默认规则和统计比较，随后与不处理、固定半仓、始终等权同时做前向纸面记录。未来若要支持自动处置，需要新样本中的稳定增量、可靠的数据与可成交成本、参数稳定性和家族检验共同提供证据。

## 8. 当前不能声称什么

- 不能声称动态重训或换信号已经显著赚钱；
- 不能声称健康监控参数已经稳定，或适用于未观察过的市场阶段；
- 不能把 2026 年已查看样本称为未见确认集；
- 不能把本地回测和 CLI 运行记录写成 QuantStudio 任务页提交、GUI 注册或实盘执行；
- 不能把误报 precision、恢复周数或 MDE 当成独立真实标签下的因果结论。

实际可交易性还受以下限制：上游股票池成员和因子发布时间没有在本包中独立重建；周度开盘价与真实下一交易日执行没有逐笔核对；入场资格继承上游可成交过滤。冲击、借券可得性和退出失败尚未建模。详细定义见 [DATA_CONTRACT.md](DATA_CONTRACT.md)。

## 9. 复现与证据入口

## 10. QuantStudio 平台真实入口状态

本课题要求必须从 QuantStudio 真实入口执行并留下输入、运行和输出记录。本次已在 QuantStudio `quantstudio` profile/session 中确认项目路径 `E:\period5_package\period5_package`，执行 `python scripts/run_package.py`、自评、11 项回归测试和 manifest；会话 ID、输入哈希、命令、stdout、输出清单和哈希保存在 [平台记录](runs/quantstudio_platform_entry/platform_entry_record.json)。QuantStudio 没有向本会话暴露独立 run ID，也未执行任务页 GUI 注册或外部提交；任务页状态仍为“创作中 / 尚未提交成果”。因此本报告可以声称“已从 QuantStudio 真实入口执行并留痕”，但不能声称“已提交任务”或“已有独立平台 run ID”。

完整重跑：

```powershell
& E:/envs/LLM/python.exe scripts/run_package.py
```

只重建已有结果的文档、验收和清单：

```powershell
& E:/envs/LLM/python.exe scripts/run_package.py --only report verify manifest
```

部分运行必须保留 `full_run=false`；最新执行状态以日志为准。验收检查通过表示代码、数据一致性和核算规则得到验证，**不表示盈利假设通过统计检验**。

主要证据文件：

- `results/v2/metrics.json`：各表达和动作的净收益、Sharpe、回撤；
- `results/v2/inference.json`：{inf['family_size']} 个假设的多重比较与 Reality Check；
- `results/v2/false_alarm.csv`、`recovery.json`：误报和恢复；
- `results/v2/missing_return_sensitivity.json`、`health_robustness.json`：敏感性；
- `results/v2/backtest_audit.json`：评估边界、成熟度和排除日期；
- `verification/ACCEPTANCE_V2.json`：代码、数据和回归验收；
- `runs/_pipeline/run_log.json`：实际 CLI 运行状态。旧版结果保留在 `archive/legacy_v1/`。

{one_week_note}

{appendix}
"""


def dashboard_html() -> str:
    metrics = metrics_frame()
    inf = load("inference.json")
    health = load("health_robustness.json")
    audit = load("backtest_audit.json")
    stress = pd.DataFrame(load("missing_return_sensitivity.json")).set_index(["expression", "arm"])
    long = metrics[metrics.expression == "long"].set_index("arm")
    hedge = metrics[metrics.expression == "hedge"].set_index("arm")
    rows = []
    for arm in LABELS:
        rows.append(f"<tr><th scope='row'>{html.escape(LABELS[arm])}</th>"
                    f"<td>{long.loc[arm, '净收益']}</td><td>{hedge.loc[arm, '净收益']}</td></tr>")
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>动态预警处置研究 v2</title>
<style>body{{font-family:system-ui,-apple-system,'Microsoft YaHei',sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#18212b;background:#f7f8fa;line-height:1.8}}h1{{font-size:32px;line-height:1.4;margin-bottom:8px}}h2{{margin-top:34px}}.lead{{font-size:19px;background:#e9f2ff;border-left:5px solid #2878d4;padding:16px 20px;border-radius:10px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{background:white;border:1px solid #dfe5ec;border-radius:12px;padding:16px}}.num{{font-size:25px;font-weight:700;margin-top:6px}}table{{width:100%;border-collapse:collapse;background:white;font-variant-numeric:tabular-nums}}th,td{{padding:10px;border-bottom:1px solid #e5e9ef;text-align:left}}thead th{{background:#eef2f6}}tbody th{{font-weight:500}}.muted{{color:#4b5867}}code{{background:#edf0f3;padding:2px 5px;border-radius:4px}}a{{color:#175caa}}nav{{display:flex;gap:20px;flex-wrap:wrap}}@media(max-width:700px){{.cards{{grid-template-columns:repeat(2,1fr)}}body{{padding:0 16px;margin:24px auto}}h1{{font-size:26px}}th,td{{padding:8px;font-size:14px}}}}@media(max-width:380px){{.cards{{grid-template-columns:1fr}}}}</style></head>
<body><h1>动态因子预警后的处置是否有增量价值？</h1>
<nav aria-label='文档入口'><a href='README.md'>项目简介</a><a href='report.md'>完整报告与附录</a><a href='results/v3_one_week/report.md'>一周标签探索</a><a href='TASK_CHECKLIST.md'>验收清单</a></nav>
<p class='lead'>项目完成了监控、动作模拟、成本核算和统计审计的闭环。动态重训或换信号有方向性改善，但没有统计证明其稳定优于固定半仓；当前结论是保留诊断与纸面验证，暂不自动下单。</p>
<h2>目的与解决的问题</h2><p>量化模型的预测能力可能随市场变化而下降。项目要回答：看到预警后，继续持有、减半仓位、重训还是换信号，扣除成本后哪个更有价值？项目统一了监控、处置和对照实验，并修正旧版时间边界、买卖成本及统计核算，让结论可以复核。</p>
<p class='muted'>IC 是预测分数与未来收益的相关程度；健康入口结合衰退概率和累积变化发出预警。重训使用当时已成熟的数据拟合新 Ridge 模型并持续使用；换信号仅在预警期间启用冻结的等权备选信号。</p>
<div class='cards'><div class='card'>决策日期<div class='num'>2025–2026</div><div class='muted'>{date_label(audit['eval_dates'][0])} 至 {date_label(audit['eval_dates'][-1])}<br>4 个相位，每相位 {audit['phase_cycles']} 周期</div></div><div class='card'>假设数量<div class='num'>{inf['family_size']}</div><div class='muted'>BH ≤ 0.10：{inf['n_bh_10']} 个</div></div><div class='card'>最小保守 p<div class='num'>{inf['min_bh_conservative']:.4f}</div><div class='muted'>Reality Check 正向 p {inf['rc_positive_block']:.4f}</div></div><div class='card'>健康路径稳定性<div class='num'>{'是' if health['stable_across_path_parameters'] else '否'}</div><div class='muted'>{health['parameter_sets']} 组参数，最大分歧 {health['max_disagreement_with_default']*100:.1f}%</div></div></div>
<h2>全部方案的主要结果</h2><table><caption>四相位账户终值收益平均，扣成本，非年化收益</caption><thead><tr><th scope='col'>处置方案</th><th scope='col'>多头累计净收益</th><th scope='col'>对冲累计净收益</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p class='muted'>多头按分数选前 50 只；对冲表达为多头减同池等权组合，没有估计 beta。阈值只用 2024 年校准；标签成熟等待 5 个周度观测，实际持有 4 个观测。</p>
<h2>结果为什么这样解读</h2><p>成熟 IC 重训和换信号在多头中高于不处理，但动态半仓牺牲了上涨收益。对冲中固定半仓为 {hedge.loc['B','净收益']}，高于全部动态方案的点估计。始终等权多头已有 {long.loc['A_ew','净收益']}，换信号的改善不能全部归功于预警时机。全部 {inf['family_size']} 项检验均未通过保守 BH，说明当前证据不足；漂移入口消费真实 drift CLI 的 warning 状态，第三期 PSI 仅作为冻结基线。</p>
<h2>影响结论的限制</h2><ul><li>健康规则 27 组扰动的告警占比为 {health['evaluation_alarm_share_min']*100:.1f}%—{health['evaluation_alarm_share_max']*100:.1f}%，动作时间对参数敏感。</li><li>缺失收益基准填 0；改填 −100% 后，多头不处理由 {long.loc['A','净收益']} 变为 {pct(stress.loc[('long','A'),'total'])}，绝对收益和部分方案排序对缺失假设敏感。</li><li>告警恢复包含右删失；误报指标是动作盈亏描述，没有独立标注的真实失效事件。</li><li>2026 样本已被查看，属于回顾性纠错；市场冲击、融券可得性和退出失败未建模。本地 CLI 不代表平台 GUI 注册或提交。</li></ul>
<h2>下一步决策</h2><p>保留监控和纸面记录，先补足缺失收益与退出记录，再冻结规则，用新数据与不处理、固定半仓、始终等权同步对照。当前证据不支持自动执行交易。</p>
<h2>证据入口</h2><ul><li><a href='report.md'>完整研究报告</a>：成本拆分、敏感性及全部 {inf['family_size']} 项检验附录。</li><li><a href='results/v2/metrics.json'>收益与风险结果</a> · <a href='results/v2/inference.json'>统计检验</a> · <a href='results/v2/health_robustness.json'>参数稳定性</a></li><li><a href='verification/ACCEPTANCE_V2.json'>验收结果</a> · <a href='runs/_pipeline/run_log.json'>实际执行日志</a> · <a href='ARTIFACTS.md'>产物索引</a></li></ul><p class='muted'>验收通过证明核算和代码一致性，盈利假设是否成立由统计结果另行判断。</p></body></html>"""


def main() -> None:
    report = markdown_report()
    (ROOT / "report.md").write_text(report, encoding="utf-8")
    (ROOT / "dashboard.html").write_text(dashboard_html(), encoding="utf-8")
    print("[report] wrote report.md and dashboard.html")


if __name__ == "__main__":
    main()
