"""Tests for the data models (VehicleParams, DrivingBehavior)."""

from dcpredictor import DrivingBehavior, VehicleParams


class TestVehicleParams:
    def test_round_trip(self):
        """to_dict / from_dict preserves a diesel VehicleParams."""
        vp = VehicleParams(
            energy_type="diesel",
            frontal_area_m2=10.0,
            drag_coefficient=0.5,
            rolling_resistance_coeff=0.00464,
            transmission_efficiency=0.95,
            max_torque_nm=2500,
            engine_efficiency=0.42,
            heating_value_mj_l=38.7,
            idle_fuel_consumption_l_per_hr=0.0,
        )
        assert vp.is_diesel()
        assert not vp.is_electric()
        assert VehicleParams.from_dict(vp.to_dict()) == vp

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict tolerates extra keys (e.g. the 'company' field in presets)."""
        data = {
            "energy_type": "diesel",
            "frontal_area_m2": 10.0,
            "drag_coefficient": 0.5,
            "rolling_resistance_coeff": 0.00464,
            "transmission_efficiency": 0.95,
            "max_torque_nm": 2500,
            "company": "Turners",  # not a dataclass field
        }
        vp = VehicleParams.from_dict(data)
        assert vp.frontal_area_m2 == 10.0

    def test_electric_flag(self):
        vp = VehicleParams(
            energy_type="electric",
            frontal_area_m2=10.0,
            drag_coefficient=0.5,
            rolling_resistance_coeff=0.00464,
            transmission_efficiency=0.95,
            max_torque_nm=2500,
            battery_efficiency=0.9,
        )
        assert vp.is_electric()
        assert not vp.is_diesel()


class TestDrivingBehavior:
    def test_round_trip(self):
        db = DrivingBehavior(
            v_cap=25.0,
            v_cruise=25.0,
            v_roundabout_enter=3.0,
            v_turn=4.0,
            v_other_action=5.0,
            a_acc=0.58,
            a_dec=0.83,
            dt=1.0,
            smooth_speed=True,
        )
        assert DrivingBehavior.from_dict(db.to_dict()) == db
