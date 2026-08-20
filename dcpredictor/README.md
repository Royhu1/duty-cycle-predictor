# `dcpredictor` — package architecture

> This is the **single source of truth for the `dcpredictor` package**: its public API, module map, data flow,
> and key algorithms. The repository-wide map is the root [`README.md`](../README.md). Versioning / commit /
> changelog conventions are in [`../.claude/rules/git-workflow.md`](../.claude/rules/git-workflow.md).

`dcpredictor` is the SemVer-versioned core of the project (import name `dcpredictor`; the repository is **not**
packaged or distributed). It turns a route into a duty cycle: a speed profile, a gradient profile, and an
energy/fuel profile.

## Run

```bash
conda activate dcp
pip install -r requirements.txt
```

No installation step: import the package directly from the repository root (`import dcpredictor`); the demo
notebooks add the root to `sys.path` in their first cell. The version is single-sourced from `version.py`
(`__version__`).

## Public API

Top-level (`from dcpredictor import ...`):

| Symbol | Kind | Description |
|--------|------|-------------|
| `DutyCyclePredictor` | class | End-to-end orchestrator. `.predict(origin, destination, mass_kg, vehicle_params, driving_behavior, departure_time=None, via_points=None) -> Optional[DutyCycle]`; properties `.version`, `.version_info`. |
| `load_default_vehicle_params(preset="default")` | func | Load a `VehicleParams` preset from `params/vehicle_params.json` (`"default"`, `"AY71UCD"`, `"FX73VAE"`). |
| `load_default_driving_behavior(preset="default")` | func | Load a `DrivingBehavior` preset from `params/driving_behavior.json`. |
| `DutyCycle` | dataclass | Result container: `speed_profile`, `gradient_profile`, `energy_profile` (+ reserved `weather_profile`, `auxiliary_profile`). |
| `VehicleParams` | dataclass | Vehicle physics/powertrain parameters (mass is passed separately to `predict`). `is_diesel()` / `is_electric()`, `to_dict()` / `from_dict()`. |
| `DrivingBehavior` | dataclass | Driver model parameters (speed caps, accel/decel, time step, smoothing). |

Sub-package exports:

- `from dcpredictor.generators import DrivingCycleGenerator, ElevationGradientGenerator, EnergyProfileGenerator`
- `from dcpredictor.utils import HereAPIClient, SRFAPIClient, SRFLoggerDataDownloader` and the standalone
  dynamics functions `calculate_wheel_power`, `calculate_diesel_consumption_rate`, `calculate_fuel_consumption_rate`,
  `calculate_battery_consumption_rate`, `calculate_gradient_profile`, `predict_gradient_cycle`.

## Package structure

```
dcpredictor/
├── __init__.py                        # public exports (see table above)
├── version.py                         # version metadata (importlib.metadata + fallback)
├── CHANGELOG.md                       # package SemVer changelog
├── duty_cycle_predictor.py            # DutyCyclePredictor orchestrator + load_default_* helpers
├── generators/
│   ├── driving_cycle_generator.py     # DrivingCycleGenerator — kinematic speed profile (primary)
│   ├── driving_cycle_fsm.py           # FSM-based alternative speed generator (not exported by default)
│   ├── elevation_gradient_generator.py# ElevationGradientGenerator — elevation + gradient
│   └── energy_profile_generator.py    # EnergyProfileGenerator — power & fuel/energy via LVD
├── utils/
│   ├── here_api.py                    # HereAPIClient — HERE routing → route DataFrame
│   ├── srf_api.py                     # SRFAPIClient — SRF elevation lookup
│   ├── srf_logger_downloader.py       # SRFLoggerDataDownloader — bulk logger-data download
│   ├── lvd.py                         # standalone longitudinal-vehicle-dynamics functions
│   └── models.py                      # DutyCycle / VehicleParams / DrivingBehavior dataclasses
└── params/
    ├── vehicle_params.json            # vehicle presets: default, AY71UCD, FX73VAE
    └── driving_behavior.json          # driving-behaviour presets: default
```

## Data flow (inside `DutyCyclePredictor.predict`)

```
origin, destination, (via_points), departure_time
        │
        ▼  HereAPIClient.get_route_dataframe
route_df  (Lat, Lon, MaxSpeed, BaseSpeed, TrafficSpeed, Action)
        │   └─ guard: _is_route_df_valid (>= 5 km, else return None)
        ▼  DrivingCycleGenerator.generate_use_static_behaviour
speed_profile  (per-second timestamp, Lat/Lon, distance, speed, acc, ...)
        │
        ▼  ElevationGradientGenerator.generate_use_srf_api (SRFAPIClient)
gradient_profile  (elevation, gradient°, cumulative gain/loss)
        │
        ▼  EnergyProfileGenerator.generate_use_longitudinal_vehicle_dynamics
energy_profile  (wheel_power_kW, engine_power_kW, fuel_rate_L_hr | energy_rate_kW, cumulative)
        ▼
DutyCycle(speed_profile, gradient_profile, energy_profile)
```

If no SRF key is configured, the gradient stage falls back to a flat (zero-elevation) profile.

## Key algorithms

### Speed profile — `DrivingCycleGenerator.generate_use_static_behaviour`

Simulates motion at a fixed time step (`dt`):
1. Pre-compute segment lengths (haversine) along the route.
2. Each step: advance the vehicle, crossing route segments as needed, interpolating position.
3. Look ahead to the next constraining action (turn, roundabout, arrival) and compute the safe desired speed
   `v_desired = min(v_cruise, sqrt(v_target² + 2·a_dec·dist))`.
4. Apply acceleration/deceleration limits (`_update_speed`); decelerate to a stop at arrival.
5. Optionally smooth with a Savitzky–Golay filter and clip to `v_cap`.

### Wheel power — `lvd.calculate_wheel_power` / `EnergyProfileGenerator`

```
P = (F_roll + F_grade + F_aero + F_accel) · v
F_roll  = Cr · m · g · cos(θ)      # rolling resistance
F_grade = m · g · sin(θ)           # grade
F_aero  = 0.5 · ρ · Cd · A · v²    # aerodynamic drag
F_accel = m · a                    # acceleration
```

### Gradient — `ElevationGradientGenerator`

`gradient° = arctan(Δelevation / segment_distance)`, rolling-mean smoothed (window 5) and clipped to ±8°.

### Fuel / energy rate — `EnergyProfileGenerator`

Diesel: `wheel_power → engine_power (÷ transmission_efficiency) → fuel_power (÷ engine_efficiency) → L/hr (÷ heating value)`;
negative wheel power uses the idle rate. Electric: battery power `= wheel_power / (transmission · battery efficiency)`,
with optional regenerative recovery on negative power.

## Versioning

SemVer applies to this package only. On release: bump `version.py` `__version__` and its
`VERSION_DATE` / `VERSION_DESCRIPTION`, add a `CHANGELOG.md` entry, commit, and tag `vX.Y.Z`. See
[`../.claude/rules/git-workflow.md`](../.claude/rules/git-workflow.md).
