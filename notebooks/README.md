# `notebooks/` — exploratory Jupyter notebooks

Interactive notebooks for running and inspecting predictions. They import the installed `dcpredictor` package, so
run `pip install -e .` first; notebooks that hit the live HERE/SRF APIs also need keys in `.env`.

**Status legend:** ✅ uses the current `dcpredictor` API · ⚠️ legacy (references the pre-rename
`duty_cycle_prediction` API and needs updating) · 🔬 experiment harness (verify imports / API keys before use).

| Notebook | Status | Purpose |
|----------|--------|---------|
| `tutorial.ipynb` | ✅ | Walk-through of the prediction workflow. |
| `sample_usage.ipynb` | ⚠️ | Minimal usage — predates the package rename. |
| `sample_usage_with_maps.ipynb` | ⚠️ | Usage with map overlays — relies on map utilities no longer in the package. |
| `unit_test.ipynb` | ⚠️ | Ad-hoc component checks — predates the package rename. |
| `run_single_test.ipynb` | 🔬 | Run a single trip-leg prediction and inspect the result. |
| `run_single_test_reportonly.ipynb` | 🔬 | Single-leg run, report output only. |
| `run_single_test_for_srf2025annualmeeting.ipynb` | 🔬 | Single-leg run for the SRF 2025 annual meeting. |
| `run_mult_test.ipynb` | 🔬 | Batch-run multiple trip legs. |
| `analyze_mult_results.ipynb` | 🔬 | Aggregate and analyse batch results. |

> For current, runnable usage prefer [`../examples/`](../examples/) (`basic_usage.py` runs offline). The ⚠️
> notebooks reference the old `duty_cycle_prediction` API (removed before this layout refactor) and need updating
> before they will run. Generated outputs (CSV/HTML/figures) and notebook checkpoints are gitignored; mature,
> reproducible analyses belong in their own separate project repositories — this repository stays focused on the
> predictor itself.
