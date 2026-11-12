"""Reproducible frozen and mature-label rolling LightGBM comparison for 2026."""
from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from engine_v2 import ROOT, CFG, load_cache, metrics, save, sha, simulate

CONFIG = ROOT / "config/lightgbm_2026.json"
OUT = ROOT / "results/v2/lightgbm_2026"
RUN = ROOT / "runs/lightgbm_2026"


def training_dates(dates, prediction_date, window=156, maturity=5):
    """Use the same conservative fold as v2: last train date is index i-6."""
    i = dates.index(prediction_date)
    end = i - maturity
    if end < window:
        raise ValueError("insufficient training history")
    return dates[end-window:end]


def evaluation_dates(dates, start="20260101", end="20261231", maturity=5):
    year = [d for d in dates if start <= d <= end]
    mature = [d for i, d in enumerate(dates) if d in year and i + maturity < len(dates)]
    balanced = mature[:len(mature)//4*4]
    return year, mature, balanced


def training_arrays(cache, selected):
    x = np.vstack([cache[d]["X"] for d in selected])
    y = np.concatenate([cache[d]["ret"] for d in selected])
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    return x[valid], y[valid]


def fit_predict(cache, dates, train, test, factors, parameters, directory):
    from lightgbm import LGBMRegressor
    from sklearn.linear_model import Ridge

    directory.mkdir(parents=True, exist_ok=True)
    assert max(train) < min(test)
    x, y = training_arrays(cache, train)
    lgb = LGBMRegressor(**parameters).fit(x, y)
    ridge = Ridge(alpha=1.).fit(x, y)
    # NumPy input avoids LightGBM's rejection of ':' in upstream feature names.
    lgb.booster_.save_model(str(directory / "lightgbm.txt"))
    np.savez(directory / "ridge.npz", coef=ridge.coef_, intercept=ridge.intercept_)
    by_model = {"lightgbm": {}, "ridge": {}}
    for d in test:
        xx = cache[d]["X"]
        valid = np.isfinite(xx).all(axis=1)
        for name, estimator in (("lightgbm", lgb), ("ridge", ridge)):
            values = np.full(len(xx), np.nan)
            # Booster consumes ndarray directly, preserving the saved model's feature order.
            values[valid] = lgb.booster_.predict(xx[valid], num_threads=4) if name == "lightgbm" else estimator.predict(xx[valid])
            by_model[name][d] = values
    record = {"train_dates": train, "train_first": train[0], "train_last": train[-1],
        "train_observations": len(train), "train_rows": len(y), "test_dates": test,
        "first_test_gap_observations": dates.index(test[0])-dates.index(train[-1]),
        "has_2026_training_labels": any(d >= "20260101" for d in train),
        "feature_order": factors, "parameters": parameters,
        "training_X_sha256": __import__("hashlib").sha256(x.tobytes()).hexdigest(),
        "training_y_sha256": __import__("hashlib").sha256(y.tobytes()).hexdigest(),
        "lightgbm_model_sha256": sha(directory / "lightgbm.txt")}
    save(directory / "input.json", record)
    importance = pd.DataFrame({"factor": factors,
        "gain": lgb.booster_.feature_importance(importance_type="gain"),
        "split": lgb.booster_.feature_importance(importance_type="split")})
    importance.to_csv(directory / "importance.csv", index=False)
    return by_model, record, importance


def ic_table(cache, predictions, dates):
    rows = []
    for model, scores in predictions.items():
        for d in dates:
            c = cache[d]
            pool = c["elig"] & np.isfinite(c["score"]) & np.isfinite(c["X"]).all(axis=1)
            ok = pool & np.isfinite(c["ret"]) & np.isfinite(scores[d])
            value = pd.Series(scores[d][ok]).corr(pd.Series(c["ret"][ok]), method="spearman")
            rows.append({"model": model, "date": d, "rank_ic": value,
                "pool": int(pool.sum()), "n_labels": int(ok.sum()),
                "missing_labels": int((pool & ~np.isfinite(c["ret"])).sum())})
    return pd.DataFrame(rows)


def write_report(summary, audit, importance):
    names = {"lightgbm_frozen": "LightGBM 冻结（主结果）", "ridge_frozen": "Ridge 冻结",
        "lightgbm_rolling": "LightGBM 滚动", "ridge_rolling": "Ridge 滚动",
        "equal_weight": "54 因子均值", "ridge_archived_wf": "原存档 Ridge WF"}
    frozen = audit["frozen_fit"]
    lines = ["# 54 因子 LightGBM 合成：2026 年回顾性测试", "",
        "固定原有 54 个因子，未根据 2026 年结果调参、选择模型或筛选因子。2026 样本已经被查看，本次属于回顾性探索性比较。", "",
        f"- 主结果：冻结模型；训练 {frozen['train_first']}—{frozen['train_last']}，共 156 个周度观测、{frozen['train_rows']:,} 行，不使用任何 2026 年训练标签。",
        "- 次结果：每 4 个周度观测重训；滚动 156 周，跳过临近预测日的 5 个周度观测，最后训练日期为预测位置 i-6。允许使用当时已成熟的 2026 标签。",
        "- 两种模型均拟合原始 4 周前瞻收益；LightGBM 固定 200 棵树、15 叶、学习率 0.05、列采样 0.8、种子 20261111。未使用早停。subsample_freq=0，故行采样不生效，与上游技能默认一致。",
        f"- 配平的组合测试：{audit['eval_dates'][0]}—{audit['eval_dates'][-1]}，4 个独立相位，每相位 {len(audit['eval_dates'])//4} 个四周持有周期；终值收益取四相位算术平均。",
        "- 采用 v2 相同可交易股票池；所有模型都要求原 score_wf 和 54 因子完整，以保证对照一致。股票池不按未来收益是否缺失过滤。",
        "- Top50 等权；单边 8 bp，计入买卖和持仓漂移；对冲减同池等权并计 2% 年借券费。初始权益计入回撤。起始仓位为空，与 v2 一致。",
        f"- 相位配平排除：{', '.join(audit['excluded_for_phase_balance'])}；标签未成熟排除：{', '.join(audit['excluded_for_label_maturity'])}。IC 主表与组合使用相同测试日期，完整成熟日期 IC 另存。", "",
        "| 模型 | 表达 | 净收益 | 平均 Sharpe | 最差相位回撤 | 平均双向换手/周期 | 平均 RankIC | ICIR（周频年化） | 缺失收益填 -100% 时净收益 |", "|---|---|---|---|---|---|---|---|---|"]
    for row in summary:
        lines.append(f"| {names[row['model']]} | {row['expression']} | {row['total']:+.2%} | {row['sharpe_mean']:.2f} | {row['worst_phase_mdd']:.2%} | {row['avg_turnover']:.2%} | {row['rank_ic_mean']:.4f} | {row['rank_ic_ir_weekly']:.2f} | {row['stress_total']:+.2%} |")
    lines.extend(["", "ICIR = 周度 RankIC 均值 / 样本标准差 × √52。4 周标签彼此重叠，这不是显著性统计量。每相位仅 9 个周期，不能把点估计或较高收益解读为显著优越。所有 6 个模型与两种表达均保留，未根据结果选优。", "",
        "## 主结果的重要性", "", "冻结模型的 gain 为树分裂训练期增益，不代表因果贡献或稳健的样本外重要性。", "", "| 因子 | gain 占比 |", "|---|---|"])
    ranked = importance.sort_values("gain", ascending=False)
    for row in ranked.head(15).itertuples():
        lines.append(f"| `{row.factor}` | {row.gain / ranked.gain.sum():.2%} |")
    lines.extend(["", "## 边界与证据", "",
        "- 因子来自既有选择与预处理快照；这里只隔离模型拟合与评估，不能据此证明上游因子筛选完全无前视。",
        "- 缺失收益主口径填 0，同时必须查看 -100% 压力结果；绝对收益对缺失值假设敏感。健康监控参数稳定性未通过的原项目发现仍保留，本实验不据此启用预警动作。",
        "- 原存档 Ridge WF 的训练计划不同，只作历史参考；公平比较使用本次同窗口重训的 Ridge。",
        "- `combined_signal.csv` 保存 2026 全部日期预测，含未成熟尾部；组合与 IC 评估仅使用 audit 明确列出的成熟日期。",
        "- 本地 CLI 研究执行不等于 QuantStudio GUI 注册、提交或实盘交易。",
        "- 本次实验记录在 `runs/lightgbm_2026/`，含配置/输入哈希、运行时、模型、训练边界、命令和状态；`full_run=false` 仅指本实验未代替完整 v2 流程。", "",
        "复现：`E:/envs/LLM/python.exe scripts/lightgbm_2026.py`。", ""])
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts/lightgbm_2026.py")]
    (RUN / "cmd.txt").write_text(subprocess.list2cmdline(cmd) + "\n", encoding="utf-8")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    log = {"status": "running", "all_ok": False, "full_run": False,
        "scope": "independent retrospective LightGBM 2026 comparison; not the full v2 pipeline",
        "run_at": datetime.now().astimezone().isoformat(), "argv": cmd,
        "configuration": cfg, "config_sha256": sha(CONFIG), "script_sha256": sha(__file__),
        "runtime": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scikit-learn", "lightgbm")},
        "inputs": {p: sha(ROOT / p) for p in ("data/panel_for_platform.csv", "data/weekly_slim.csv", "data/upstream_summary.json", "scripts/engine_v2.py")}}
    save(RUN / "run_log.json", log)
    try:
        cache, factors = load_cache()
        dates = list(cache)
        year, mature, evaluation = evaluation_dates(dates, cfg["test_start"], cfg["test_end"], cfg["maturity_observations"])
        assert cfg["hold_observations"] == CFG["hold_observations"] == 4
        assert cfg["maturity_observations"] == CFG["maturity_observations"] == 5
        train = training_dates(dates, year[0], cfg["train_observations"], cfg["maturity_observations"])
        assert max(train) < cfg["test_start"]
        fitted, frozen, importance = fit_predict(cache, dates, train, year, factors, cfg["parameters"], RUN / "frozen")
        predictions = {"lightgbm_frozen": fitted["lightgbm"], "ridge_frozen": fitted["ridge"],
            "equal_weight": {d: cache[d]["ew"] for d in year},
            "ridge_archived_wf": {d: cache[d]["score"] for d in year},
            "lightgbm_rolling": {}, "ridge_rolling": {}}
        print(f"[frozen] {train[0]}..{train[-1]}, {frozen['train_rows']:,} rows; 2026={len(year)} dates", flush=True)
        rolling = []
        for j in range(0, len(year), cfg["update_step"]):
            block = year[j:j+cfg["update_step"]]
            train = training_dates(dates, block[0], cfg["train_observations"], cfg["maturity_observations"])
            result, record, _ = fit_predict(cache, dates, train, block, factors, cfg["parameters"], RUN / "rolling" / block[0])
            rolling.append(record)
            for name in ("lightgbm", "ridge"):
                predictions[name+"_rolling"].update(result[name])
            print(f"[rolling] {block[0]}..{block[-1]} train_last={train[-1]}", flush=True)
        score_rows = []
        for name, scores in predictions.items():
            for d, values in scores.items():
                score_rows.append(pd.DataFrame({"date": d, "symbol": cache[d]["sym"], "model": name, "score": values}))
        pd.concat(score_rows, ignore_index=True).to_csv(OUT / "combined_signal.csv", index=False)
        importance.to_csv(OUT / "feature_importance_frozen.csv", index=False)
        ic = ic_table(cache, predictions, mature)
        ic.to_csv(OUT / "weekly_ic.csv", index=False)
        summary, frames, stress = [], [], []
        for name, scores in predictions.items():
            series = ic.loc[ic.model.eq(name) & ic.date.isin(evaluation), "rank_ic"].dropna()
            for expression in ("long", "hedge"):
                frame = simulate(cache, evaluation, expression, scores=scores)
                frame["model"] = name
                frames.append(frame)
                stressed = simulate(cache, evaluation, expression, scores=scores, missing_fill=-1.)
                stress.append({"model": name, "expression": expression, **metrics(stressed)})
                summary.append({"model": name, "expression": expression, **metrics(frame),
                    "avg_turnover": float(frame.turnover.mean()), "rank_ic_observations": len(series),
                    "rank_ic_mean": float(series.mean()), "rank_ic_ir_weekly": float(series.mean()/series.std()*np.sqrt(52)),
                    "rank_ic_positive_share": float((series>0).mean()), "stress_total": metrics(stressed)["total"]})
        pd.concat(frames).to_csv(OUT / "trades.csv", index=False)
        save(OUT / "summary.json", summary)
        save(OUT / "missing_return_sensitivity.json", stress)
        audit = {"all_ok": True, "factor_count": len(factors), "eval_dates": evaluation,
            "all_prediction_dates": year, "all_mature_dates": mature,
            "excluded_for_phase_balance": mature[len(evaluation):],
            "excluded_for_label_maturity": [d for d in year if d not in mature],
            "frozen_fit": frozen, "rolling_fits": rolling,
            "point_in_time_model_fitting_only": True, "no_2026_parameter_selection": True,
            "retrospective_test": True, "upstream_feature_selection_independence_verified": False}
        save(OUT / "audit.json", audit)
        write_report(summary, audit, importance)
        log.update(status="completed", all_ok=True, completed_at=datetime.now().astimezone().isoformat(),
            outputs={p.name: sha(p) for p in OUT.iterdir() if p.is_file()})
        save(RUN / "run_log.json", log)
        for row in summary:
            print(f"[result] {row['model']} {row['expression']} net={row['total']:+.4%} IC={row['rank_ic_mean']:.4f}", flush=True)
        return 0
    except Exception as exc:
        log.update(status="failed", all_ok=False, error=str(exc))
        save(RUN / "run_log.json", log)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
