"""Build a review-sized QuantStudio archive while preserving evidence and results."""
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "period5_package_quantstudio_slim.zip"
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv"}

def excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if any(x in path.relative_to(ROOT).parts for x in SKIP_PARTS):
        return True
    if rel == "data/panel_for_platform.csv":
        return True
    if "/panel_window.csv.gz" in rel:
        return True
    if rel.endswith("/health_panel.csv") or rel.endswith("/drift_panel.csv"):
        return True
    return False

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and not excluded(p) and p.name != "SLIM_ZIP_RECEIPT.json"]
    with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in files:
            zf.write(p, p.relative_to(ROOT).as_posix())
    receipt = {
        "archive": str(DEST), "source_root": str(ROOT), "file_count": len(files),
        "bytes": DEST.stat().st_size, "sha256": sha(DEST),
        "excluded_policy": ["data/panel_for_platform.csv", "*/panel_window.csv.gz", "*/health_panel.csv", "*/drift_panel.csv", "git/cache dirs"],
        "full_archive": str(ROOT.parent / "period5_package_quantstudio_verified.zip"),
    }
    (ROOT / "runs/quantstudio_platform_entry/SLIM_ZIP_RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))

if __name__ == "__main__":
    main()
