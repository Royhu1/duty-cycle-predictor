# duty-cycle-predictor

> **This file is the project map** — overall design, repository layout, and how to install, use, and develop the
> project. For the *internals of the toolkit itself* (public API, module map, algorithms), see the package README at
> [`dcpredictor/README.md`](dcpredictor/README.md). At every level, that directory's own `README.md` is the
> single source of truth for that directory.

A Python toolkit for predicting vehicle **duty cycles** from a route: a time-series **speed profile**, an
**elevation/gradient profile**, and an **energy/fuel profile**, computed from external routing (HERE) and
elevation (SRF) data plus a longitudinal vehicle-dynamics model.

## Project architecture: a hierarchical design

The repository is deliberately small: one versioned core package (`dcpredictor/`) at the root — imported
directly, **not packaged or distributed** — plus
demo notebooks (`demo/`) showing how to use it, and unit tests (`tests/`, with sample GPS data under
`tests/data/`, kept out of git). Each directory documents itself through its own `README.md`, so humans and AI
agents can navigate by progressive disclosure. Only source code and documentation are committed (see `.gitignore`).

This repository is deliberately scoped to the **development and testing of the predictor itself** — clone it to use,
experiment with, or evaluate the toolkit. Paper writing and project-level analyses (e.g. conference papers,
fleet case studies) live in their own separate repositories that use `dcpredictor` (clone this repository and
add its root to `PYTHONPATH`, or vendor the `dcpredictor/` folder).

## Repository layout

Only the top level is shown; folders with their own `README.md` document their internal structure there.

```
./
├── dcpredictor          # core package — the versioned core, imported directly (not packaged)
├── demo                 # demo notebooks: offline basics, end-to-end prediction, validation
├── tests                # unit tests (pytest)
│   └── data             # sample GPS trip legs, tests/data/<REG>/*.csv (gitignored)
├── tmp                  # one-off scratch: logs, debug figures, _tmp_*.py (gitignored)
├── requirements.txt     # pip dependency list (runtime + demos/tests + style tools)
├── pyproject.toml       # tool configuration only (black / isort / pytest / mypy)
├── README.md            # project map (this file)
├── CLAUDE.md            # Claude / AI collaboration conventions (imports .claude/rules/*)
└── .claude              # Claude Code config: committed rules, gitignored skills/runtime
```

## Environment setup

This project uses a dedicated conda environment named **`dcp`** (Python ≥ 3.10).

```bash
# 1. Create and activate the environment
conda create -n dcp python=3.10 -y
conda activate dcp

# 2. Install dependencies
pip install -r requirements.txt
```

> There is **no installation step**: the package lives at the repository root, so `import dcpredictor` works
> directly when running from the root (the demo notebooks add the root to `sys.path` in their first cell).

### API keys

Copy `.env.example` to `.env` and fill in your keys (the `.env` file is gitignored):

```bash
HERE_API_KEY=your_here_api_key_here   # HERE Maps — route planning (required). https://developer.here.com/
SRF_API_KEY=your_srf_api_key_here     # SRF platform — elevation + logger data (optional; falls back to flat)
```

## Quick start

### End-to-end prediction (needs API keys)

```python
from datetime import datetime

from dcpredictor import (
    DutyCyclePredictor,
    load_default_vehicle_params,
    load_default_driving_behavior,
)

# Keys are read from .env automatically (or pass here_api_key=/srf_api_key=).
predictor = DutyCyclePredictor()

result = predictor.predict(
    origin=(52.292, 0.389),                              # (lat, lon)
    destination=(51.550, -0.242),
    mass_kg=5000.0,
    vehicle_params=load_default_vehicle_params(),        # or load_default_vehicle_params("AY71UCD")
    driving_behavior=load_default_driving_behavior(),
    departure_time=datetime(2025, 2, 27, 9, 0, 0),
)

if result is None:
    print("Route too short or invalid — no cycle generated.")
else:
    print(result.speed_profile.head())     # timestamp, Lat, Lon, distance, speed (m/s), acc, ...
    print(result.gradient_profile.head())  # elevation (m), gradient (deg), cumulative gain/loss
    print(result.energy_profile.head())    # wheel_power_kW, fuel_rate_L_hr, fuel_cumulative_L
```

`predict()` returns `None` when the route is shorter than ~5 km (a guard against degenerate routes).

### Demo notebooks

Worked examples live in [`demo/`](demo/):

| Notebook | Needs | Shows |
|----------|-------|-------|
| `basic_usage_offline.ipynb` | nothing | offline building blocks: speed profile + wheel power + fuel rate |
| `predict_end_to_end.ipynb` | HERE key (SRF optional) | the full `predict()` pipeline with plots and a folium route map |
| `predict_vs_measured_leg.ipynb` | HERE key + sample data | prediction validated against a measured GPS trip leg, incl. a measured-vs-predicted trajectory map |

## What it predicts

**Input:** an origin/destination (and optional via points), a vehicle mass, vehicle parameters, and a driving-behaviour
profile. **Output:** a [`DutyCycle`](dcpredictor/README.md) with three aligned DataFrames —

1. **Speed profile** — per-second speed/acceleration over the route, from a kinematic driver model.
2. **Gradient profile** — elevation and road gradient (degrees) along the route, from SRF elevation data.
3. **Energy profile** — wheel/engine power and fuel (diesel) or energy (electric) rate plus cumulative consumption.

## Input data format

Sample measured GPS trip legs (used by the validation demo and any data-driven tests) live under
`tests/data/<REG>/` (e.g. `tests/data/AY71UCD/20250227_AY71UCD_Leg1.csv`; gitignored — supplied separately):

| Column | Description |
|--------|-------------|
| `Latitude`, `Longitude` | GPS coordinates |
| `UnixTime` or timestamp | Time of measurement |
| `Spd_Kmph_x` | Vehicle speed (km/h) |
| `MassKg` (optional) | Vehicle mass (kg) |
| `FuelRate` (optional) | Measured fuel rate |

## Key parameters

Defaults live in `dcpredictor/params/*.json` and are loaded via `load_default_vehicle_params(<key>)` /
`load_default_driving_behavior(<key>)`. Override by constructing `VehicleParams` / `DrivingBehavior` directly.

**Vehicle (`vehicle_params.json` → `default`):**

| Field | Default | Meaning |
|-------|---------|---------|
| `energy_type` | `"diesel"` | `"diesel"` or `"electric"` |
| `frontal_area_m2` | 10.0 | frontal area (m²) |
| `drag_coefficient` | 0.5 | aerodynamic drag coefficient (Cd) |
| `rolling_resistance_coeff` | 0.00464 | rolling resistance coefficient (Cr) |
| `transmission_efficiency` | 0.95 | driveline efficiency |
| `engine_efficiency` | 0.42 | engine thermal efficiency (diesel) |
| `heating_value_mj_l` | 38.7 | diesel lower heating value (MJ/L) |

**Driving behaviour (`driving_behavior.json` → `default`):**

| Field | Default | Meaning |
|-------|---------|---------|
| `v_cap` / `v_cruise` | 25.0 | max / cruise speed (m/s) ≈ 90 km/h |
| `a_acc` / `a_dec` | 0.58 / 0.83 | acceleration / deceleration (m/s²) |
| `v_turn` / `v_roundabout_enter` | 4.0 / 3.0 | speed at turns / roundabouts (m/s) |
| `dt` | 1.0 | simulation time step (s) |
| `smooth_speed` | `true` | Savitzky–Golay smoothing of the speed profile |

## Development & testing

```bash
conda activate dcp
pip install -r requirements.txt

pytest                 # run unit tests (no API keys required)
black .                # format
isort .                # sort imports
mypy dcpredictor/      # type-check the package
```

## Package internals

The toolkit's public API, module map, and algorithms are documented in
[`dcpredictor/README.md`](dcpredictor/README.md). Versioning (SemVer on the package only), commit, branch and
changelog conventions are in [`.claude/rules/git-workflow.md`](.claude/rules/git-workflow.md).

## License

MIT License — free for research and commercial use.
