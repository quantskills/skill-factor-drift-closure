"""Create the project-local one-week label snapshot without modifying v2 data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "one_week"
SOURCE_BARS = Path(r"C:\Users\DELL\Documents\QuantSkills\output\strategy2026\data\weekly_bars.csv")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not SOURCE_BARS.is_file():
        raise FileNotFoundError(f"missing source weekly bars: {SOURCE_BARS}")
    base = pd.read_csv(ROOT / "data" / "weekly_slim.csv", dtype={"date": str, "symbol": str})
    bars = pd.read_csv(SOURCE_BARS, dtype={"date": str, "symbol": str})
    bars = bars.sort_values(["symbol", "date"])
    bars["fwd_ret1"] = bars.groupby("symbol").open.shift(-2) / bars.groupby("symbol").open.shift(-1) - 1
    label = bars[["date", "symbol", "fwd_ret1"]]
    out = base.drop(columns=["fwd_ret"]).merge(label, on=["date", "symbol"], how="left", validate="one_to_one")
    out = out.rename(columns={"fwd_ret1": "fwd_ret"}).sort_values(["date", "symbol"])
    target = OUT / "weekly_slim.csv"
    out.to_csv(target, index=False)
    # Validate that the adapter is reconstructing the intended one-week contract.
    expected = bars["fwd_ret1"].notna().mean()
    observed = out["fwd_ret"].notna().mean()
    if abs(expected - observed) > 1e-12:
        raise AssertionError((expected, observed))
    meta = {
        "label": "open(t+2)/open(t+1)-1, one-week forward return",
        "maturity_observations": 5,
        "holding_observations": 1,
        "source_bars": str(SOURCE_BARS),
        "source_bars_sha256": sha(SOURCE_BARS),
        "source_weekly_slim_sha256": sha(ROOT / "data" / "weekly_slim.csv"),
        "output_sha256": sha(target),
        "rows": len(out),
        "label_coverage": observed,
        "note": "Derived comparison snapshot; v2 frozen four-week label is unchanged.",
    }
    (OUT / "provenance.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
