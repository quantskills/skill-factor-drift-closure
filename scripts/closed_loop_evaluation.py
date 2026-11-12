"""Validate the minimum shape of a drift-closure experiment and write an audit stub."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REQUIRED_PANEL = {"date", "symbol"}
REQUIRED_ALERTS = {"date", "status"}

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def header(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines()[0].split(",")]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--alerts", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    phead = header(args.panel) if args.panel.suffix.lower() in {".csv", ".txt"} and args.panel.is_file() else []
    ahead = header(args.alerts) if args.alerts.is_file() else []
    result = {
        "status": "shape_only",
        "panel": {"path": str(args.panel), "exists": args.panel.is_file(), "sha256": sha(args.panel) if args.panel.is_file() else None, "header": phead},
        "alerts": {"path": str(args.alerts), "exists": args.alerts.is_file(), "sha256": sha(args.alerts) if args.alerts.is_file() else None, "header": ahead},
        "checks": {
            "panel_primary_keys_present": REQUIRED_PANEL.issubset(set(phead)) if phead else False,
            "alerts_fields_present": REQUIRED_ALERTS.issubset(set(ahead)) if ahead else False,
            "warning_only_action_rule": "status" in ahead,
            "full_backtest_performed": False,
        },
        "note": "This adapter validates input shape and records hashes. A project-specific engine must implement mature-label gating, arm accounting and inference before making claims.",
    }
    (args.output / "run_record.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Shape validation is intentionally a runnable first stage; the adapter must
    # not pretend that a full backtest happened just because the headers pass.
    shape_ok = all(v for k, v in result["checks"].items() if k != "full_backtest_performed")
    return 0 if shape_ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
