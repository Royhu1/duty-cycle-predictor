"""Tests for the longitudinal vehicle-dynamics functions (dcpredictor.utils.lvd)."""

from dcpredictor.utils.lvd import (
    calculate_battery_consumption_rate,
    calculate_fuel_consumption_rate,
    calculate_wheel_power,
)


class TestVehicleDynamics:
    """Test cases for the standalone vehicle-dynamics functions."""

    def test_calculate_wheel_power_basic(self):
        """Constant speed on a flat road must overcome rolling + aero drag (> 0)."""
        power = calculate_wheel_power(
            mass_kg=5000.0, gradient_degrees=0.0, velocity_mps=20.0, acceleration_mps2=0.0
        )
        assert power > 0

    def test_calculate_wheel_power_zero_velocity(self):
        """At zero velocity, instantaneous power is zero (P = F * v)."""
        power = calculate_wheel_power(
            mass_kg=5000.0, gradient_degrees=5.0, velocity_mps=0.0, acceleration_mps2=0.0
        )
        assert power == 0.0

    def test_calculate_wheel_power_uphill_vs_flat(self):
        """Uphill requires more power than flat; downhill requires less."""
        flat = calculate_wheel_power(
            mass_kg=5000.0, gradient_degrees=0.0, velocity_mps=20.0, acceleration_mps2=0.0
        )
        uphill = calculate_wheel_power(
            mass_kg=5000.0, gradient_degrees=5.0, velocity_mps=20.0, acceleration_mps2=0.0
        )
        downhill = calculate_wheel_power(
            mass_kg=5000.0, gradient_degrees=-5.0, velocity_mps=20.0, acceleration_mps2=0.0
        )
        assert uphill > flat > downhill

    def test_calculate_fuel_consumption_rate(self):
        """Positive wheel power yields a positive diesel fuel rate in L/hr."""
        result = calculate_fuel_consumption_rate(wheel_power_watts=50000.0)
        assert result["unit"] == "L/hr"
        assert result["rate"] > 0

    def test_calculate_fuel_consumption_rate_negative_power(self):
        """Negative (braking) power falls back to the idle rate (0 by default)."""
        result = calculate_fuel_consumption_rate(wheel_power_watts=-10000.0)
        assert result["rate"] == 0.0

    def test_calculate_battery_consumption_rate(self):
        """Driving draws positive battery power in kW."""
        result = calculate_battery_consumption_rate(wheel_power_watts=50000.0)
        assert result["unit"] == "kW"
        assert result["rate"] > 0

    def test_calculate_battery_consumption_rate_regenerative(self):
        """Regenerative braking returns negative battery power (charging)."""
        result = calculate_battery_consumption_rate(wheel_power_watts=-10000.0)
        assert result["rate"] < 0
