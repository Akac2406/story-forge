# v37: read metadata even without the [[META]] marker

## Why
The first real DeepSeek V4.1 Flash (OpenCode Go) trial showed that 34 of 41 replies ended with the metadata key lines but without the `[[META]]` marker. The app only looked for the marker, so:
- those lines appeared in the story text;
- STATS, CAST, BONDS, suggestions and the memory engine all ignored them.

## Changes
**`index.html`**
- New `metaAt(text)` finds where the metadata starts, trying these in order:
  1. the `[[META` marker;
  2. a bare `META`, `**META**` or `[META]` heading line;
  3. a trailing run of KEY: lines.
- The trailing-run rule needs at least 2 key lines, at least 2 of them known keys (NEXT, EVENTS, LEARNED, SCENE, STATS, CAST, BONDS, GOAL, QUESTS, STATUS, TOPICS, COUNTERS, CHAPTER, INFO, DEAD, ENDING), and nothing but list items after them. A capitalised label in the middle of prose, such as "WARNING: keep out.", is left alone.
- `vis()`, `applyMeta()`, `applySim()` and `memDiag()` now use `metaAt()`.
- Diagnostics record `nm: true` when the marker was missing.
- VER is now 37.

**`memory-engine.js`**
- Same detection, as `metaStart()`, which is also exported.
- `metaBlock()` now uses it, and `validateMeta()` flags `noMarker`.

**`sw.js`**
- The cache is now `sf-v37`.

## Not changed
- Prompts, themes, layouts, relationships and the memory default (still off). No Phase 2 work.
- Replies that do have the marker are handled exactly as before.

## Tests
- New `tests/metaless_v37.py`: 12 checks, all passing on v37; 6 of them fail on v36, as expected.
- Unit checks for `metaStart`: 10, all passing.
- Full `run_all.py`: all scripts pass. crop30, imp21, imp30 and lib29 are skipped because they need an EPUB or screenshots.

## Added after reviewing with ChatGPT
**Chapter recaps can no longer hold up the story.**
- Before the next turn, the app waits at most `DB.recWait` seconds for a recap (default 45). If the recap is slower, the turn goes ahead and the recap finishes in the background.
- `digest()` already threw away a recap if its chapter changed in the meantime.
- Each recap that misses the deadline is logged in `se.recLate` so slow recaps can be measured.
- Only one recap request per chapter runs at a time (the `DIGW` guard). Before this, a background recap and the pre-turn check could ask for the same chapter twice.
- The deadline belongs to the pending recap as a whole: a later turn waits only for whatever time is left, never a fresh 45 seconds.
- A branch made while a recap is pending is unaffected. The late recap is saved to the original story only.
- Test: `tests/recap_deadline_v37.py` (7 checks). With a recap delayed by 20 seconds and a 5-second deadline, the next reply arrives in about 5.4 seconds, the recap is saved later, and nothing is requested twice.

**The trial's knowledge check now also accepts paraphrases.**
- Each scripted fact can list accepted wordings (`alt`), and lines that negate the fact are ignored.
- The report shows two rows: the exact-keyword result, kept so results stay comparable, and the paraphrase result.
- The Python harness still uses exact keywords only.

**Still the same:** no prompt change, and the `[[META]]` reminder hasn't been added. ChatGPT and I agreed to confirm the parser fix alone first.
