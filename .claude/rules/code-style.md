> Python code style — referenced from the root `CLAUDE.md` "## Code Style" section via `@import`.
> Editing here = editing the code-style conventions for the whole project (committed with `.claude/`).

Python code follows PEP 8 and uses the tools configured in `pyproject.toml` (tool tables only — the repository
is not packaged; install the tools via `requirements.txt`) for a uniform style:

- **Formatting**: `black` (line length 88).
- **Import ordering**: `isort` (profile `black`; stdlib / third-party / local — three groups; `known_first_party = ["dcpredictor"]`).
- **Static typing**: `mypy` (strict; see `[tool.mypy]`). Public functions should annotate parameters and return values.

### Naming rules

| Object | Style | Example |
|--------|-------|---------|
| Package / module file | `snake_case` | `dcpredictor`, `driving_cycle_generator.py` |
| Function / method / variable | `snake_case` | `compute_desired_speed_2_next_action`, `haversine_distance` |
| Class | `PascalCase` | `DutyCyclePredictor`, `EnergyProfileGenerator`, `VehicleParams` |
| Constant / module-level config | `UPPER_SNAKE_CASE` | `VERSION_DATE`, `_FALLBACK_VERSION` |
| Internal / private (module / function / attribute) | leading underscore | `_haversine_distance()`, `_is_route_df_valid()` |

- Keep abbreviations consistent across the project (`dc` = driving cycle, `lvd` = longitudinal vehicle dynamics,
  `srf` = SRF platform, `gps`, `ep` = energy/power).
- Quantities carrying physical units state the unit in the name: `mass_kg`, `velocity_mps`, `gradient_degrees`,
  `fuel_rate_L_hr`, `wheel_power_kW`, `dt` (seconds).
- Prefer `pathlib.Path` for paths and f-strings for formatting.

### Comments / docstrings language

- **Code comments and docstrings committed to the repository are written in English** — even when the working /
  chat language is Chinese. The codebase is migrating away from mixed-language comments: when you touch a function,
  prefer leaving its docstring/comments in English. Chinese is used only for (a) interactive chat and (b) any
  gitignored local notes.

### One-off / temporary scripts

- Name throwaway scripts `_tmp_*.py` and keep them in `tmp/` (gitignored); delete after use and do not
  reference them in any README.
- Do not drop one-off scripts in the repository root — they belong in `tmp/` (see `housekeeping.md`).

### Sub-project independence (reproducible-archive convention)

The demo workspace (`demo/`) should be a
self-contained, reproducible archive — deletable or archivable on its own without breaking anything else:

- The only code dependencies allowed are: the Python standard library, pip packages, the versioned
  `dcpredictor` package (imported from the repository root), and the sub-project's own files.
- **`sys.path.insert` pointing at another sub-project is forbidden.** If you need shared code, import it from
  `dcpredictor`; if it does not belong there yet, copy it with a provenance header (source path, copy date, reason).
- **Rule of three**: logic reused by 3+ sub-projects and already stable should be promoted into the `dcpredictor`
  package (bump a SemVer minor), not copied endlessly.
- A sub-project reads sample data from `tests/data/` (gitignored) and writes its own outputs into its own
  `results/` / `figures/` (gitignored); it must not read another sub-project's outputs. Cross-linking documents
  (README links) is fine.

> The package's own architecture conventions (public API, module map, key algorithms) live in
> `dcpredictor/README.md`. This file governs Python style only.
