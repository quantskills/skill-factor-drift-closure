"""Reproduce the current project-local v2; stop immediately on failure."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import datetime

from engine_v2 import ROOT, save, sha

STEPS = {
    "monitor": ("run_monitor_entries.py", "runs/r01_monitor_entry/run_log.json"),
    "robustness": ("health_robustness_v2.py", "results/v2/health_robustness.json"),
    "backtest": ("engine_v2.py", "results/v2/backtest_audit.json"),
    "analysis": ("analyze_v2.py", "results/v2/inference.json"),
    "report": ("report_v2.py", "report.md"),
    "verify": ("verify_v2.py", "verification/ACCEPTANCE_V2.json"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--only", nargs="+", choices=[*STEPS, "manifest"], default=[*STEPS, "manifest"])
    args = ap.parse_args()
    rec = ROOT / "runs/_pipeline"
    rec.mkdir(parents=True, exist_ok=True)
    log_path = rec / "run_log.json"
    if log_path.exists():
        (rec / "run_log_previous.json").write_bytes(log_path.read_bytes())
    full = args.only == [*STEPS, "manifest"]
    log = {"run_at": datetime.now().astimezone().isoformat(), "requested_steps": args.only,
        "full_run": full, "status": "running", "all_ok": False, "steps": [],
        "python": args.python, "scope": "v2 only; archive/legacy_v1 retained",
        "runtime": {name: importlib.metadata.version(name) for name in
                    ("numpy", "pandas", "scipy", "matplotlib", "scikit-learn")}}
    save(log_path, log)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    try:
        for step in args.only:
            if step == "manifest":
                continue
            script, marker = STEPS[step]
            directory = rec / f"v2_{step}"
            directory.mkdir(parents=True, exist_ok=True)
            cmd = [args.python, "-u", str(ROOT / "scripts" / script)]
            (directory / "cmd.txt").write_text(subprocess.list2cmdline(cmd) + "\n", encoding="utf-8")
            save(directory / "input.json", {"argv": cmd, "script_sha256": sha(cmd[-1]),
                "plan_sha256": sha(ROOT / "config/audit_v2.json"),
                "local_data_provenance_sha256": sha(ROOT / "data/provenance.json")})
            print(f"[start] {step}", flush=True)
            with (directory / "stdout.log").open("w", encoding="utf-8") as stream:
                process = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env)
                for line in process.stdout:
                    stream.write(line)
                    stream.flush()
                    print(line, end="", flush=True)
                process.wait()
            ok = process.returncode == 0 and (ROOT / marker).is_file()
            status = {"step": step, "exit_code": process.returncode, "ok": ok,
                "marker": marker, "marker_sha256": sha(ROOT / marker) if (ROOT / marker).exists() else None}
            if ok and step in ("monitor", "backtest", "verify"):
                status["ok"] = bool(json.loads((ROOT / marker).read_text(encoding="utf-8")).get("all_ok"))
            log["steps"].append(status)
            save(directory / "status.json", status)
            save(log_path, log)
            if not status["ok"]:
                raise RuntimeError(f"{step} failed; see {directory / 'stdout.log'}")
        if "manifest" in args.only:
            log["steps"].append({"step": "manifest", "ok": True, "marker": "manifest.json"})
        log.update(status="completed", all_ok=True, completed_at=datetime.now().astimezone().isoformat())
        save(log_path, log)
        if "manifest" in args.only:
            from build_manifest import build
            build()
        print(f"[complete] all_ok=True full_run={full} steps={len(log['steps'])}", flush=True)
        return 0
    except Exception as exc:
        log.update(status="failed", all_ok=False, error=str(exc))
        save(log_path, log)
        print(f"[failed] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
