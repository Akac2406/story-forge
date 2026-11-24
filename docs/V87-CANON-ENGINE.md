# v87 Canon & Instruction Enforcement: engine side (Claude)

Branch `v87-canon`, based on v86 (`0a931cc`). Development build: not deployed, no paid calls made.

## Why notes and canon were ignored (audit of v86 `buildMsgs`)
1. User Notes sat in the middle of a long system prompt, after the wiki notes and source passages. The final message repeated only the metadata format.
2. Six sections each claimed authority, with no order between them.
3. Canon retrieval was a substring keyword match over the last 3 turns plus every character ever met. Entries were added in list order until the budget ran out, and anything after that was dropped silently.
4. `OOC:` directions vanished once their turn left the history window.
5. Who-knows-what from the memory engine never reached the narrator (Memory Phase 2 not started).
6. Strict canon leaned on the model's own knowledge of the base story.

## What changed
- **New file `site/canon-engine.js`** (`window.SFCanon`): pure functions, with no DOM, network or paid calls. It is added to the offline cache list.
- **`buildMsgs` builds the prompt from named sections:**
  - role and rules, then pacing/agency (`paceAgencyPrompt(se)` if the UI defines it);
  - **PRIORITY** statement;
  - **PLAYER INSTRUCTIONS AND LOCKED CANON** block;
  - era, story setup (and `canonModePrompt(se, st)` if defined);
  - relevant canon, player character, and the rest as before;
  - reply format.
- **Precedence:**
  1. OOC in the latest message;
  2. must-notes;
  3. locked and player-confirmed canon;
  4. story record;
  5. retrieved canon, source and wiki;
  6. the model's own knowledge.

  In the `au` and `creative` canon modes, this playthrough's story record outranks base canon.
- **Protected block:** must, should and style notes (scoped), earlier standing OOC directions, locked canon and confirmed canon. It is never trimmed, and must-notes are echoed in the final message before the model writes.
- **Size control:** if the prompt exceeds 90k/60k/36k characters (by saving level), optional sections are dropped in this order: research, wiki notes, source passages, characters, long-term memories, life log, retrieved canon, open threads, recent memory, story record. If the protected block alone exceeds 24k/16k/10k characters, the send stops with a message and the player's draft is kept. Notes are never shortened.
- **Retrieval (`SFCanon.lore`):**
  - entries are scored by hits in the action, the last turn, the last 3 turns and the characters present in the scene, plus priority;
  - matching is whole-word, with aliases, plurals and possessives;
  - the budget is filled by score;
  - locked entries are always included;
  - dropped entries are reported with a reason;
  - timeline markers (`after`/`before`) are shown with the entry.
- **Extraction (`SFCanon.suggestEntries`):** draft Canon Bible entries from recurring names in source passages, for the player to approve. No model call.
- **Divergence tracking:**
  - a `CANON:` metadata line is requested when a Canon Bible exists and the mode isn't creative;
  - it is parsed into `se.divergences` on commit (strict drift is `open`; AU drift is recorded as `au`, accepted);
  - a local check flags a dead character speaking;
  - a failed or cancelled regeneration changes nothing;
  - `branchAt` trims records the same way as other per-turn data.
- **Shared helpers** for the UI: `promptReport(se)` (null before the first build), `activeNotes(se, st, hist, action)`, `detectStandingOoc(text)`, `canonEntryId(st, entry, index)`.
- **Tests:** `tests/canon_engine_v87.mjs` (38 unit checks) and `tests/canon_v87_browser.py` (27 checks against the real app, with simulated replies). `run_all.py` now runs every Node test in the folder; two of ChatGPT's (`v85_sw_scope`, `world_era_v86`) weren't being run before.

## Memory Phase 2 review
- **Status:** built, **off**. `SFCanon.knowledge()` produces "Current scene", "X knows / Does NOT know" and "Recent key events" from the memory engine, read-only. It is used only when `se.memPrompt` is true **and** story memory is on for that story. Nothing sets `memPrompt`.
- **Why it's gated:** it changes what the narrator sees, so it needs Anna's approval and a paid comparison run.
- **Proposed test:** a Cedar Ridge replay with and without it, scoring knowledge leaks.
- **Risks to check in that run:**
  - stale `scene.who` after a scene change;
  - "Does NOT know" lists naming secrets the narrator would otherwise not have mentioned. They are labelled as constraints, but this needs watching.
- **The memory engine (`memory-engine.js`) is unchanged.**

## Left to the UI side (ChatGPT)
- Notes editor (`DB.notes` / `se.notes`);
- Canon Bible editor (extends `st.entries`, assigns `id`);
- canon mode picker and `canonModePrompt`;
- `paceAgencyPrompt`;
- inspectors (from `promptReport`);
- divergence review UI;
- "Pin as note" (from `detectStandingOoc`);
- safe chapter regeneration;
- the version bump to 87.
