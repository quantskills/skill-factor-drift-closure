"""Hash the deliverable, including hidden project-local skill definitions."""
from datetime import datetime

from engine_v2 import ROOT, save, sha


def build():
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if any(part in {".git", "__pycache__", ".pytest_cache", ".venv"} for part in path.relative_to(ROOT).parts):
            continue
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    save(ROOT / "manifest.json", {"package": "period5_closed_loop_package", "version": "2.0.0",
        "built_at": datetime.now().astimezone().isoformat(), "authoritative_results": "results/v2/",
        "historical_results": "archive/legacy_v1/", "installation_scope": "project .agents/skills",
        "platform_boundary": "QuantStudio quantstudio-profile session executed the project pipeline with persisted input/output records; independent run id and GUI task registration/submission not exposed or performed",
        "entry_points": {"pipeline": "scripts/run_package.py", "monitor": "scripts/run_monitor_entries.py",
            "refit": ".agents/skills/skill-ml-factor-ensemble/scripts/ml_ensemble.py"},
        "n_files": len(files), "total_bytes": sum(f["bytes"] for f in files), "files": files})
    print(f"[manifest] {len(files)} files, hashes recorded")


if __name__ == "__main__":
    build()
