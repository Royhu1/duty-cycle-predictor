# `tests/` — unit tests

Pytest unit tests for the `dcpredictor` package. They exercise pure, deterministic logic and **require no API
keys and no data files**. The [`data/`](data/) subfolder holds sample measured GPS trip legs (gitignored) used
by the validation demo (`demo/predict_vs_measured_leg.ipynb`) — see [`data/README.md`](data/README.md).

```bash
conda activate dcp
pytest                 # or: pytest -v
pytest --cov           # coverage (configured in pyproject.toml: --cov=dcpredictor)
```

| File | Covers |
|------|--------|
| `test_driving_cycle_generator.py` | `DrivingCycleGenerator` helpers (haversine distance, speed interpolation, accel/decel update) and a small end-to-end `generate_use_static_behaviour` run on a synthetic route. |
| `test_vehicle_dynamics.py` | `dcpredictor.utils.lvd` functions: wheel power (flat vs uphill), diesel fuel-rate dict, and battery-rate dict (drive vs regenerative). |
| `test_models.py` | `VehicleParams` / `DrivingBehavior` dataclass round-trips (`to_dict` / `from_dict`) and `is_diesel` / `is_electric`. |

Test discovery and options are configured in `pyproject.toml` (`[tool.pytest.ini_options]`).
