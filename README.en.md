# skill-factor-drift-closure

An evidence-first skill for testing whether actions after a factor-drift alert create net value. It compares no action, fixed de-risking, alert-triggered downweighting, retraining and signal switching out of sample, while reporting false-alarm cost and recovery latency.

Read `SKILL.md`, `references/data-contract.md` and `references/output-contract.md` before running. The skill freezes predictions and parameters, waits for mature labels, separates calibration from evaluation, charges full turnover and costs, retains censored events, and applies family-wise multiple-comparison controls.

When QuantStudio is required, execution must come from the real QuantStudio entry and persist the session/workspace, input hashes, command logs, outputs and manifest. EVO pages and unbound local CLI runs are not platform evidence.

This repository is GPL-3.0-only, contains no market data or credentials, and is for quantitative research and education only.
