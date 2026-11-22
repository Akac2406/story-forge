# Test results: Story Forge v36

**All results are automated simulations in desktop Chromium. No real model was called.** The build workspace can't reach OpenRouter.

| Suite | Result |
|---|---|
| `node tests/memory_phase1_unit.mjs` | **19 passed, 0 failed** |
| `python tests/memory_phase1_browser.py` | **30 passed** |
| `python tests/reliability_v35_browser.py` | **32 passed** |
| `python tests/trial_sim_check.py`: 40-turn trial, clean and messy simulated profiles | **both passed** |
| `python tests/devmode_v36.py` | **3 of 3 passed** |
| `python tests/run_all.py <epub>`: every suite above plus the 19 older regression suites | **all passed** (run before `devmode_v36.py` was added; that one was run separately) |
| `crop30`, `imp30` (screenshot import) | **not run**: they need the OOC screenshots, which aren't included |

Simulated trial details: `MEMORY-TRIAL-REPORT-v36.md` §2, and `tests/realmodel/reports/*sim-*.md`.

## Still needs real-model or device testing
- **The live trial with DeepSeek and Gemini**: META consistency, accuracy, duplicates, knowledge and scene tracking on real replies. It needs your key and your approval of the cost.
- **iPhone Safari**: snapshot and IndexedDB behavior (carried over from v35).
- **Stop being visible during short preparation steps on a phone** (carried over from v35).
