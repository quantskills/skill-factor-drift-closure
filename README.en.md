# skill-factor-drift-closure

English | [简体中文](README.md)

This QuantSkills skill evaluates whether a factor-drift alert creates net value after the response action. It compares no action, fixed de-risking, alert-triggered downweighting, retraining and signal switching out of sample, with false-alarm cost and recovery latency.

The executable implementation, tests, frozen configs, compact result snapshots and QuantStudio evidence are under [`project/`](project/). Raw market panels, rolling refit intermediates and credentials are excluded.

See [`README.md`](README.md) for the detailed Chinese documentation, project design, results, limitations and reproduction steps.
