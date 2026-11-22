# Story Forge v35: reliability update (before the real-model memory trial)

Baseline: v34 (Memory Phase 1). The memory engine stays **disabled by default** (`DB.memv2 === false`). Phase 2 has not started, and prompt assembly is unchanged.

## Changes

### 1. Safe snapshot before the first memory migration
- **New `memSnapshot(se)`.** Before memory is added to a playthrough for the first time, the whole playthrough is saved to IndexedDB under `snap:<sessionId>:pre-mem`, as `{at, ver, session}`.
- **The snapshot is verified.** It is read back and compared byte for byte.
- **It is never overwritten or deleted automatically.** If a snapshot already exists, it is kept.
- **No snapshot, no migration.** `memEnsure()` now refuses to create `se.mem` unless `se.memSnap.ok` is true. If IndexedDB is unavailable or the write fails, memory simply stays off for that story, and the story plays normally.
- **When the snapshot is taken:** at the start of `send()` and of `regen()`, before anything in the turn changes the playthrough, and only when the flag is on and the story has no memory yet.
- **New `memRestoreSnapshot(id)`** puts the snapshot back. It has no UI yet, by design.
- New optional field: `se.memSnap = {key, at, ok}`.

### 2. Regenerate is now all-or-nothing (fixes the lost-reply bug)
**Before:** `regen()` removed the original reply and rolled back stats, the chapter record, life data and memory *before* calling `send()`. If `send()` stopped before the request, all of that was lost. Causes included the budget pause, a missing key, Stop, an error while preparing the request, or a busy story.

**Now:**
- **`regen()` saves a copy first** (`RBK`) of everything it is about to change: the reply pair, stats, facts and the previous facts, the ending, suggestions, life and its timeline, the last chapter's record, and the `/impersonation` correction.
- **The regenerate counts as started only once the new reply has been added.** That is the commit point. It comes *after* the prompt is built, so an error while building the prompt is also covered.
- **If it never reaches that point, `regenRollback()` puts everything back.** That includes re-applying the original reply's memory delta (`ai.mx`) and clearing any `/impersonation` correction, so it can't leak into the next turn.
- **Errors before the request** now show "… Your earlier reply is kept." instead of failing silently.
- **Stop during the preparation steps** (checking the story record, tidying memory, reference and wiki lookups) now cancels before the request, through `PRE.cancel`. It used to do nothing until the request had started.
- **Leftover version data is cleared.** A pending regenerate's version list (`REGV`) can no longer leak into a later message.

### Files changed
| File | Change |
|---|---|
| `story-forge-pwa/index.html` | Snapshot functions; `memEnsure` and `memRecord` guards; snapshot and cancel checks in `send()`; commit point moved after the reply is added; `regen()` is now async and all-or-nothing, with `regenRollback()`; Stop button also cancels the preparation steps; `VER` set to 35 |
| `story-forge-pwa/sw.js` | Cache name set to `sf-v35` |
| `tests/reliability_v35_browser.py` | **New:** 32 checks |
| `CHANGELOG-v35.md`, `TEST-RESULTS-v35.md`, `patches-v35/` | **New** |

`memory-engine.js` is unchanged. A search of the diff confirms no theme, relationship, layout or CSS lines changed. Exact diffs against v34 are in `patches-v35/`.

### Compatibility
- Only new optional fields were added (`se.memSnap`), and nothing was renamed or removed.
- **Stories with memory off behave exactly as before**, apart from the regenerate fix, which applies whether the flag is on or off.

## A bug found and fixed during this work
The first version of the fix put the commit point before the prompt was built. An error there skipped the rollback, and the original reply was lost from the live data. The first test missed this because it read the saved copy, which hadn't been written yet. The commit point now comes after the new reply is added, and the tests now read the **live** data and also check that the saved copy matches it.

## Still needs real-model or device testing
1. **Snapshot on iPhone Safari.** The tests run in desktop Chromium. Safari's IndexedDB limits and private browsing could make the snapshot fail. If it does, memory stays off (safe), but that should be confirmed on the device.
2. **Snapshot size.** Very long playthroughs produce large snapshots, and they're never deleted automatically. Storage use on the phone should be watched during the trial. A cleanup or keep-last-N policy belongs with design Phase 8.
3. **Stop during preparation in real use.** The cancel path is tested directly. On the phone, the Stop button appears only once the screen redraws, so during very short preparation steps there may be nothing to tap. A visible "Preparing…" state would be a UI change, so it was left out on purpose.
4. **Real-model META output** for EVENTS, LEARNED and SCENE is still untested, as noted in Phase 1. This is the purpose of the upcoming trial.
5. **The `crop30` and `imp30` suites** (screenshot import) need the OOC screenshots, which aren't included. They weren't run on v35; the code they test wasn't changed.
