# Project source bundle

This directory contains the executable implementation behind `skill-factor-drift-closure`.

## Included implementation

- `scripts/engine_v2.py`: leakage-safe rolling model, mature-label gating, four phase accounts, turnover/cost accounting, alert arms, right-censored episodes.
- `scripts/run_monitor_entries.py`: project-local drift and health monitor entry points with input/output hashes.
- `scripts/analyze_v2.py`: bootstrap, BH family correction, serial dependence handling, and Reality Check.
- `scripts/health_robustness_v2.py`: pre-registered health-parameter perturbation analysis.
- `scripts/report_v2.py`: report and dashboard generation.
- `scripts/verify_v2.py` and `scripts/self_audit.py`: acceptance checks and requirement scoring.
- `scripts/run_package.py`: reproducible pipeline entry point with `full_run` bookkeeping.
- `tests/`: accounting, leakage, inference, and model regression tests.
- `config/`: frozen analysis plans and model settings.
- `.agents/skills/`: project-local copies of the two upstream monitoring skills, including their licenses.
- `runs/quantstudio_platform_entry/`: QuantStudio entry evidence, input/output hashes, console logs, and manifest receipts.
- `results/v2/`: compact result snapshots; raw panels and rolling refit matrices are intentionally excluded.

## Run locally

```powershell
python -m unittest discover -s tests -v
python scripts/run_package.py
```

The pipeline expects the project data contract described in `DATA_CONTRACT.md`. Raw market panels are excluded from this community Skill; supply an authorized local snapshot under `data/` and preserve its provenance hash.

## QuantStudio evidence

The recorded run under `runs/quantstudio_platform_entry/` is the project evidence bundle. A local CLI invocation or an EVO page is not a substitute for the QuantStudio entry record. For a new run, preserve the session/workspace identity, exact command, input hashes, stdout/stderr, output manifest, and `full_run` status.
