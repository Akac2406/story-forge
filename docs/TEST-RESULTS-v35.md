# Test results: Story Forge v35

Run on the exact packaged files. Desktop Chromium (Playwright), Linux. All AI services replaced by stand-in replies. Memory flag **off** unless a test turns it on.

## Summary
| Suite | Result |
|---|---|
| `node tests/memory_phase1_unit.mjs` | **15 passed, 0 failed** |
| `python tests/memory_phase1_browser.py` | **30 passed, 0 failed** |
| `python tests/reliability_v35_browser.py` (**new**) | **32 passed, 0 failed** |
| `python tests/run_all.py <epub>`: all 22 runnable suites (19 older regression suites plus the 3 above) | **All passed** |
| `crop30`, `imp30` (screenshot import) | **Not run.** They need the OOC screenshots, which aren't included. The importer code wasn't changed. |

## New checks in `reliability_v35_browser.py`
Every regenerate check runs twice, once with the memory flag **off** and once **on**.

**Snapshot (8 checks)**
- written before memory is added; holds the playthrough exactly as it was;
- memory created only after it;
- never overwritten by later turns;
- `memRestoreSnapshot` restores the original exactly;
- a failed snapshot means no memory is added, and the story still plays;
- flag off means no snapshot and no memory.

**Regenerate stopped before the request**
- budget pause: no request sent; reply, stats, facts, chapters and memory unchanged; reply still shown;
- after the pause, regenerating works and keeps both versions;
- *(flag on)* memory holds only the new version, and switching back restores the original's memory;
- missing API key: everything unchanged;
- Stop during the preparation steps: everything unchanged;
- an error while preparing the request: everything unchanged, and the person sees "Your earlier reply is kept.";
- paused `/impersonation`: reply kept, no leftover correction, and the next turn has no stray correction;
- *(flag on)* memory integrity check passes after all of the above;
- the live data and the saved copy matched at every step.

## About `look20`
During this work `look20` failed intermittently: 2 of 3, then 3 of 5 on v35, and 1 of 5 on v34. The cause was a **race in the test**. It clicked Send and only then began waiting for the typing dots, while the stand-in model blocked the test thread for 1.2 s, so the dots could come and go before the wait started.

The test now watches for the dots *before* clicking. That's the only change to an older test. Afterwards it passed **15 of 15** runs, alternating v33, v34 and v35, and it passes in the final full run. The app wasn't changed for this.

## Not covered by these tests (needs real-model or device testing)
- iPhone Safari: IndexedDB snapshot behavior, storage limits, private browsing.
- Snapshot storage growth on long playthroughs.
- Whether Stop is visible and tappable during short preparation steps on a phone.
- Real-model META output (EVENTS, LEARNED, SCENE): the purpose of the upcoming trial.
- Screenshot-import suites (`crop30`, `imp30`).
