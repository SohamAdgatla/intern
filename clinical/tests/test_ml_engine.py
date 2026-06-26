"""Unit tests for trend feature engineering (no database required)."""
from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from clinical.services.ml_engine import (
    ObservationPoint,
    analyze_observation_series,
    classify_trend,
    compute_moving_average,
    compute_regression_slope,
)


class TrendEngineTests(SimpleTestCase):
    def _series(self, start_value: float, step: float, n: int) -> list:
        base = datetime(2023, 1, 1, tzinfo=timezone.utc)
        return [
            ObservationPoint(
                effective_datetime=base + timedelta(days=30 * i),
                value=start_value + step * i,
            )
            for i in range(n)
        ]

    def test_moving_average_trailing_window(self):
        points = self._series(100.0, 1.0, 6)
        ma = compute_moving_average(points, window_days=400)
        self.assertIsNotNone(ma)
        self.assertGreater(ma, 100.0)

    def test_regression_slope_positive_trend(self):
        points = self._series(5.0, 0.1, 12)
        slope = compute_regression_slope(points, window_days=400)
        self.assertIsNotNone(slope)
        self.assertGreater(slope, 0)

    def test_analyze_series_labels_rising(self):
        points = self._series(120.0, 2.0, 10)
        result = analyze_observation_series(points)
        self.assertEqual(result.trend_label, "rising")
        self.assertIsNotNone(result.slope_per_year)

    def test_classify_trend_stabilizing(self):
        self.assertEqual(classify_trend(0.005), "stabilizing")
