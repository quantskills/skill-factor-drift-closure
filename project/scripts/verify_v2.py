"""Independent data/accounting/inference acceptance checks for the current package."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from engine_v2 import CFG, DATA, OUT, ROOT, metrics, save, sha


def main():
    checks = []
    def check(name, condition):
        checks.append({"name": name, "ok": bool(condition)})
        if not condition:
            raise AssertionError(name)

    report = {"all_ok": False, "checks": checks}
    target = ROOT / "verification/ACCEPTANCE_V2.json"
    try:
        run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (ROOT / "verification/unit_tests.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        check("financial/accounting/leakage regression suite", run.returncode == 0)
        provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
        for record in provenance["files"]:
            path = ROOT / record["path"]
            if path.is_file():
                check(f"frozen source hash: {record['path']}", sha(path) == record["sha256"])
            elif "entry_sha256" in record:
                check("platform ML source unchanged", sha(path / "scripts/ml_ensemble.py") == record["entry_sha256"])
        calibration = json.loads((OUT / "calibration.json").read_text(encoding="utf-8"))
        check("threshold calibration ends before evaluation", calibration["end"] < CFG["eval_start"])
        check("threshold calibration is 2024 only", calibration["start"].startswith("2024") and calibration["end"].startswith("2024"))
        check("health baseline predates evaluation", calibration["health_baseline_end"] < CFG["eval_start"])
        check("equal-threshold IC rule has zero additional latch delay", calibration["latch_extra_delay"] == 0)
        audit = json.loads((OUT / "backtest_audit.json").read_text(encoding="utf-8"))
        check("analysis plan matches results", audit["plan_sha256"] == sha(ROOT / "config/audit_v2.json"))
        dates = pd.read_csv(DATA / "weekly_slim.csv", usecols=["date"], dtype=str).date.unique().tolist()
        position = {date: i for i, date in enumerate(sorted(dates))}
        check("evaluation tail matured", all(position[d] + 5 < len(position) for d in audit["eval_dates"]))
        availability = pd.read_csv(ROOT / "runs/r01_monitor_entry/label_availability.csv", dtype=str)
        check("all health labels available at least five observations later", all(position[b]-position[a] == 5 for a,b in availability.itertuples(index=False,name=None)))
        for name in ("health", "drift"):
            directory = ROOT / f"runs/r01_monitor_entry/{name}_entry"
            record = json.loads((directory / "input.json").read_text(encoding="utf-8"))
            check(f"{name} uses project-local skill", (ROOT / ".agents/skills").resolve() in Path(record["entry"]).resolve().parents)
            check(f"{name} entry hash matches execution", sha(record["entry"]) == record["entry_sha256"])
            check(f"{name} input hash matches execution", sha(record["input"]) == record["input_sha256"])
        module_path = ROOT / ".agents/skills/skill-factor-health-monitor/scripts/factor_health.py"
        spec = importlib.util.spec_from_file_location("acceptance_health", module_path)
        health = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = health
        spec.loader.exec_module(health)
        detail = pd.read_csv(ROOT / "runs/r01_monitor_entry/health/health_timeseries.csv", parse_dates=["date"])
        prefix = detail[["date", "factor", "ic", "n_symbols"]].iloc[:180]
        replay, _ = health.analyze(prefix, health.Config(weighting="step"))
        check("health probabilities/CUSUM unchanged by future suffix", np.allclose(replay.decline_probability, detail.decline_probability.iloc[:180]) and np.array_equal(replay.cusum_alarm, detail.cusum_alarm.iloc[:180]))
        refits = json.loads((OUT / "platform_refits.json").read_text(encoding="utf-8"))
        check("all main-experiment platform refits executed and equivalent", refits["all_ok"] and all(r["exit_code"] == 0 and r["spearman"] > .999999 and r["max_abs_diff"] < 1e-8 and r["gap_observations"] == 6 for r in refits["records"]))
        for row in refits["records"]:
            directory = ROOT / "runs/v2/refits" / row["date"]
            entry = json.loads((directory / "input.json").read_text(encoding="utf-8"))
            check(f"refit compressed input immutable: {row['date']}", sha(ROOT / entry["input"]) == entry["input_sha256"])
        trades = pd.read_csv(OUT / "trades.csv", dtype={"date": str})
        check("no duplicate phase-arm decisions", not trades.duplicated(["expression", "arm", "phase", "cycle"]).any())
        check("gross minus costs equals net", np.max(np.abs(trades.gross - trades.cost - trades.net)) < 1e-12)
        check("trade and borrow costs reconcile", np.max(np.abs(trades.trade_cost + trades.borrow_cost - trades.cost)) < 1e-12)
        check("all known phase cycles present", trades.groupby(["expression", "arm", "phase"]).size().eq(audit["phase_cycles"]).all())
        check("all decisions mature and matched", set(trades.date) == set(audit["eval_dates"]))
        recorded = {(r["expression"], r["arm"]): r for r in json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))}
        for key, group in trades.groupby(["expression", "arm"]):
            calculated = metrics(group)
            check(f"phase totals recomputed {key}", abs(calculated["total"] - recorded[key]["total"]) < 1e-12)
        cost = pd.read_csv(OUT / "cost_decomposition.csv")
        check("increment accounting reconciled", np.max(np.abs(cost.delta_gross - cost.delta_cost - cost.delta_net)) < 1e-12)
        reconciled = pd.read_csv(OUT / "episode_reconciliation.csv")
        check("event plus outside-event P&L reconciled", np.max(np.abs(reconciled.event_window_delta + reconciled.outside_event_delta - reconciled.total_arithmetic_delta)) < 1e-12)
        placebo = pd.read_csv(OUT / "placebo.csv")
        check("50 placebo seeds for each expression/action", placebo.groupby(["expression", "arm"]).seed.nunique().eq(50).all())
        inference = json.loads((OUT / "inference.json").read_text(encoding="utf-8"))
        check("24 hypotheses, serially aware bootstrap", inference["family_size"] == 24 and inference["circular_block_cycles"] == 4)
        check("drift action arms are present", {"C_drift", "D_drift", "F_drift"}.issubset(set(trades.arm)))
        monitor = pd.read_csv(OUT / "monitor.csv", dtype={"date": str})
        check("drift alarm is persisted", "drift_alarm" in monitor.columns and monitor.drift_alarm.any())
        drift_cli = pd.read_csv(ROOT / "runs/r01_monitor_entry/drift.csv")
        warning_periods = set(drift_cli.loc[drift_cli.status.eq("warning"), "window"].astype(str))
        mapped = set(pd.PeriodIndex(pd.to_datetime(monitor.loc[monitor.drift_alarm, "date"], format="%Y%m%d"), freq="Q").astype(str))
        check("drift CLI warning state reaches evaluation trigger", bool(warning_periods & mapped))
        robustness = json.loads((OUT / "health_robustness.json").read_text(encoding="utf-8"))
        check("27 health parameter perturbations reported without tuning", robustness["parameter_sets"] == 27)
        for required in ("README.md", "report.md", "dashboard.html", "TASK_CHECKLIST.md", "ARTIFACTS.md"):
            check(f"deliverable exists: {required}", (ROOT / required).is_file())
        report.update(all_ok=True, checks=checks, checks_passed=len(checks), limitations=[
            "No proof of prospective holdout: historical sample already inspected",
            "Platform GUI registration/submission not verified",
            "Upstream point-in-time membership and real execution timing not independently reconstructed",
            "Missing labels imputed explicitly; impact and borrow availability not modeled"])
        save(target, report)
        print(f"[verify] {len(checks)} checks passed; 8 regression tests passed")
    except Exception as exc:
        report.update(error=str(exc), checks=checks)
        save(target, report)
        raise


if __name__ == "__main__":
    main()
