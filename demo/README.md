# `demo/` — usage demos

Jupyter notebooks demonstrating how to use the `dcpredictor` package. Run `pip install -e .` in the
repository root first (conda env `dcp`); start Jupyter from this folder so the relative paths resolve.

| Notebook | Needs | Shows |
|----------|-------|-------|
| `basic_usage_offline.ipynb` | nothing | Offline building blocks: synthetic route → `DrivingCycleGenerator` speed profile → wheel power + diesel fuel rate via the `lvd` functions. |
| `predict_end_to_end.ipynb` | `HERE_API_KEY` (`SRF_API_KEY` optional) | The full `DutyCyclePredictor.predict()` pipeline: route → speed / gradient / energy profiles, with plots. |
| `predict_vs_measured_leg.ipynb` | `HERE_API_KEY` + sample data | A prediction validated against a measured GPS trip leg from [`../tests/data/`](../tests/data/): speed-profile and cumulative-fuel comparison with error table. |

API keys go in the repository-root `.env` (copy `.env.example`; the file is gitignored). Each notebook that
calls the live APIs makes **one** HERE routing request per run — mind your monthly quota when re-running.

Cell outputs are cleared before committing (see `.claude/rules/code-style.md`); run a notebook top-to-bottom
to regenerate them. Generated outputs (CSV/HTML/figures) belong in a gitignored `results/` or `figures/`
folder here, never in git.
