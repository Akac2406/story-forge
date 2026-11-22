# Memory Engine, Phase 1: Event Ledger and Reversible Memory Deltas

**Baseline:** `story-forge-infinite-worlds-v33-phase0.zip` (ChatGPT's Phase 0).
**Result:** Story Forge v34. The memory engine stays **disabled by default** (`DB.memv2` is `false`).

## Status
| Item | Status | Evidence |
|---|---|---|
| 1. Parse `EVENTS`, `LEARNED`, `SCENE` | ✅ Done | Unit tests 1–3, 13–14; browser checks "on: …" |
| 2. Per-turn memory changes in `ai.mx` | ✅ Done | Browser: "every AI turn has a delta", "event anchored to its AI turn index" |
| 3. Rollback on regenerate, rewind, delete | ✅ Done | Browser: "regen: …", "rewind: …", "delete: …"; unit: "deleting a middle turn keeps the later chain correct" |
| 4. Correct memory when switching versions | ✅ Done | Browser: "switch: version 1 restores memory exactly as it was before regenerating", plus after a page reload |
| 5. Automated tests | ✅ 15 unit and 30 browser checks pass; the full older suite passes | See "Test results" |
| Extra: branching uses the deltas | ✅ Done (small, low-risk) | Browser: "branch: …" |

**Integration status:** Phase 1 works end-to-end in the browser tests with the flag on. It has **not** been tried with real model replies; every test uses stand-in replies (see "What remains unfinished"). Keep `memv2` off for normal play until a real-model trial has been done.

## Files changed
Only three files in `story-forge-pwa/` changed. Exact diffs are in `patches/`.

| File | Change |
|---|---|
| `memory-engine.js` | +Phase 1 API: `parseMeta`, `buildDelta`, `apply`, `undo`, `record`, `shiftTurns`, `empty`. Phase 0 functions are unchanged. |
| `index.html` | +6 small helper functions and 8 one-line hooks (listed below). `VER` changed from 31 to 34. |
| `sw.js` | Cache name changed from `sf-v30` to `sf-v34`. |

Unchanged: themes, `UI_LAYOUTS`, the relationship tracker (`relationshipSheet`, `REL_FIELDS`, `se.relationships`), bond meters, all layouts and CSS, `listen.html`, the manifest and the icons. The diff touches no theme, relationship or layout code (checked by searching the diff).

> Note on the baseline: v33's `index.html` declared `VER=31`, and `sw.js` still used `sf-v30`. Both now say 34, so installed copies get the update prompt.

### New helpers in `index.html` (all no-ops unless the flag is on)
| Helper | Purpose |
|---|---|
| `memOn(se)` | True only if `DB.memv2===true` or `se.memv2===true`, and `SFMemory` is loaded |
| `memEnsure(se,st)` | Creates `se.mem` from Phase 0's `SFMemory.migrate()` the first time it's needed. Old fields are not modified |
| `memMeta()` | The extra META instructions. At Save money level 2 (Maximum) it asks only for `EVENTS`, with importance 3 or higher |
| `memRecord(se,st,ai,raw)` | Parses the reply and stores the turn's delta in `ai.mx` |
| `memDrop(se,idxs)` | Undoes the deltas of removed turns, newest first, and repairs the "previous value" chain of later turns |
| `memSwap(se,t,v)` | Undoes the shown version's delta and applies the chosen version's delta |

### Hooks in existing functions
| Function | Change |
|---|---|
| `buildMsgs()` | Appends `memMeta()` to the META spec when the flag is on (not for character chats) |
| `send()`, success | `memRecord()` runs right after `applyMeta()`. Kept versions now store `mx` |
| `send()`, failed regenerate | The restored old version gets its memory back (`SFMemory.apply(o.mx)`) |
| `regen()` | Undoes the current version's memory before regenerating, and stores `mx` in the version list |
| `verSw()` | Calls `memSwap()` |
| `turnMenu()` "Delete message" | `memDrop([i])`, then `shiftTurns(i,-1)` so later events keep pointing at the right turn |
| `turnMenu()` "Rewind to here" | `memDrop(every later turn)` |
| `branchAt()` | The branch's copy of memory undoes every turn after the cut |

## Data format
New and optional fields only. **No existing field was renamed or removed.**
```js
se.mem          // Phase 0 schema v1; created lazily on the first reply with the flag on
se.memAt        // when it was created
se.mem.scene    // {where, who[], when}: current scene (new in Phase 1)
ai.tid          // stable id of an AI turn
ai.mx           // the turn's memory delta:
{ v:1, t, tid,
  ev:[event…],          // full copies of events added
  fa:[fact…],           // full copies of facts added (from LEARNED)
  nc:[{n, o}],          // characters created, with their initial object
  ml:[[name, eventId]], // character ↔ event links
  kn:[[name, factId, how]],  // who learned what, and how
  set:[[path[], old, new]],  // scene and character location changes
  seq:[before, after] }      // id counter (ids are never reused)
ai.vs[k].mx     // each kept version carries its own delta
```
Events follow the design: `{id,t,ch,tid,when,where,who[],wit[],kind,imp,text,open,src:"meta"}`. `kind` is one of: action, reveal, promise, betrayal, injury, death, item, travel, bond, secret, decision, threat, mystery. Promise, secret, threat and mystery events are marked `open`.

### Rules the engine follows
- **Deltas are self-contained.** They hold full copies, so an older version can be restored without calling the model again.
- **`apply` is idempotent.** Applying a delta twice has the same effect as applying it once.
- **`undo` restores a value only if it's still the one this turn set.** If a later turn changed it, the later turn inherits the old value instead. This keeps memory right after deleting a message in the middle.
- **Duplicates:** an event counts as a duplicate only if it is the same kind, has the same participants, is within 6 turns of an existing event, and overlaps it by 85% or more. Numbers count as words.
- **Learned facts** link to an existing fact only if the two overlap by 90% or more. The "(how)" part is stored separately, so it doesn't affect matching.

## Compatibility with saved stories
- With the flag off, nothing is created, the prompt doesn't change, and no `mx` is stored. The browser tests confirm the prompt and saved data are unchanged.
- **Old saves (v30 format) load and play unchanged.** With the flag on, they are migrated on the next reply. The old `facts`, chapter summaries and cast are left exactly as they were (checked in the browser tests).
- Turning the flag off after use is safe: `se.mem` and `ai.mx` are ignored, and the old memory path was never removed.

## How to enable it for testing
In the browser console of a test copy, run `DB.memv2=true; save()`. To enable it for one playthrough only, run `DB.sessions.find(s=>s.id===view.id).memv2=true; save()`. There is no UI toggle on purpose, because UI changes are out of scope for this phase.

## Test results (on the packaged files)
- `node tests/memory_phase1_unit.mjs`: **15 passed, 0 failed**.
- `python tests/memory_phase1_browser.py`: **30 passed, 0 failed**. Covers: flag-off behavior; META parsing into memory; three regenerations; switching versions both ways, including an exact match with the memory before regenerating; switching after a page reload; a failed regeneration (simulated provider error); deleting a middle message (events removed, later turn numbers shifted); rewind (events, knowledge and scene restored); branching (branch truncated, original untouched); an integrity check; and an old v30-format save with the flag off and then on.
- `python tests/run_all.py <book.epub>`: **all 21 runnable suites pass**, including the 19 older regression suites from v30.
  - `crop30` and `imp30` were skipped because they need the OOC screenshots, which aren't included since they contain a creator's art. They passed on v30 and Phase 1 doesn't touch the importer.
  - `look20` failed once during development and passed on 3 reruns. It also failed once on the **unchanged v33 baseline**. It is timing-sensitive (it waits for the typing animation), so this isn't a Phase 1 regression.

## What remains unfinished
1. **No trial with a real model yet.** Real models may format `EVENTS`, `LEARNED` and `SCENE` loosely. The parser accepts missing fields, bad importance values (clamped to 1–5), unknown kinds (become `action`) and "none". Real output may still need prompt tuning. Next step: play 30–50 turns on DeepSeek Flash and on a Gemini mode with the flag on, then review `se.mem`.
2. **Memory isn't used in prompts yet.** Phase 1 only *records* memory. Retrieval, knowledge limits and prompt assembly are phases 2–4.
3. **Hand-edited replies** ("Save edit" in the message menu) don't re-extract events. The old delta stays. Design question 4 is still open.
4. **`/impersonation` and ⏩ (move the story on)** go through the normal regenerate and send paths, so they're covered, but they have no dedicated tests.
5. **[Resolved in v35]** A pre-existing issue: if a regenerate is cancelled before sending (for example by the budget pause), the old reply is already removed. That's existing v29+ behavior; with the flag on, its memory is also undone, which matches the missing reply. Worth fixing separately.
6. **Migration** uses Phase 0's `migrate()` as written. Imported legacy events have `t:0`, so branching before the first Phase 1 turn keeps legacy memories. That's acceptable for now, and Phase 7 should anchor them properly.
7. **[Resolved in v35]** No snapshot was taken before migration (design §6.2). Plan it for Phase 8, or add it before turning the flag on by default.

## Running the tests on Windows
```powershell
pip install playwright
python -m playwright install chromium
node tests\memory_phase1_unit.mjs
python tests\memory_phase1_browser.py
python tests\run_all.py C:\path\to\a-book-you-own.epub
```
Run suites **one at a time**. Each script uses a fixed local port, so running two runners in parallel makes them collide.
