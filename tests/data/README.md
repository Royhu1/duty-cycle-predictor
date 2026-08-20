# `tests/data/` — sample GPS trajectory data

Measured vehicle trip legs used by the validation demo (`demo/predict_vs_measured_leg.ipynb`) and any
data-driven tests, organised per vehicle registration:

```
tests/data/
└── <REG>/                       # e.g. AY71UCD/
    └── <YYYYMMDD>_<REG>_Leg<N>.csv
```

**Only this README is committed** — the CSVs are gitignored and supplied separately (or downloaded via
`SRFLoggerDataDownloader`). The unit tests in `tests/` do **not** depend on these files; they run on synthetic
data with no API keys.

## CSV columns

| Column | Description |
|--------|-------------|
| `Latitude`, `Longitude` | GPS coordinates |
| `UnixTime` | Time of measurement (ms) |
| `Spd_Kmph_x` | Vehicle speed (km/h) |
| `distance_gps` | Cumulative GPS distance (m) |
| `MassKg` (optional) | Vehicle mass (kg) |
| `FuelRate` (optional) | Measured fuel rate (L/hr) |
