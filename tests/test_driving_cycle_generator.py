"""Tests for the DrivingCycleGenerator class."""

from datetime import datetime

import pandas as pd

from dcpredictor.generators import DrivingCycleGenerator


class TestDrivingCycleGenerator:
    """Test cases for DrivingCycleGenerator."""

    def test_haversine_distance(self):
        """Haversine great-circle distance: London to Cambridge is ~79.5 km."""
        lat1, lon1 = 51.5074, -0.1278  # London
        lat2, lon2 = 52.2053, 0.1218   # Cambridge

        distance = DrivingCycleGenerator.haversine_distance(lat1, lon1, lat2, lon2)

        # ~79.5 km straight-line, returned in metres.
        assert 79000 <= distance <= 80000

    def test_interpolate_speed(self):
        """Linear speed interpolation."""
        assert DrivingCycleGenerator.interpolate_speed(10.0, 20.0, 0.5) == 15.0
        assert DrivingCycleGenerator.interpolate_speed(0.0, 10.0, 0.0) == 0.0
        assert DrivingCycleGenerator.interpolate_speed(0.0, 10.0, 1.0) == 10.0

    def test_update_speed_acceleration(self):
        """Speed update while accelerating is capped by a_acc * dt."""
        v_new = DrivingCycleGenerator._update_speed(
            v_cur=10.0, v_desired=15.0, a_acc=2.0, a_dec=2.0, dt=1.0
        )
        assert v_new == 12.0  # 10 + 2 * 1

    def test_update_speed_deceleration(self):
        """Speed update while decelerating is bounded by a_dec * dt."""
        v_new = DrivingCycleGenerator._update_speed(
            v_cur=15.0, v_desired=10.0, a_acc=2.0, a_dec=2.0, dt=1.0
        )
        assert v_new == 13.0  # 15 - 2 * 1

    def test_generate_use_static_behaviour(self):
        """End-to-end speed-profile generation on a short synthetic route."""
        # ~1 km straight route (each 0.003 deg lat step ~ 333 m).
        route_df = pd.DataFrame(
            {
                "Lat": [52.2000, 52.2030, 52.2060, 52.2090],
                "Lon": [0.1000, 0.1000, 0.1000, 0.1000],
                "MaxSpeed": [25.0, 25.0, 25.0, 25.0],
                "BaseSpeed": [25.0, 25.0, 25.0, 25.0],
                "TrafficSpeed": [25.0, 25.0, 25.0, 25.0],
                "Action": ["start", "continue", "continue", "arrive"],
            }
        )

        generator = DrivingCycleGenerator()
        result = generator.generate_use_static_behaviour(
            route_df, datetime(2025, 2, 27, 9, 0, 0)
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        for col in ("timestamp", "speed", "distance", "acc"):
            assert col in result.columns
        # Speed never exceeds the cap (smoothed output is clipped to v_cap).
        assert result["speed"].max() <= 25.0 + 1e-6
        # Distance is monotonically non-decreasing.
        assert result["distance"].is_monotonic_increasing
