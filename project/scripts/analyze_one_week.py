"""Run the existing v2 accounting/inference audit against v3 one-week results."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import engine_v2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v3_one_week"


def main() -> None:
    engine_v2.OUT = OUT
    engine_v2.CFG = json.loads((ROOT / "config" / "audit_v3_one_week.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("analyze_one_week_impl", ROOT / "scripts" / "analyze_v2.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.main()


if __name__ == "__main__":
    main()
