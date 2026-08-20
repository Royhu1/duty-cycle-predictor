#!/usr/bin/env python3
"""Offline example for the dcpredictor package (no API keys required).

Builds a small synthetic route, generates a driving cycle with
``DrivingCycleGenerator``, then computes instantaneous wheel power and diesel
fuel rate with the ``dcpredictor.utils.lvd`` functions.

Run:
    conda activate dcp
    python examples/basic_usage.py
"""

from datetime import datetime

import pandas as pd

from dcpredictor.generators import DrivingCycleGenerator
from dcpredictor.utils.lvd import calculate_fuel_consumption_rate, calculate_wheel_power


def make_sample_route() -> pd.DataFrame:
    """A short synthetic route with speed limits and a mid-route turn."""
    return pd.DataFrame(
        {
            "Lat": [52.2000, 52.2050, 52.2120, 52.2180, 52.2240],
            "Lon": [0.1000, 0.1050, 0.1120, 0.1000, 0.0900],
            "MaxSpeed": [25.0, 25.0, 25.0, 20.0, 15.0],
            "BaseSpeed": [25.0, 25.0, 25.0, 20.0, 15.0],
            "TrafficSpeed": [25.0, 22.0, 25.0, 18.0, 15.0],
            "Action": ["start", "continue", "turn", "continue", "arrive"],
        }
    )


def main() -> None:
    print("dcpredictor - basic offline usage")
    print("=" * 50)

    route_df = make_sample_route()
    print(f"Sample route: {len(route_df)} waypoints")

    generator = DrivingCycleGenerator()
    cycle = generator.generate_use_static_behaviour(
        route_df, datetime(2025, 2, 27, 9, 0, 0)
    )

    print(f"Generated driving cycle: {len(cycle)} time steps (dt = 1 s)")
    print(f"  distance : {cycle['distance'].iloc[-1] / 1000:.2f} km")
    print(f"  avg speed: {cycle['speed'].mean() * 3.6:.1f} km/h")
    print(f"  max speed: {cycle['speed'].max() * 3.6:.1f} km/h")

    # Instantaneous power + fuel at the fastest point (flat road assumed).
    idx = cycle["speed"].idxmax()
    speed = cycle.loc[idx, "speed"]
    acc = cycle.loc[idx, "acc"]
    power_w = calculate_wheel_power(
        mass_kg=5000.0, gradient_degrees=0.0, velocity_mps=speed, acceleration_mps2=acc
    )
    fuel = calculate_fuel_consumption_rate(power_w)
    print(
        f"At max speed ({speed * 3.6:.1f} km/h): "
        f"{power_w / 1000:.1f} kW, {fuel['rate']:.2f} {fuel['unit']}"
    )
    print("Done.")


if __name__ == "__main__":
    main()
