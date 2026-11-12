"""Independent checks for the one-week label comparison branch."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v3_one_week"


def main() -> None:
    checks = []
    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})
        if not ok:
            raise AssertionError(name)

    provenance = json.loads((ROOT / "data/one_week/provenance.json").read_text(encoding="utf-8"))
    check("one-week label contract", provenance["label"] == "open(t+2)/open(t+1)-1, one-week forward return")
    check("maturity remains five observations", provenance["maturity_observations"] == 5)
    check("holding period is one observation", provenance["holding_observations"] == 1)
    metrics = pd.DataFrame(json.loads((OUT / "metrics.json").read_text(encoding="utf-8")))
    check("20 metric cells present", len(metrics) == 20 and set(metrics.arm) == {"A", "B", "A_ew", "C_ic", "D_ic", "F_ic", "C_health", "D_health", "F_health", "C_psi"})
    trades = pd.read_csv(OUT / "trades.csv", dtype={"date": str})
    check("gross-cost-net reconciles", np.max(np.abs(trades.gross - trades.cost - trades.net)) < 1e-12)
    check("no duplicate phase cycles", not trades.duplicated(["expression", "arm", "phase", "cycle"]).any())
    inference = json.loads((OUT / "inference.json").read_text(encoding="utf-8"))
    check("18 hypotheses and 22 matched cycles", inference["family_size"] == 18 and inference["cycles"] == 22)
    refs = json.loads((OUT / "platform_refits.json").read_text(encoding="utf-8"))
    check("platform refits equivalent", refs["all_ok"] and all(r["exit_code"] == 0 and r["spearman"] > .999999 and r["max_abs_diff"] < 1e-8 for r in refs["records"]))
    audit = json.loads((OUT / "backtest_audit.json").read_text(encoding="utf-8"))
    check("88 evaluation dates", len(audit["eval_dates"]) == 88 and audit["phase_cycles"] == 22)
    check("v2 remains separate", (ROOT / "results/v2/metrics.json").is_file() and (ROOT / "results/v2/inference.json").is_file())
    result = {"all_ok": True, "checks": checks, "checks_passed": len(checks),
              "interpretation": "exploratory retrospective one-week label comparison; v2 remains authoritative"}
    (ROOT / "verification/ONE_WEEK_LABEL_VERIFY.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[one-week verify] {len(checks)} checks passed")


if __name__ == "__main__":
    main()
