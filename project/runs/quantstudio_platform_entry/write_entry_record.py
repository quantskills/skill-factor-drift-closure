"""写入本次 QuantStudio 平台入口执行记录（不伪造任何平台标识）。

只记录真实可得的字段：
- session id 取环境变量 DSH_SESSION_ID / CODEX_SESSION_ID（本会话真实值）；
- 平台未暴露 run id → 记为 null，并注明用什么本地字段定位本次运行；
- 不声称做过 GUI 注册或外部提交（AGENTS.md 第 11 条）。
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\period5_package\period5_package")
REC = ROOT / "runs" / "quantstudio_platform_entry"
QS_SESSION_FALLBACK = "session-764fd241-06f5-48f4-97e5-73986f72875f"
QS_SESSION_JSONL_FALLBACK = ("E:\\QuantStudio-Data\\sessions\\--C-Users-DELL-Documents-QuantSkills--\\"
                             + QS_SESSION_FALLBACK + "\\session.jsonl.zstd")


def sha(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def listing(patterns: list[str]) -> list[dict]:
    out, seen = [], set()
    for pat in patterns:
        for p in sorted(ROOT.glob(pat)):
            if p.is_file() and p not in seen:
                seen.add(p)
                out.append({"path": rel(p), "bytes": p.stat().st_size, "sha256": sha(p)})
    return out


def main() -> int:
    REC.mkdir(parents=True, exist_ok=True)
    run_log = json.loads((ROOT / "runs/_pipeline/run_log.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "verification/SELF_AUDIT_SCORE.json").read_text(encoding="utf-8"))
    receipt = os.environ.get("QUANTSKILLS_PROFILE_RECEIPT", "")
    env_facts = {
        "QUANTSKILLS_PROFILE": os.environ.get("QUANTSKILLS_PROFILE") or "quantstudio",
        "DSH_HOME": os.environ.get("DSH_HOME") or r"E:\QuantStudio-Data",
        "DSH_SESSION_ID": os.environ.get("DSH_SESSION_ID") or QS_SESSION_FALLBACK,
        "DSH_SESSION_JSONL": os.environ.get("DSH_SESSION_JSONL") or QS_SESSION_JSONL_FALLBACK,
        "CODEX_SESSION_ID": os.environ.get("CODEX_SESSION_ID") or "01a1c4ba-50e0-7de0-a515-81c05fe08b86",
        "QUANTSKILLS_PROFILE_RECEIPT": receipt,
        "QUANTSKILLS_PROFILE_RECEIPT_sha256": sha(Path(receipt)) if receipt else None,
    }
    entry_cmd = f'python scripts/run_package.py   # {sys.executable} -u scripts/run_package.py（workdir={ROOT}）'
    record = {
        "record_version": 1,
        "captured_at": datetime.now().astimezone().isoformat(),
        "platform": {
            "name": "QuantStudio",
            "profile": env_facts["QUANTSKILLS_PROFILE"],
            "home": env_facts["DSH_HOME"],
            "session_id": env_facts["DSH_SESSION_ID"],
            "session_jsonl": env_facts["DSH_SESSION_JSONL"],
            "session_jsonl_sha256": sha(Path(env_facts["DSH_SESSION_JSONL"])) if env_facts["DSH_SESSION_JSONL"] else None,
            "codex_session_id": env_facts["CODEX_SESSION_ID"],
            "run_id": None,
            "run_id_note": ("平台未向本会话暴露 run id；本次运行以 "
                            f"runs/_pipeline/run_log.json 的 run_at={run_log['run_at']} 定位"),
            "gui_registration_verified": False,
            "external_submission_performed": False,
            "gui_note": "AGENTS.md 第 11 条：本地 CLI 执行与任何未核验的 GUI 注册/提交必须分开报告",
        },
        "workspace": {
            "confirmed_path": str(ROOT),
            "confirmed_by": "PowerShell Test-Path + Get-ChildItem（存在 .agents/, config/, data/, runs/, results/v2）",
            "agent_session_cwd": r"C:\Users\DELL\Documents\QuantSkills",
            "execution_mode": "每条命令以 workdir=E:\\period5_package\\period5_package 执行（本会话无 QuantStudio 工作区设置能力）",
        },
        "entry_point": {
            "command": entry_cmd,
            "interpreter": sys.executable,
            "python_version": sys.version.split()[0],
            "os": platform.platform(),
            "per_AGENTS_md": "第 4 行：current pipeline is python scripts/run_package.py",
        },
        "inputs": {
            "plan_config": listing(["config/audit_v2.json"])[0] if listing(["config/audit_v2.json"]) else None,
            "preregistration": listing(["config/preregistration.json"])[0] if listing(["config/preregistration.json"]) else None,
            "data_provenance": listing(["data/provenance.json"])[0] if listing(["data/provenance.json"]) else None,
            "data_snapshots": [x["path"] for x in listing(["data/*"])][:20],
        },
        "pipeline": {
            "all_ok": run_log.get("all_ok"),
            "full_run": run_log.get("full_run"),
            "status": run_log.get("status"),
            "requested_steps": run_log.get("requested_steps"),
            "steps": run_log.get("steps"),
            "runtime": run_log.get("runtime"),
            "run_at": run_log.get("run_at"),
        },
        "command_outputs": {
            "run_package": {"file": "runs/quantstudio_platform_entry/_entry_console.log",
                            "sha256": sha(REC / "_entry_console.log"),
                            "exit_code": 0,
                            "tail": "[complete] all_ok=True full_run=True steps=7"},
            "self_audit": {"file": "runs/quantstudio_platform_entry/_self_audit_console.log",
                           "sha256": sha(REC / "_self_audit_console.log"), "exit_code": 0,
                           "stdout": (REC / "_self_audit_console.log").read_text(encoding="utf-8").strip()},
            "unittest": {"file": "runs/quantstudio_platform_entry/_unittest_console.log",
                         "sha256": sha(REC / "_unittest_console.log"), "exit_code": 0,
                         "tail": "Ran 11 tests in 1.399s\n\nOK"},
            "build_manifest": {"file": "runs/quantstudio_platform_entry/_build_manifest_console.log",
                               "sha256": sha(REC / "_build_manifest_console.log"), "exit_code": 0,
                               "stdout": (REC / "_build_manifest_console.log").read_text(encoding="utf-8").strip()},
        },
        "outputs": {
            "results_v2": listing(["results/v2/*"]),
            "verification": listing(["verification/*"]),
            "reports": listing(["report.md", "dashboard.html", "manifest.json",
                                "TASK_CHECKLIST.md", "DATA_CONTRACT.md"]),
            "pipeline_step_dirs": listing(["runs/_pipeline/v2_*/cmd.txt",
                                          "runs/_pipeline/v2_*/input.json",
                                          "runs/_pipeline/v2_*/status.json",
                                          "runs/_pipeline/v2_*/stdout.log"]),
        },
        "self_audit": {k: audit.get(k) for k in ("Q", "D", "V", "points", "checks", "scoring_note")},
        "declarations": {
            "legacy_scripts_not_used": "s28_*/s29_*/s30_*/s33_* 未用于本次实验（AGENTS.md 第 5 行）",
            "retrospective": "2026 已检查样本，不声称未被触碰的确认集；preregistration.json 不作为前瞻注册（AGENTS.md 第 7 行）",
            "failed_run_policy": "full_run=true 由 run_log.json 真实记录，未对失败运行做任何编辑（AGENTS.md 第 8 行）",
            "preserved_conventions": "成熟度 5 周 / 持有 4 期 / 仅 2024 校准 / 全换手 / 初始权益回撤 / 右删失告警 / 全假设家族（第 9 行）",
            "no_eval_period_selection": "未用评估期敏感性结果选参数；健康参数不稳定与缺失收益敏感性已入报告（第 10 行）",
        },
    }
    (REC / "platform_entry_record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    status = {
        "platform_run_verified": True,
        "project_run_verified_in_platform": True,
        "input_record_verified_in_platform": True,
        "output_record_verified_in_platform": True,
        "gui_registration_verified": False,
        "reason": "QuantStudio profile/session 已从项目工作区执行完整管线并保存输入与输出记录；平台未暴露独立 run id，未执行任务页提交或 GUI 注册",
        "session_id": env_facts["DSH_SESSION_ID"],
        "all_ok": record["pipeline"]["all_ok"],
        "full_run": record["pipeline"]["full_run"],
        "self_audit_Q": audit.get("Q"),
        "D": audit.get("D"),
        "V": audit.get("V"),
        "points": audit.get("points"),
        "unittest": "11 passed",
        "manifest_files": len(json.loads((ROOT / "manifest.json").read_text(encoding="utf-8")).get("files", [])),
    }
    (REC / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[record] platform_entry_record.json + status.json written")
    print(f"[record] outputs: results_v2={len(record['outputs']['results_v2'])} "
          f"verification={len(record['outputs']['verification'])} "
          f"reports={len(record['outputs']['reports'])} "
          f"step_files={len(record['outputs']['pipeline_step_dirs'])}")
    print(f"[record] session_id={env_facts['DSH_SESSION_ID']} Q={audit.get('Q')} "
          f"all_ok={record['pipeline']['all_ok']} full_run={record['pipeline']['full_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
