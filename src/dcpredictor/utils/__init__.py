"""
Utils package for API clients, data models, and vehicle dynamics.
"""

from dcpredictor.utils.models import DutyCycle, VehicleParams, DrivingBehavior
from dcpredictor.utils.here_api import HereAPIClient
from dcpredictor.utils.srf_api import SRFAPIClient
from dcpredictor.utils.lvd import (
    calculate_wheel_power,
    calculate_diesel_consumption_rate,
    calculate_fuel_consumption_rate,
    calculate_battery_consumption_rate,
    calculate_gradient_profile,
    predict_gradient_cycle,
)
from dcpredictor.utils.srf_logger_downloader import SRFLoggerDataDownloader

__all__ = [
    # Data models
    "DutyCycle",
    "VehicleParams",
    "DrivingBehavior",
    # API clients
    "HereAPIClient",
    "SRFAPIClient",
    # Data downloader
    "SRFLoggerDataDownloader",
    # Vehicle dynamics
    "calculate_wheel_power",
    "calculate_diesel_consumption_rate",
    "calculate_fuel_consumption_rate",
    "calculate_battery_consumption_rate",
    "calculate_gradient_profile",
    "predict_gradient_cycle",
]
