"""Matched-calendar inference, accounting, episode and recovery audits."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine_v2 import CFG, OUT, ROOT, cycle_series, episodes, metrics, save


def bh(p):
    p = np.asarray(p)
    order = np.argsort(p)
    adjusted = np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]
    result = np.empty_like(p)
    result[order] = np.minimum(1, adjusted)
    return result


def bootstrap(mat, draws, block, rng):
    n = len(mat)
    starts = rng.integers(0, n, size=(draws, int(np.ceil(n / block))))
    index = ((starts[:, :, None] + np.arange(block)) % n).reshape(draws, -1)[:, :n]
    return mat[index].mean(axis=1)


def inference(mat):
    observed = mat.mean(axis=0)
    rng = np.random.default_rng(CFG["seed"])
    results = []
    for block in (1, CFG["bootstrap_block_cycles"]):
        boot = bootstrap(mat, CFG["bootstrap_draws"], block, rng)
        # Null-centered bootstrap. Compare to the observed statistic, never to zero.
        null = boot - observed
        p = (1 + (np.abs(null) >= np.abs(observed)).sum(axis=0)) / (len(boot) + 1)
        rc_positive = (1 + (null.max(axis=1) >= observed.max()).sum()) / (len(boot) + 1)
        rc_negative = (1 + ((-null).max(axis=1) >= (-observed).max()).sum()) / (len(boot) + 1)
        se = boot.std(axis=0, ddof=1)
        results.append({"block": block, "p": p, "bh": bh(p), "rc_positive": rc_positive,
            "rc_negative": rc_negative, "ci_lo": np.quantile(boot, .025, axis=0),
            "ci_hi": np.quantile(boot, .975, axis=0), "mde80": 2.8 * se})
    return observed, results


def main():
    trades = pd.read_csv(OUT / "trades.csv", dtype={"date": str})
    monitors = pd.read_csv(OUT / "monitor.csv", dtype={"date": str}).set_index("date")
    cells, series = [], []
    base = {}
    for expr, expression in trades.groupby("expression"):
        baseline = expression[expression.arm.eq("A")].set_index(["phase", "cycle"])
        base[expr] = baseline
        for arm, frame in expression.groupby("arm"):
            if arm == "A":
                continue
            paired = frame.set_index(["phase", "cycle"]).join(baseline[["net", "gross", "cost"]], rsuffix="_base", validate="one_to_one")
            assert not paired.net_base.isna().any()
            delta = (paired.net - paired.net_base).groupby("cycle").mean().sort_index()
            cells.append((expr, arm))
            series.append(delta)
    mat = pd.concat(series, axis=1)
    assert not mat.isna().any().any()
    observed, tests = inference(mat.to_numpy())
    rows = []
    for j, (expr, arm) in enumerate(cells):
        rows.append({"expression": expr, "arm": arm, "cycles": len(mat), "delta_mean": observed[j],
            "delta_arith": observed[j] * len(mat),
            "p_iid": tests[0]["p"][j], "p_block": tests[1]["p"][j],
            "p_bh_iid": tests[0]["bh"][j], "p_bh_block": tests[1]["bh"][j],
            "p_bh_conservative": max(tests[0]["bh"][j], tests[1]["bh"][j]),
            "ci_block_lo": tests[1]["ci_lo"][j], "ci_block_hi": tests[1]["ci_hi"][j],
            "mde80_per_cycle": max(tests[0]["mde80"][j], tests[1]["mde80"][j])})
    pd.DataFrame(rows).to_csv(OUT / "multiplicity.csv", index=False)
    save(OUT / "inference.json", {"family_size": len(cells), "cycles": len(mat),
        "bootstrap_draws": CFG["bootstrap_draws"], "circular_block_cycles": CFG["bootstrap_block_cycles"],
        "rc_positive_iid": tests[0]["rc_positive"], "rc_negative_iid": tests[0]["rc_negative"],
        "rc_positive_block": tests[1]["rc_positive"], "rc_negative_block": tests[1]["rc_negative"],
        "min_bh_conservative": min(r["p_bh_conservative"] for r in rows),
        "n_bh_10": sum(r["p_bh_conservative"] <= .1 for r in rows),
        "method": "nonstudentized White-style maximum mean: centered resamples compared to observed max; IID + circular block; descriptive on a retrospectively revised historical sample"})
    accounting, episode_rows, recovery_rows, attribution = [], [], [], []
    monitor_dates = monitors.index[monitors.index >= CFG["eval_start"]]
    for expr, expression in trades.groupby("expression"):
        baseline = base[expr]
        for arm, frame in expression.groupby("arm"):
            if arm == "A":
                continue
            paired = frame.set_index(["phase", "cycle"]).join(baseline[["net", "gross", "cost"]], rsuffix="_base", validate="one_to_one")
            paired["delta"] = paired.net - paired.net_base
            dg = float((paired.gross - paired.gross_base).sum() / 4)
            dc = float((paired.cost - paired.cost_base).sum() / 4)
            dn = float(paired.delta.sum() / 4)
            assert abs(dg - dc - dn) < 1e-12
            accounting.append({"expression": expr, "arm": arm, "delta_gross": dg, "delta_cost": dc,
                "delta_net": dn, "cost_saving_share": -dc / dn if abs(dn) > 1e-12 else None})
            if arm in ("B", "A_ew"):
                continue
            monitor_col = (
                "health_alarm" if "health" in arm
                else "drift_alarm" if "drift" in arm
                else "psi_alarm" if "psi" in arm
                else "ic_alarm"
            )
            events = episodes(monitors.loc[monitor_dates, monitor_col])
            for index, event in enumerate(events):
                affected = paired[paired.date.ge(event["start"])]
                if event["end_exclusive"]:
                    affected = affected[affected.date.lt(event["end_exclusive"])]
                # Quantify realized action P&L; right-censored means unresolved signal, not unknown past returns.
                gain = float(affected.delta.sum() / 4)
                episode_rows.append({"expression": expr, "arm": arm, "episode": index, **event,
                    "phase_decisions": len(affected), "delta_net": gain,
                    "verdict": "unexposed" if len(affected) == 0 else "gain" if gain > 0 else "loss" if gain < 0 else "neutral"})
            completed = [e["duration_observations"] for e in events if not e["right_censored"]]
            recovery_rows.append({"expression": expr, "arm": arm, "episodes": len(events),
                "completed": len(completed), "right_censored": sum(e["right_censored"] for e in events),
                "completed_mean_observations": float(np.mean(completed)) if completed else None,
                "completed_mean_is_survival_biased": True,
                "observed_mean_including_lower_bounds": float(np.mean([e["duration_observations"] for e in events])),
                "extra_latch_observations": 0 if monitor_col == "ic_alarm" else None,
                "note": "weeks are weekly observation counts, not calendar weeks; no causal claim about time saved"})
            # Descriptive association only: down is an ex-post outcome, not an implementable predictor.
            delta_cycle = paired.delta.groupby("cycle").mean()
            if arm.startswith("C"):
                x = (paired.exposure - 1).groupby("cycle").mean().to_numpy()
            else:
                x = paired.alarm.groupby("cycle").mean().to_numpy(dtype=float)
            down = (baseline.net.groupby("cycle").mean() < 0).to_numpy(dtype=float)
            X = np.column_stack([np.ones(len(x)), x, x * down])
            y = delta_cycle.to_numpy()
            coeff = np.linalg.pinv(X) @ y
            error = y - X @ coeff
            inv = np.linalg.pinv(X.T @ X)
            vcov = inv @ ((X * error[:, None] ** 2).T @ X) @ inv * len(x) / (len(x) - 3)
            sd = np.sqrt(np.maximum(np.diag(vcov), 0))
            attribution.append({"expression": expr, "arm": arm, "coef_action": coeff[1], "coef_action_down": coeff[2],
                "t_action": coeff[1] / sd[1] if sd[1] > 0 else None,
                "t_action_down": coeff[2] / sd[2] if sd[2] > 0 else None,
                "rank": int(np.linalg.matrix_rank(X)), "causal": False,
                "note": "ex-post down-period split; not proof of beta timing or alpha repair"})
    pd.DataFrame(accounting).to_csv(OUT / "cost_decomposition.csv", index=False)
    pd.DataFrame(episode_rows).to_csv(OUT / "episodes.csv", index=False)
    save(OUT / "recovery.json", recovery_rows)
    save(OUT / "attribution.json", attribution)
    event_df = pd.DataFrame(episode_rows)
    precision = []
    for (expr, arm), group in event_df.groupby(["expression", "arm"]):
        exposed = group[group.phase_decisions.gt(0)]
        wins = exposed[exposed.delta_net.gt(0)].delta_net
        losses = -exposed[exposed.delta_net.lt(0)].delta_net
        hit_mean, miss_mean = wins.mean(), losses.mean()
        precision.append({"expression": expr, "arm": arm, "episodes": len(group),
            "exposed_episodes": len(exposed), "unexposed_episodes": int(group.phase_decisions.eq(0).sum()),
            "hits": len(wins), "losses": len(losses), "neutral": int(exposed.delta_net.eq(0).sum()),
            "precision_descriptive": len(wins) / (len(wins) + len(losses)) if len(wins) + len(losses) else None,
            "gain_sum": wins.sum(), "false_alarm_cost": losses.sum(),
            "breakeven_precision": miss_mean / (hit_mean + miss_mean) if len(wins) and len(losses) else None,
            "definition": "positive/negative action P&L; not independently labeled drift detection accuracy"})
    pd.DataFrame(precision).to_csv(OUT / "false_alarm.csv", index=False)
    # P&L after alert exit is reported rather than silently discarded (persistent refits and trading costs).
    residual = []
    for (expr, arm), group in trades.groupby(["expression", "arm"]):
        if arm in ("A", "B", "A_ew"):
            continue
        paired = group.set_index(["phase", "cycle"]).join(base[expr][["net"]], rsuffix="_base")
        total = float((paired.net - paired.net_base).sum() / 4)
        in_episode = float(event_df[event_df.expression.eq(expr) & event_df.arm.eq(arm)].delta_net.sum())
        residual.append({"expression": expr, "arm": arm, "total_arithmetic_delta": total,
            "event_window_delta": in_episode, "outside_event_delta": total - in_episode})
    pd.DataFrame(residual).to_csv(OUT / "episode_reconciliation.csv", index=False)
    print(f"[analysis] {len(cells)} hypotheses, {len(mat)} cycles; accounting and censored episodes reconciled")


if __name__ == "__main__":
    main()
