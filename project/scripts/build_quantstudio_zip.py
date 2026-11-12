"""Build the QuantStudio delivery archive from the current project tree."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "period5_package_quantstudio_verified.zip"
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv"}
SKIP_FILES = {"ZIP_RECEIPT.json"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    receipt_path = ROOT / "runs" / "quantstudio_platform_entry" / "ZIP_RECEIPT.json"
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name in SKIP_FILES or any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    receipt_path.write_text(json.dumps({
        "source_root": str(ROOT),
        "excluded": sorted(SKIP_PARTS),
        "note": "Archive receipt for the QuantStudio project package; archive hash is printed after creation.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name not in SKIP_FILES and not any(part in SKIP_PARTS for part in p.relative_to(ROOT).parts)]
    compression = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(DEST, "w", compression=compression, compresslevel=6) as zf:
        for path in files:
            arc = path.relative_to(ROOT).as_posix()
            # Existing parquet/csv.gz intermediates are already compressed; keep them intact.
            if path.suffix == ".gz" or path.suffix in {".parquet", ".zip", ".png", ".jpg"}:
                zf.write(path, arcname=arc, compress_type=zipfile.ZIP_STORED)
            else:
                zf.write(path, arcname=arc)
        receipt = {
            "archive": str(DEST),
            "source_root": str(ROOT),
            "file_count": len(files),
            "sha256": None,
            "excluded": sorted(SKIP_PARTS),
            "external_quantstudio_session": "E:/QuantStudio-Data/sessions/.../session.jsonl.zstd (referenced by platform_entry_record.json; not copied into package)",
        }
    receipt["sha256"] = sha(DEST)
    receipt["bytes"] = DEST.stat().st_size
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(DEST), "file_count": len(files), "bytes": DEST.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
