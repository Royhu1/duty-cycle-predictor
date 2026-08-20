> Naming conventions — referenced from the root `CLAUDE.md` "## Naming Convention" section via `@import`.
> Editing here = editing the file / directory / data naming conventions for the whole project (committed with `.claude/`).

> This file governs **project-level data / artefact / file / directory naming**. Python identifiers
> (`snake_case` / `PascalCase` / `UPPER_SNAKE` / private leading underscore), unit suffixes and one-off script
> naming are in `code-style.md`; branch / commit / version-tag / changelog naming is in `git-workflow.md`.

### Vehicle / directory

- **Vehicle registration**: uppercase, no spaces, exactly as on the plate (e.g. `AY71UCD`, `FX73VAE`);
  used as the `<REG>` token in data folders (`tests/data/<REG>/`), parameter presets (`vehicle_params.json` keys),
  and result folders.
- **Folders**: lowercase `snake_case` (e.g. `demo`, `tests`); the core package directory is `dcpredictor/` at
  the repository root.

### Date / period

- Data fields and per-record timestamps: ISO `YYYY-MM-DD` (or full ISO 8601 with time).
- GPS trip-leg files: `<YYYYMMDD>_<REG>_Leg<N>.csv` (e.g. `20250227_AY71UCD_Leg1.csv`).
- Date-bearing result folders use compact `YYYYMMDD`; a period uses `YYYYMMDD_YYYYMMDD` (start_end).

### Parameters & presets

- Vehicle / driving presets live in `dcpredictor/params/{vehicle_params,driving_behavior}.json`, keyed by
  `"default"` or a `<REG>`; load them via `load_default_vehicle_params(<key>)` / `load_default_driving_behavior(<key>)`.

### Figures & outputs

- Figures are PNG, written into a workspace's own `figures/` or `results/` folder; they must be reproducible from a
  committed script in that workspace (no hand-drawn, plot-and-delete figures).
- Generated data products (CSV/HTML) are gitignored; only the generating code + documentation are committed.
