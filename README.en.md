# skill-factor-drift-closure

An evidence-first skill for testing whether actions after a factor-drift alert create net value. It compares no action, fixed de-risking, alert-triggered downweighting, retraining and signal switching out of sample, while reporting false-alarm cost and recovery latency.

Read `SKILL.md`, `references/data-contract.md` and `references/output-contract.md` before running. The skill freezes predictions and parameters, waits for mature labels, separates calibration from evaluation, charges full turnover and costs, retains censored events, and applies family-wise multiple-comparison controls.

When QuantStudio is required, execution must come from the real QuantStudio entry and persist the session/workspace, input hashes, command logs, outputs and manifest. EVO pages and unbound local CLI runs are not platform evidence.

This repository is GPL-3.0-only, contains no market data or credentials, and is for quantitative research and education only.

## Project implementation

The executable project is included under [`project/`](project/). It contains the `engine_v2.py` closed-loop engine, monitor entry points, refit and inference code, report generation, acceptance checks, regression tests, frozen configs, QuantStudio run evidence, and compact result snapshots. Raw market panels, rolling refit intermediates, and credentials are excluded; provide authorized local data according to `project/DATA_CONTRACT.md`.

```powershell
cd project
python -m unittest discover -s tests -v
python scripts/run_package.py
```
