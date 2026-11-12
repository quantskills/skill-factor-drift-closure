"""Run the v2 closed-loop engine with a derived one-week return label.

This is a comparison branch. It writes only under results/v3_one_week and runs
the same actions, accounting, inference and placebo logic with a one-week label.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "engine_v2.py"
OUT = ROOT / "results" / "v3_one_week"
DATA = ROOT / "data" / "one_week"
RUNS = ROOT / "runs" / "v3_one_week_monitor"


def save_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    # The v2 engine is intentionally loaded after its module constants are patched.
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine_one_week_impl", SRC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.DATA = DATA
    mod.OUT = OUT
    mod.CFG = json.loads((ROOT / "config" / "audit_v3_one_week.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    # The monitor entry is run against the derived one-week snapshot. Its health
    # output is then consumed by engine_v2-compatible monitor loading.
    cmd = [sys.executable, str(ROOT / "scripts" / "run_monitor_entries.py"),
           "--source", str(DATA / "weekly_slim.csv"), "--run-root", str(RUNS)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (ROOT / "runs" / "v3_one_week_monitor.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(proc.stderr[-2000:])
    # Point the implementation to the branch monitor output.
    mod.ROOT = ROOT
    mod.DATA = ROOT / "data"
    mod.OUT = OUT
    def load_cache_one_week():
        factors = json.loads((ROOT / "data" / "upstream_summary.json").read_text(encoding="utf-8"))["factors"]["selected_names"]
        weekly = pd.read_csv(DATA / "weekly_slim.csv", dtype={"date": str, "symbol": str,
            "in_universe": "boolean", "entry_tradable": "boolean"}, low_memory=False)
        raw = pd.read_csv(ROOT / "data" / "panel_for_platform.csv", dtype={"date": str, "symbol": str})
        raw = raw.drop(columns="fwd_ret").merge(weekly, on=["date", "symbol"], validate="one_to_one")
        cache = {}
        for date, group in raw.groupby("date", sort=True):
            x = group[factors].to_numpy(dtype=float)
            cache[date] = {"sym": group.symbol.to_numpy(), "X": x,
                "score": group.score_wf.to_numpy(dtype=float),
                "ew": group[factors].mean(axis=1).to_numpy(dtype=float),
                "ret": group.fwd_ret.to_numpy(dtype=float),
                "elig": (group.in_universe.fillna(False) & group.entry_tradable.fillna(False)).to_numpy(dtype=bool)}
        return cache, factors
    mod.load_cache = load_cache_one_week

    def platform_refits_one_week(cache, factors, models, starts):
        cli = ROOT / ".agents/skills/skill-ml-factor-ensemble/scripts/ml_ensemble.py"
        records, dates = [], list(cache)
        refit_root = ROOT / "runs" / "v3_one_week_refits"
        for date in sorted(set(starts)):
            i = dates.index(date)
            end = i - mod.CFG["maturity_observations"]
            train_dates = dates[end - mod.CFG["train_observations"]:end]
            directory = refit_root / date
            directory.mkdir(parents=True, exist_ok=True)
            window = directory / "panel_window.csv.gz"
            frames = []
            for d in dates[end - mod.CFG["train_observations"]:i + 1]:
                c = cache[d]
                f = pd.DataFrame(c["X"], columns=factors)
                f.insert(0, "symbol", c["sym"]); f.insert(0, "date", d); f["fwd_ret"] = c["ret"]
                frames.append(f)
            pd.concat(frames, ignore_index=True).to_csv(window, index=False, compression={"method": "gzip", "compresslevel": 1})
            cmd = [sys.executable, str(cli), "--panel-csv", str(window), "--factors", ",".join(factors),
                   "--model", "ridge", "--horizon", "5", "--train-window", "161", "--step", "4",
                   "--embargo", "0", "--out", str(directory / "oos_scores.csv"), "--report", str(directory / "report.md")]
            mod.recorded_cli(cmd, directory, {"date": date, "train_first": train_dates[0], "train_last": train_dates[-1],
                "train_observations": len(train_dates), "gap_observations": i - dates.index(train_dates[-1]),
                "input": str(window.relative_to(ROOT)), "input_sha256": mod.sha(window),
                "origin": "project-local unchanged copy of QuantStudio skill; horizon=5 retained to match five-observation maturity gate"})
            scores = pd.read_csv(directory / "oos_scores.csv", dtype={"symbol": str}).set_index("symbol").score
            w, xm, ym = models.fit(date); c = cache[date]
            predicted = pd.Series((c["X"] - xm) @ w + ym, index=c["sym"])
            both = pd.DataFrame({"cli": scores, "fast": predicted}).dropna()
            error = float((both.cli - both.fast).abs().max()); rho = float(both.cli.corr(both.fast, method="spearman"))
            if error >= 1e-8 or rho <= .999999: raise AssertionError((date, rho, error))
            rec = {"date": date, "exit_code": 0, "spearman": rho, "max_abs_diff": error,
                   "train_last": train_dates[-1], "gap_observations": 6, "rows": len(both)}
            mod.save(directory / "verification.json", rec); records.append(rec)
            print(f"[one-week refit] {date}: rho={rho:.9f} error={error:.2g}")
        mod.save(OUT / "platform_refits.json", {"all_ok": True, "records": records})
        return records
    mod.platform_refits = platform_refits_one_week
    # Its monitor loader uses the fixed v2 path; provide a branch-local copy.
    monitor_dir = OUT / "_monitor_entry"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(RUNS / "health", monitor_dir / "health", dirs_exist_ok=True)
    # The drift CLI writes its CSV/JSON at the run root; health writes a folder.
    original_monitor = ROOT / "runs" / "r01_monitor_entry"
    backup = ROOT / "runs" / "_r01_monitor_entry_backup"
    if backup.exists():
        shutil.rmtree(backup)
    if original_monitor.exists():
        original_monitor.rename(backup)
    RUNS.rename(original_monitor)
    try:
        mod.main()
    finally:
        if original_monitor.exists():
            original_monitor.rename(RUNS)
        if backup.exists():
            backup.rename(original_monitor)
    # Keep branch metadata explicit and make the label definition machine-readable.
    save_json(OUT / "branch_audit.json", {
        "label": "open(t+2)/open(t+1)-1",
        "holding_observations": 1,
        "maturity_observations": 5,
        "source": str(DATA / "weekly_slim.csv"),
        "v2_untouched": True,
        "interpretation": "retrospective one-week label comparison, not confirmation",
    })
    print(f"[one-week] complete: {OUT}")


if __name__ == "__main__":
    main()
