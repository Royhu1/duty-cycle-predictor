# `examples/` — runnable example scripts

Small, self-contained scripts demonstrating the `dcpredictor` API. Install the package first (`pip install -e .`).

| Script | Needs API keys? | What it shows |
|--------|-----------------|---------------|
| `basic_usage.py` | No | Generate a speed profile from a sample route with `DrivingCycleGenerator`, then compute wheel power and diesel fuel rate with the `dcpredictor.utils.lvd` functions. Runs fully offline. |
| `predict_end_to_end.py` | Yes (`HERE_API_KEY`; `SRF_API_KEY` optional) | The full `DutyCyclePredictor.predict()` flow from origin/destination to a `DutyCycle`, using the default parameter presets. |

```bash
conda activate dcp
python examples/basic_usage.py          # offline
python examples/predict_end_to_end.py   # requires .env keys
```
