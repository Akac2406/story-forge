# Story Forge v36: memory trial preparation

Baseline: v35. The memory engine stays **off by default** (`DB.memv2 === false`). Phase 2 has not started, and prompt assembly is unchanged. Themes, layouts and relationship systems are untouched; a search of the diff confirms no lines in those areas changed.

## App changes (`story-forge-pwa/`)
| File | Change |
|---|---|
| `memory-engine.js` | `metaLine()` now reads lists split over several lines (bulleted or numbered) and strips bold `**` around keys. Importance written as a word is understood (high → 4, critical → 5, …). New read-only `validateMeta(raw)` for diagnostics. |
| `index.html` | New `memDiag()` records per-turn META diagnostics in `se.memDiag` (only while memory is on for that story; capped at 300 and never interrupts a reply). New `memDevEnable(id)` turns memory on for one playthrough, only on localhost or with `?dev=1`. `VER` is now 36. |
| `sw.js` | Cache name is now `sf-v36`. |

New optional session fields: `se.memDiag[]`, `se.memDev`. Nothing was renamed or removed. Diffs against v35 are in `patches-v36/`.

## New test tooling
- `tests/realmodel/scenario.json`: the 40-turn trial story, with per-turn expectations.
- `tests/realmodel/run_trial.py`: the trial harness, in simulated mode (no cost) or live mode (real OpenRouter calls; needs your key in an environment variable, a spending cap and a typed confirmation).
- `tests/trial_sim_check.py`: runs both simulated profiles as part of the suite.
- `tests/devmode_v36.py`: checks that development mode works only on local addresses or with `?dev=1`, and never turns memory on globally.
- `tests/memory_phase1_unit.mjs`: now has 19 unit tests (4 new).

## Note on `?dev=1`
On the live site, adding `?dev=1` to the address lets `memDevEnable()` be called from the browser console. It still affects only the chosen playthrough, and there's no button for it. If you'd rather it work only on localhost, remove the `?dev=1` part of the check.

## Harness update: OpenCode-only DeepSeek trial
- `run_trial.py --provider opencode` runs the live trial on DeepSeek V4.1 Flash through your OpenCode Go connector. It reads `OPENCODE_API_KEY` and `STORYFORGE_CONNECTOR` from the environment, asks you to type `opencode` to confirm, and stops at an estimated 5-hour Go-limit percentage (`--max-pct`).
- The cancel test on OpenCode uses the missing-key path, because the budget pause only applies to OpenRouter.
- Reports list requests by destination and redact the connector address.
- `trial_sim_check.py` also runs a simulated OpenCode trial. It passed, with 43 of 43 requests going to the connector and none to OpenRouter.
- The app files are unchanged from v36.

## Phone trial page (v36, same app build)
- New files: `story-forge-pwa/memtrial.html`, `memtrial.js` and `trial/scenario.json`. `index.html`, `sw.js` and `memory-engine.js` are unchanged.
- The page loads a copy of `index.html` in an iframe with three exact text substitutions: the storage key, the IndexedDB name, and the service-worker registration. If those strings ever stop matching, it refuses to run.
- It drives the copy with the app's own `send`, `regen`, `branchAt` and version buttons, and scores it the same way as `run_trial.py`.
- New test: `tests/phone_trial_check.py` (27 checks, picked up automatically by `run_all.py`).
