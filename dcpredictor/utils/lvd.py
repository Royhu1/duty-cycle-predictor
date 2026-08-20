"""
Longitudinal Vehicle Dynamics (LVD) Module

This module provides functions for calculating vehicle dynamics, power requirements,
and fuel consumption. It matches the interface expected by the existing notebooks.
"""

import numpy as np
from typing import Union, Dict, Tuple, Optional


def calculate_wheel_power(
    mass_kg: float,
    gradient_degrees: float,
    velocity_mps: float,
    acceleration_mps2: float,
    rolling_resistance_coeff: float = 0.00464,
    drag_coefficient: float = 0.5,
    frontal_area_m2: float = 10.0,
    air_density_kg_m3: float = 1.225,
    g: float = 9.81
) -> float:
    """
    Calculate instantaneous wheel power based on vehicle dynamics.

    This function calculates the total traction force needed to overcome four main resistances:
    - Rolling Resistance
    - Grade Resistance
    - Aerodynamic Drag
    - Acceleration Resistance

    Args:
        mass_kg: Total vehicle mass (kg)
        gradient_degrees: Road gradient (degrees). Positive for uphill, negative for downhill
        velocity_mps: Instantaneous vehicle velocity (m/s)
        acceleration_mps2: Instantaneous vehicle acceleration (m/s²)
        rolling_resistance_coeff: Rolling resistance coefficient, default 0.00464
        drag_coefficient: Aerodynamic drag coefficient, default 0.5
        frontal_area_m2: Vehicle frontal area (m²), default 10.0
        air_density_kg_m3: Air density (kg/m³), default 1.225
        g: Gravitational acceleration (m/s²), default 9.81

    Returns:
        Wheel power in watts (W)
    """
    # Convert gradient from degrees to radians
    gradient_radians = np.radians(gradient_degrees)

    # Calculate individual force components
    # 1. Rolling resistance force
    F_roll = rolling_resistance_coeff * mass_kg * g * np.cos(gradient_radians)

    # 2. Grade resistance force
    F_grade = mass_kg * g * np.sin(gradient_radians)

    # 3. Aerodynamic drag force
    F_aero = 0.5 * air_density_kg_m3 * drag_coefficient * frontal_area_m2 * velocity_mps**2

    # 4. Acceleration force
    F_accel = mass_kg * acceleration_mps2

    # Total traction force (sum of all resistances)
    F_total = F_roll + F_grade + F_aero + F_accel

    # Calculate wheel power (force × velocity)
    power_watts = F_total * velocity_mps

    return power_watts


def calculate_diesel_consumption_rate(
    wheel_power_watts: float,
    heating_value_mj_l: float = 36.0,
    engine_efficiency: float = 0.42,
    transmission_efficiency: float = 0.95,
    idle_fuel_consumption_l_per_hr: float = 0.0
) -> float:
    """
    Calculate instantaneous diesel fuel consumption rate based on wheel power.

    Args:
        wheel_power_watts: Instantaneous wheel power (watts, W)
        heating_value_mj_l: Diesel lower heating value (MJ/L), default 36.0
        engine_efficiency: Engine thermal efficiency, default 0.42 (42%)
        transmission_efficiency: Transmission efficiency (engine to wheels), default 0.95
        idle_fuel_consumption_l_per_hr: Idle fuel consumption rate (L/hr), default 0.0

    Returns:
        Fuel consumption rate in L/hr
    """
    # For negative power (braking/coasting), assume idle consumption
    if wheel_power_watts <= 0:
        return idle_fuel_consumption_l_per_hr

    # 1. Calculate engine power from wheel power
    engine_power_watts = wheel_power_watts / transmission_efficiency

    # 2. Calculate required fuel power from engine power
    fuel_power_watts = engine_power_watts / engine_efficiency

    # 3. Convert heating value from MJ/L to J/L for unit consistency
    heating_value_j_l = heating_value_mj_l * 1e6  # 1 MJ = 1e6 J

    # 4. Calculate fuel consumption rate in Liters per second (L/s)
    fuel_rate_l_s = fuel_power_watts / heating_value_j_l

    # 5. Convert rate from Liters per second to Liters per hour (L/hr)
    fuel_rate_l_hr = fuel_rate_l_s * 3600  # 3600 seconds per hour

    return fuel_rate_l_hr


def calculate_fuel_consumption_rate(
    wheel_power_watts: float,
    transmission_efficiency: float = 0.35,
    engine_efficiency: float = 0.42,
    heating_value_mj_l: float = 36.0,
    idle_fuel_consumption_l_per_hr: float = 0.0
) -> Dict[str, Union[float, str]]:
    """
    Calculate instantaneous fuel consumption rate (compatible with original interface).

    Args:
        wheel_power_watts: Instantaneous wheel power (watts, W)
        transmission_efficiency: Transmission efficiency, default 0.35
        engine_efficiency: Engine thermal efficiency, default 0.42
        heating_value_mj_l: Fuel lower heating value (MJ/L), default 36.0
        idle_fuel_consumption_l_per_hr: Idle fuel consumption rate (L/hr), default 0.0

    Returns:
        Dictionary containing fuel consumption rate (L/hr) and unit
    """
    # For negative power (braking/coasting), assume idle consumption
    if wheel_power_watts <= 0:
        return {"rate": idle_fuel_consumption_l_per_hr, "unit": "L/hr"}

    # 1. Calculate engine power from wheel power
    engine_power_watts = wheel_power_watts / transmission_efficiency

    # 2. Calculate required fuel power from engine power
    fuel_power_watts = engine_power_watts / engine_efficiency

    # 3. Convert heating value from MJ/L to J/L for unit consistency
    heating_value_j_l = heating_value_mj_l * 1e6  # 1 MJ = 1e6 J

    # 4. Calculate fuel consumption rate in Liters per second (L/s)
    fuel_rate_l_s = fuel_power_watts / heating_value_j_l

    # 5. Convert rate from Liters per second to Liters per hour (L/hr)
    fuel_rate_l_hr = fuel_rate_l_s * 3600  # 3600 seconds per hour

    return {"rate": fuel_rate_l_hr, "unit": "L/hr"}


def calculate_battery_consumption_rate(
    wheel_power_watts: float,
    battery_to_wheel_efficiency: float = 0.85
) -> Dict[str, Union[float, str]]:
    """
    Calculate instantaneous battery power consumption rate for electric vehicles.

    Args:
        wheel_power_watts: Instantaneous wheel power (watts, W)
        battery_to_wheel_efficiency: Battery to wheel efficiency, default 0.85

    Returns:
        Dictionary containing battery consumption rate (kW) and unit
    """
    if wheel_power_watts >= 0:
        # Driving: Power is drawn from the battery, losing efficiency on the way to the wheels
        power_at_battery_watts = wheel_power_watts / battery_to_wheel_efficiency
    else:
        # Regenerative braking: Power flows back to battery, with efficiency loss
        power_at_battery_watts = wheel_power_watts * battery_to_wheel_efficiency

    # Convert to kW for convenience
    rate_kw = power_at_battery_watts / 1000

    return {"rate": rate_kw, "unit": "kW"}


# Additional helper functions for gradient cycle prediction
def calculate_gradient_profile(
    elevations: list,
    distances: list
) -> list:
    """
    Calculate gradient profile from elevation and distance data.

    Args:
        elevations: List of elevation values (m)
        distances: List of cumulative distances (m)

    Returns:
        List of gradient values (degrees)
    """
    gradients = [0.0]  # First point has zero gradient

    for i in range(1, len(elevations)):
        if i < len(distances):
            elevation_change = elevations[i] - elevations[i-1]
            distance_change = distances[i] - distances[i-1]

            if distance_change > 0:
                gradient_rad = np.arctan(elevation_change / distance_change)
                gradient_deg = np.degrees(gradient_rad)
                gradients.append(gradient_deg)
            else:
                gradients.append(0.0)
        else:
            gradients.append(0.0)

    return gradients


def predict_gradient_cycle(
    route_df,
    resolution_m: float = 50.0
) -> Dict[str, list]:
    """
    Predict gradient cycle from route data.

    Args:
        route_df: DataFrame with route information including elevation
        resolution_m: Distance resolution for gradient calculation

    Returns:
        Dictionary containing gradient cycle prediction
    """
    # This is a placeholder for gradient cycle prediction
    # In the future, this will use elevation data to predict gradients

    if 'elevation' in route_df.columns:
        elevations = route_df['elevation'].tolist()
    elif 'Elev' in route_df.columns:
        elevations = route_df['Elev'].tolist()
    else:
        # Use zero elevation as fallback
        elevations = [0.0] * len(route_df)

    # Calculate cumulative distances
    distances = [0.0]
    for i in range(1, len(route_df)):
        if i < len(route_df):
            # Use haversine distance if lat/lon available
            if 'Lat' in route_df.columns and 'Lon' in route_df.columns:
                from math import radians, sin, cos, asin, sqrt

                lat1, lon1 = route_df.iloc[i-1]['Lat'], route_df.iloc[i-1]['Lon']
                lat2, lon2 = route_df.iloc[i]['Lat'], route_df.iloc[i]['Lon']

                # Haversine distance calculation
                R = 6371000  # Earth radius in meters
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
                dist = 2 * R * asin(sqrt(a))

                distances.append(distances[-1] + dist)
            else:
                distances.append(distances[-1] + resolution_m)

    # Calculate gradients
    gradients = calculate_gradient_profile(elevations, distances)

    return {
        'distances': distances,
        'elevations': elevations,
        'gradients': gradients
    }
