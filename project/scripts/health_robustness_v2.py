"""Execute upstream robustness CLI, then inspect whole-path alarm stability."""
import importlib.util
import sys

import pandas as pd

from engine_v2 import CFG, OUT, ROOT, recorded_cli, save, sha


def main():
    source = ROOT / "runs/r01_monitor_entry/health_panel.csv"
    skill = ROOT / ".agents/skills/skill-factor-health-monitor/scripts"
    output = ROOT / "runs/v2/health_robustness"
    recorded_cli([sys.executable, str(skill / "robustness_check.py"), "--panel", str(source),
        "--output", str(output)], output / "entry",
        {"input": str(source.relative_to(ROOT)), "input_sha256": sha(source),
         "use": "sensitivity only; no choice of best historical parameter"})
    spec = importlib.util.spec_from_file_location("robustness_health", skill / "factor_health.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    detail = pd.read_csv(ROOT / "runs/r01_monitor_entry/health/health_timeseries.csv", parse_dates=["date"])
    ic = detail[["date", "factor", "ic", "n_symbols"]]
    baseline_alarm = (detail.decline_probability >= .8) | detail.cusum_alarm
    evaluation = detail.date >= pd.Timestamp(CFG["eval_start"])
    rows = []
    for threshold in (.01, .02, .03):
        for q in (5e-7, 1e-6, 5e-6):
            for cusum in (4., 5., 7.):
                series, _ = module.analyze(ic, module.Config(decline_threshold=threshold, process_var=q, cusum_threshold=cusum))
                alarm = (series.decline_probability >= .8) | series.cusum_alarm
                rows.append({"decline_threshold": threshold, "process_var": q, "cusum_threshold": cusum,
                    "evaluation_alarm_share": float(alarm[evaluation].mean()),
                    "disagreement_with_default": float((alarm[evaluation] != baseline_alarm[evaluation]).mean())})
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "health_path_sensitivity.csv", index=False)
    spread = float(frame.evaluation_alarm_share.max() - frame.evaluation_alarm_share.min())
    save(OUT / "health_robustness.json", {"parameter_sets": len(frame),
        "evaluation_alarm_share_min": frame.evaluation_alarm_share.min(),
        "evaluation_alarm_share_max": frame.evaluation_alarm_share.max(),
        "max_disagreement_with_default": frame.disagreement_with_default.max(),
        "stable_across_path_parameters": spread <= .25,
        "note": "Default policy remains fixed; latest-only upstream red-rate stability does not prove path stability; no labeled decay events available"})
    print(f"[health robustness] 27 combinations, path alarm share spread={spread:.3f}; default policy unchanged")


if __name__ == "__main__":
    main()
