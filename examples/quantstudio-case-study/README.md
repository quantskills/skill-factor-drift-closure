# QuantStudio case study

This repository's originating project tested whether factor-drift alerts should trigger downweighting or retraining. It was executed through a QuantStudio `quantstudio` profile/session with persisted input/output records. The project retained five-observation label maturity, four-observation holding period, 2024-only calibration, full turnover and right-censored events.

The study produced a directional negative result: dynamic responses did not survive the complete multiple-comparison and Reality Check controls, and fixed exposure reduction explained part of the observed improvement. The correct research decision was to keep monitoring as a diagnostic input and avoid automatic trading action until an independent evaluation period is available.

The original large data and local session archive are intentionally excluded. This example is a short, source-grounded summary for reviewers; the full evidence package is delivered separately.
