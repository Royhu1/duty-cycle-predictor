#!/usr/bin/env python3
"""End-to-end example using DutyCyclePredictor.predict().

Requires ``HERE_API_KEY`` in ``.env`` (``SRF_API_KEY`` optional — without it the
gradient profile falls back to flat). Run from the project root after
``pip install -e .``:

    conda activate dcp
    python examples/predict_end_to_end.py
"""

from datetime import datetime

from dcpredictor import (
    DutyCyclePredictor,
    load_default_driving_behavior,
    load_default_vehicle_params,
)


def main() -> None:
    print("dcpredictor - end-to-end prediction")
    print("=" * 50)

    predictor = DutyCyclePredictor()  # reads API keys from .env

    result = predictor.predict(
        origin=(52.292, 0.389),                          # (lat, lon)
        destination=(51.550, -0.242),
        mass_kg=5000.0,
        vehicle_params=load_default_vehicle_params(),    # or "AY71UCD" / "FX73VAE"
        driving_behavior=load_default_driving_behavior(),
        departure_time=datetime(2025, 2, 27, 9, 0, 0),
    )

    if result is None:
        print("Route too short or invalid — no duty cycle generated.")
        return

    print(f"Speed profile   : {len(result.speed_profile)} steps")
    print(f"Gradient profile: {len(result.gradient_profile)} points")
    print(f"Energy profile  : {len(result.energy_profile)} points")

    if "fuel_cumulative_L" in result.energy_profile.columns:
        total_fuel = result.energy_profile["fuel_cumulative_L"].iloc[-1]
        dist_km = result.speed_profile["distance"].iloc[-1] / 1000
        print(f"Distance: {dist_km:.1f} km | Total fuel: {total_fuel:.2f} L")


if __name__ == "__main__":
    main()
