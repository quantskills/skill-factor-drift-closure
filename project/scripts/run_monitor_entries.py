"""Run installed, unmodified QuantSkills monitoring CLIs on project data.

Health observations are dated when the five-week label becomes available.
These diagnostic runs do not replace the frozen triggers used in the backtest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=PKG / "data" / "weekly_slim.csv")
    ap.add_argument("--skills-root", type=Path, default=PKG / ".agents" / "skills",
                    help="Project-local skill directory; defaults to .agents/skills")
    ap.add_argument("--run-root", type=Path, default=PKG / "runs" / "r01_monitor_entry",
                    help="Output directory for this monitor run")
    args = ap.parse_args()
    root = args.run_root
    root.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(args.source, dtype={"date": str, "symbol": str,
        "in_universe": "boolean", "entry_tradable": "boolean"}, low_memory=False)
    dates = sorted(panel.date.unique())
    maturity = dict(zip(dates[:-5], dates[5:]))
    eligible = panel[panel.in_universe.eq(True) & panel.entry_tradable.eq(True)].copy()
    health = eligible.dropna(subset=["score_wf", "fwd_ret"]).copy()
    health["available_date"] = health.date.map(maturity)
    health = health.dropna(subset=["available_date"])
    audit = health[["date", "available_date"]].drop_duplicates().sort_values("date")
    audit.to_csv(root / "label_availability.csv", index=False)
    pos = {date: i for i, date in enumerate(dates)}
    assert all(pos[b] - pos[a] == 5 for a, b in audit.itertuples(index=False, name=None))
    health_input = pd.DataFrame({
        "date": pd.to_datetime(health.available_date, format="%Y%m%d").dt.strftime("%Y-%m-%d"),
        "symbol": health.symbol, "factor": "ridge_score_wf",
        "value": health.score_wf, "next_return": health.fwd_ret,
    }).sort_values(["symbol", "date"], ascending=[True, False])
    health_input.to_csv(root / "health_panel.csv", index=False)
    drift_input = eligible.loc[eligible.date.ge("20240101"), ["date", "symbol", "score_wf"]].copy()
    drift_input["date"] = pd.to_datetime(drift_input.date, format="%Y%m%d").dt.strftime("%Y-%m-%d")
    drift_input = drift_input.sort_values(["symbol", "date"], ascending=[True, False])
    drift_input.to_csv(root / "drift_panel.csv", index=False)
    common = {"source": str(args.source), "source_sha256": digest(args.source),
              "maturity_weeks": 5, "time_unit": "weekly observations, not daily",
              "use": "health CLI probabilities/CUSUM feed v2 health arms; original v1 triggers retained only in archive"}
    definitions = {
        "health": ("skill-factor-health-monitor", "factor_health.py",
                   "7b00ea3315abc2cb1a0f1e40af859164896613fe",
                   ["--panel", str(root / "health_panel.csv"), "--output", str(root / "health"), "--weighting", "step"]),
        "drift": ("skill-factor-drift-monitor", "monitor_factor_drift.py",
                  "cf5ab22397c1c3f8621c6bc06089af2620fbe1a8",
                  ["--input", str(root / "drift_panel.csv"), "--factors", "score_wf",
                   "--baseline-end", "2024-12-27", "--freq", "Q", "--output", str(root / "drift")]),
    }
    records = {}
    for name, (skill, script_name, revision, cli_args) in definitions.items():
        directory = root / f"{name}_entry"
        directory.mkdir(exist_ok=True)
        entry = args.skills_root / skill / "scripts" / script_name
        cmd = [sys.executable, str(entry), *cli_args]
        (directory / "cmd.txt").write_text(subprocess.list2cmdline(cmd) + "\n", encoding="utf-8")
        save(directory / "argv.json", {"argv": cmd})
        input_path = root / f"{name}_panel.csv"
        save(directory / "input.json", {**common, "entry": str(entry), "entry_sha256": digest(entry),
            "repository": f"https://github.com/quantskills/{skill}", "source_revision": revision,
            "input": str(input_path), "input_sha256": digest(input_path)})
        env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        (directory / "stdout.log").write_text(result.stdout + "\n--- stderr ---\n" + result.stderr, encoding="utf-8")
        records[name] = {"exit_code": result.returncode, "ok": result.returncode == 0,
                         "record": str(directory.relative_to(PKG))}
        print(f"{name}: exit={result.returncode}")
        if result.returncode:
            print(result.stderr)
    if not all(r["ok"] for r in records.values()):
        save(root / "run_log.json", {"steps": records, "all_ok": False})
        return 1
    detail = pd.read_csv(root / "health" / "health_timeseries.csv")
    assert pd.to_datetime(detail.date).min().year > 2000, "Upstream numeric-date parsing error"
    expected = health_input.groupby("date").apply(
        lambda group: group.value.corr(group.next_return, method="spearman"), include_groups=False)
    observed = detail.set_index("date").ic
    overlap = observed.index.intersection(expected.index)
    ic_error = float(np.max(np.abs(observed.loc[overlap] - expected.loc[overlap])))
    assert len(overlap) == len(expected) and ic_error < 1e-10
    assert pd.to_datetime(detail.iloc[119].date) < pd.Timestamp("2025-01-03"), "Health baseline crosses evaluation start"
    summary = pd.read_csv(root / "health" / "health_summary.csv").to_dict("records")
    drift = pd.read_csv(root / "drift.csv")
    payload = {"run_at": datetime.now().astimezone().isoformat(), **common,
               "steps": records, "all_ok": True, "maturity_all_ok": True,
               "health_ic_max_abs_error": ic_error, "health_observations": len(detail),
               "health_baseline_last_available_date": detail.iloc[119].date,
               "health_summary": summary, "drift_status_counts": drift.status.value_counts().to_dict(),
               "limitations": ["Health default windows 20/60/120 count weeks on this panel",
                   "New health algorithm differs from frozen 13-week IC median threshold",
                   "Drift uses 2024 baseline and no forward-return column",
                   "Only results/v2 health arms use these CLI alerts; archived v1 returns do not",
                   "Installed in project .agents/skills; QuantStudio GUI registration not verified"]}
    save(root / "run_log.json", payload)
    save(PKG / "verification" / "MONITOR_ENTRY_VERIFY.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
