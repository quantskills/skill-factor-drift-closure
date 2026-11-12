"""Regression tests for the independent 2026 model comparison boundaries."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lightgbm_2026 import evaluation_dates, training_arrays, training_dates


class LightGBMBoundaries(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2019-01-04", "2026-11-06", freq="W-FRI").strftime("%Y%m%d").tolist()

    def test_frozen_training_uses_no_2026_or_immature_labels(self):
        first = next(d for d in self.dates if d >= "20260101")
        train = training_dates(self.dates, first)
        self.assertEqual(len(train), 156)
        self.assertLess(train[-1], "20260101")
        self.assertEqual(self.dates.index(first)-self.dates.index(train[-1]), 6)
        cache = {d: {"X": np.ones((2, 3)), "ret": np.array([.1, .2])} for d in self.dates}
        x, y = training_arrays(cache, train)
        for d in self.dates[self.dates.index(train[-1])+1:]:
            cache[d]["ret"][:] = 1e9
        xx, yy = training_arrays(cache, train)
        np.testing.assert_array_equal(x, xx)
        np.testing.assert_array_equal(y, yy)

    def test_rolling_window_has_five_excluded_observations(self):
        for date in self.dates[-40::4]:
            train = training_dates(self.dates, date)
            self.assertEqual(len(train), 156)
            self.assertEqual(self.dates.index(date)-self.dates.index(train[-1]), 6)
            self.assertFalse(set(train) & set(self.dates[self.dates.index(date)-5:]))

    def test_tail_exclusion_is_calendar_only_and_balanced(self):
        year, mature, balanced = evaluation_dates(self.dates)
        self.assertEqual(len(balanced) % 4, 0)
        self.assertEqual(mature[-1], self.dates[-6])
        self.assertEqual(year[-1], self.dates[-1])
        self.assertTrue(set(balanced) <= set(mature))
        self.assertLess(len(mature)-len(balanced), 4)


if __name__ == "__main__":
    unittest.main()
