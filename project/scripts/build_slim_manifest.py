"""Write a manifest for the review-sized archive."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manifest_slim.json"
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv"}

def excluded(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    return (p.name in {"manifest_slim.json", "SLIM_ZIP_RECEIPT.json"}
            or any(x in p.relative_to(ROOT).parts for x in SKIP_PARTS)
            or rel == "data/panel_for_platform.csv"
            or "/panel_window.csv.gz" in rel
            or rel.endswith("/health_panel.csv")
            or rel.endswith("/drift_panel.csv"))

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

def main() -> None:
    fs = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and not excluded(p)]
    OUT.write_text(json.dumps({"package": "period5_package_quantstudio_slim", "n_files": len(fs), "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in fs]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[slim-manifest] {len(fs)} files")

if __name__ == "__main__": main()
