"""dcpredictor - Duty Cycle Prediction Package.

Example:
    from dcpredictor import (
        DutyCyclePredictor,
        load_default_vehicle_params,
        load_default_driving_behavior,
    )

    # API keys are read from .env automatically.
    predictor = DutyCyclePredictor()
    result = predictor.predict(
        origin=(52.292, 0.389),
        destination=(51.550, -0.242),
        mass_kg=5000.0,
        vehicle_params=load_default_vehicle_params(),
        driving_behavior=load_default_driving_behavior(),
    )
    if result is not None:
        print(result.speed_profile.head())
"""

from dcpredictor.version import __version__, __version_info__, VERSION_DATE
from dcpredictor.utils.models import DutyCycle, VehicleParams, DrivingBehavior
from dcpredictor.duty_cycle_predictor import (
    DutyCyclePredictor,
    load_default_vehicle_params,
    load_default_driving_behavior,
)

__all__ = [
    "__version__",
    "__version_info__",
    "VERSION_DATE",
    "DutyCyclePredictor",
    "DutyCycle",
    "VehicleParams",
    "DrivingBehavior",
    "load_default_vehicle_params",
    "load_default_driving_behavior",
]
