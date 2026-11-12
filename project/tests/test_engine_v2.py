"""Regression checks for material financial/accounting and inference errors."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from engine_v2 import CFG, Models, episodes, mature_frame, max_drawdown, simulate, turnover
from analyze_v2 import bh, inference


class AccountingTests(unittest.TestCase):
    def test_selling_disappearing_position_is_charged(self):
        self.assertAlmostEqual(turnover({"new": 1.0}, {"old": 1.0}), 2.0)
        self.assertAlmostEqual(turnover({}, {"old": 1.0}), 1.0)

    def test_initial_loss_is_drawdown(self):
        self.assertAlmostEqual(max_drawdown([-.1, .01]), -.1)

    def test_recovery_excludes_exit_and_marks_censoring(self):
        actual = episodes(pd.Series([True, True, False, True], index=["a", "b", "c", "d"]))
        self.assertEqual(actual[0]["duration_observations"], 2)
        self.assertEqual(actual[0]["end_exclusive"], "c")
        self.assertFalse(actual[0]["right_censored"])
        self.assertTrue(actual[1]["right_censored"])
        self.assertEqual(actual[1]["duration_observations"], 1)

    def test_pnl_drift_generates_rebalance_cost_and_fees_reconcile(self):
        cache = {}
        symbols = np.array([f"s{i:03}" for i in range(50)])
        for i in range(8):
            returns = np.zeros(50)
            returns[0] = 1.0
            cache[str(i)] = {"sym": symbols, "X": np.ones((50, 2)), "score": np.arange(50.),
                "ew": np.arange(50.), "ret": returns, "elig": np.ones(50, dtype=bool)}
        frame = simulate(cache, list(cache), "long")
        phase0 = frame[frame.phase.eq(0)]
        self.assertGreater(phase0.iloc[1].turnover, .03)
        np.testing.assert_allclose(frame.net, frame.gross - frame.cost)
        self.assertAlmostEqual(phase0.iloc[0].cost, .0008)


class LeakageTests(unittest.TestCase):
    def test_calibration_and_maturity_are_independent_of_future(self):
        dates = pd.date_range("2022-01-07", periods=240, freq="W-FRI").strftime("%Y%m%d").tolist()
        values = pd.Series(np.sin(np.arange(len(dates))) / 10, index=dates)
        frame, calibration, threshold = mature_frame(values, dates)
        changed = values.copy()
        changed.loc[changed.index >= "20250101"] = -100.
        altered, _, altered_threshold = mature_frame(changed, dates)
        self.assertEqual(threshold, altered_threshold)
        self.assertLess(max(calibration.index), "20250101")
        j = dates.index(next(d for d in dates if d >= "20250101"))
        pd.testing.assert_series_equal(frame.monitor.iloc[:j+5], altered.monitor.iloc[:j+5])
        self.assertNotEqual(frame.monitor.iloc[j+5], altered.monitor.iloc[j+5])
        pd.testing.assert_series_equal(frame.ic_alarm, frame.monitor.lt(threshold), check_names=False)

    def test_training_excludes_purge_and_future_labels(self):
        rng = np.random.default_rng(11)
        cache = {}
        for i in range(170):
            x = rng.normal(size=(8, 3))
            cache[str(i)] = {"X": x, "ret": x @ np.array([.2, -.1, .3]) + .01 * rng.normal(size=8)}
        expected = Models(cache).fit("169")
        changed = {d: {"X": c["X"].copy(), "ret": c["ret"].copy()} for d, c in cache.items()}
        for i in range(164, 170):
            changed[str(i)]["ret"][:] = 1e9
        actual = Models(changed).fit("169")
        for a, b in zip(expected, actual):
            np.testing.assert_allclose(a, b, atol=1e-12)
        from sklearn.linear_model import Ridge
        training = [cache[str(i)] for i in range(8, 164)]
        model = Ridge(alpha=1.).fit(np.vstack([d["X"] for d in training]), np.concatenate([d["ret"] for d in training]))
        np.testing.assert_allclose(actual[0], model.coef_, atol=1e-12)


class InferenceTests(unittest.TestCase):
    def test_bh_uses_entire_family(self):
        np.testing.assert_allclose(bh([.01, .04, .03]), [.03, .04, .04])

    def test_reality_check_compares_to_observed_effect(self):
        old_draws = CFG["bootstrap_draws"]
        CFG["bootstrap_draws"] = 499
        try:
            _, zero = inference(np.zeros((20, 3)))
            _, shifted = inference(np.ones((20, 3)) * .02)
            self.assertEqual(zero[1]["rc_positive"], 1.)
            self.assertLess(shifted[1]["rc_positive"], .01)
        finally:
            CFG["bootstrap_draws"] = old_draws


if __name__ == "__main__":
    unittest.main()
