# Quick Create API (Intelligent Fanfiction Creation) — draft contract

Status: engine (`site/quick-create-engine.js`, `SFQuick`; `tests/quick_create_unit.mjs` 19 checks; fixture `tests/fixtures/quick-create.json`) and app adapters (`qc*` in index.html; `tests/quick_create_browser.py` 16 checks with a mock model and stubbed lookups) are done on memory-overhaul. Not released. No paid calls in tests.

## Flow

1. **Research** `qcResearch(query, {signal})` → `{ok, reason, work: {title, kind, year}, facts[], sources[]}` — uses the app's existing lookups (`searchWorks`: AniList and similar; `wikiApi`: fandom wiki / Wikipedia via the connector). The OpenCode model cannot browse, so it never "looks things up" itself. Each fact: `{id, text, source: {title, url (https only)}, confidence: confirmed|uncertain}`. Or, for an imported universe, facts come from it (`SFQuick.factsFromUniverse`).
2. **Preview** `qcPreview({sourceTitle, concept, character, preferences?, universeId?, facts?}, {signal})` → `{ok, reason, blueprint, issues[], unsupported[], canon (summary), estimate: {inputTokens, maxOutputTokens}, usage}` — one bounded request (prompt ≤ 24k chars, ≤ 40 facts of ≤ 400 chars). Nothing is saved.
3. **Edit** `qcEdit(blueprint, instruction, {signal})` → a staged proposal `{ok, proposalId, blueprint, diff: [{path, from, to}], issues, staged: true}`; nothing changes until `qcAccept(proposalId)` (or `qcReject(proposalId)`). The model returns `{set: {path: value}, remove: [path]}`; only those paths change; edits that break the canon or touch a locked path are refused whole. See *Editing controls* below.
4. **Commit** `qcCommit(blueprint, {universeId?})` → `{ok, applied, reason, storyId}` — atomic: universe (from the import, or a small one built from research facts), story via `ffCreateStory`, gameplay/director/memory setup as the story blueprint (every new playthrough starts from it), cinema layout and appearance for that story. All or nothing: any failure restores the previous state.

## Blueprint fields

`title, premise, opening` (own words), `modes, player {name, desc, age}, takeover, start {ch}, pov {mode}, romance {pref, pacing}, rules, locks, exceptions, fates, foreknowledge` (validated by `SFFan.newCanon`, same as the Advanced wizard), `characters [{name, role, desc, canonId?}]`, `notes [{text, cite: [factId]}]`, `gameplay`, `director {...}`, `memory`, `appearance`, `styleProfile` (details below), `styleProfile {pov, tense: past|present, pacing: slow|measured|fast, dialogue: sparse|balanced|heavy, description: spare|moderate|lush, tone, structure}`, `sources [factId]`, `uncertain [text]`.

### Setup sections (extension 3, implemented)
Every part is checked by the real engine; anything refused is left out **and reported in `issues`** (never dropped silently). Pure helpers: `SFQuick.buildGame`, `cleanMemory`, `cleanAppearance`, `buildCinema`, `appearancePatch`.

- **`gameplay`** `{career: id|null, stats: [{id, name, min, max, start, hidden?}], quests: [{id, title, steps: [text], reward?: {xp?, <statId>: n}}], milestones: [{id, title, when: {stat, op, value}}], rules: [{id, when: {stat, op, value}, effect: {stats?: {<statId>: delta}, fail?: questId, unlock?: questId}, note, repeat?}]}`. Ids are lowercase (`a-z0-9_-`, up to 32). `op`: `< <= > >= ==`; `stat` may also be `level` or `day`. Built in order through `SFGame` (startCareer → defineStat → addQuest → addRule); a milestone becomes rule `milestone:<id>` with note "Milestone reached: <title>". Limits: 12 stats, 10 quests (8 steps each), 10 milestones, 12 rules. Any accepted part turns the game on for the story (`st.blueprint.game`, enabled).
- **`memory`** `{mode: "app" | "on", recall: bool, notes: [{text, who: [names]}]}`. `app` follows the app's structured-memory setting; `on` turns it on for this story (`se.memv2`). Recall needs structured memory, so `recall: true` sets `mode: "on"` (reported). Up to 10 notes of 300 characters (quoted passages refused): they become **protected memories** on the first playthrough: layer `permanent`, pinned, locked, source `player` (`qcnote0…`).
- **`appearance`** `{layout, preset?, cinematic?: {lighting, overlay, transition, dialogueBox, narration, textReveal, …}, theme?, uiLayout?, format?, colors?: {bg, card, accent, text}}`. `layout`/`preset`/`cinematic` go through `SFCinema` (preset first, then each setting on its own); the result is the first playthrough's `se.cv`. `theme`/`uiLayout`/`format`/`colors` go through `SFAppearance` and are saved in the story's appearance scope at commit (rolled back with the stories if the commit fails). The setup prompt lists the engines' real layouts, presets, cinematic values and themes.
- **`styleProfile`** adds `balance: narration|balanced|dialogue`, `innerMonologue: none|light|frequent`, `humor: none|dry|light|frequent`, `suspense: low|medium|high`, `rhythm: short|varied|long|flowing` to `pov, tense, pacing, dialogue, description, tone, structure`. All reach the narrator's SOURCE STYLE section.

## Commit safety (extension 5, implemented)
- `qcCommit(bp, {idempotencyKey?})` runs in stages: universe → story → setup → appearance → save. A failure at any stage, including full storage (appearance settings, or the story DB when there's no IndexedDB fallback), restores stories, universes and appearance settings exactly, returns `{ok:false, applied:false, reason}` and **keeps the session**, so the player can retry.
- `save()` now returns `true` when the data was stored (localStorage, or IndexedDB pending) and `false` otherwise; commit treats `false` as "storage full: the story was not saved".
- **No duplicates.** The idempotency key (default: the blueprint id) is stored as `st.fanfic.quick.key`. Committing the same key again (double click, retry after a lost response, a re-loaded draft) returns `{ok:true, applied:false, duplicate:true, reason:"already created", storyId}`; the UI should open that story. Pass a new `idempotencyKey` to make an intentional copy.
- Test hook: `window.__qcFailAt = "universe"|"story"|"setup"|"appearance"|"save"` (tests only).

## Change preview for a story in play (extension 6, implemented)
Works on one playthrough `se`. Nothing changes until `qcChangeApply`.
- `qcStoryView(se)` → what can change: `romance, rules, fates {charId: target}, locks, exceptions, pov, director (settings), gameplay {career, stats [{…, value}], quests [{…, status}], milestones, rules}, memory {mode, recall, notes (protected memories)}, appearance {cinematic}, styleProfile`, plus `frozen {pastEvents, upcomingEvents, turns, start}`. Past events = source events at or before the playthrough's position.
- `qcEstimateChange(se, instruction)`; `qcChangePreview(se, instruction, {signal})` (one model request, max 900 output tokens) or `qcChangePreviewPatch(se, {set, remove})` (the player's own change, no request) → `{ok, staged, proposalId, changes: [{path, from, to}], refused: [{path, reason}]}`. Paths are on the view (`appearance.colors.*`/`theme`/`uiLayout`/`format` show as `appearance.story.*`).
- Rules (refused parts are listed, the rest still applies):
  - The start is frozen: `title, premise, modes, player, takeover, start, opening, characters, notes, sources, uncertain` → "already played".
  - Locks and exceptions only on upcoming events; approved exceptions aren't removed here.
  - `gameplay.stats/quests/milestones/rules` and `memory.notes` can only be added to; existing entries, current values, quest progress and the career don't change.
  - `memory.mode` can only be turned on. Canon changes go through `SFFan` (setRomance, setRule, setFate, setPOV, lock, exception), director through `SFDirector`, cinematic through `SFCinema`, story appearance through `SFAppearance`, style through `SFQuick.cleanStyle`.
- `qcChangeApply(se, proposalId)` applies everything or nothing. Refused with "the story changed since the preview; preview again" if the playthrough changed after the preview. Never touches `se.turns`. `qcChangeReject(proposalId)`.
- `qcChangeHistory(se)` (last 10, newest first) and `qcChangeUndo(se)`: restores what the last change touched (playthrough parts and story appearance) if nothing changed since; otherwise "the story changed since that change; undo the settings one by one".

## First real-model run (2026-11-25) and what changed
Six real requests on live v102 with this code loaded in one tab (Frieren: Beyond Journey's End, an original character). The setup, a section rewrite and a story-change preview were good on the first try. Fixes from the run:
- Research picks the main work over spin-offs (`SFQuick.pickWork`: exact title/alternate title first, spin-offs/parts/seasons demoted, the original medium preferred), tries several names to find the wiki (`wikiNames`), skips gallery/season/release/front pages (`skipPage`) and turns fandom infobox text into one short line (`cleanWikiText`). Coverage counts only facts with real content (`coverage.useful`).
- Every prompt (setup, edit, regenerate, change) carries the field shapes with the engines' real option lists (`SFQuick.schemaLines`), including each director setting. Before this the edit prompt had no shapes and the model sent stats and quests without ids.
- Director settings are checked one by one (a value equal to the default is kept); style and director values accept common spellings (`enumOf`: "third limited" → thirdLimited); stats, quests, milestones and rules without an id get one from their name.
- `qcEdit` and `qcChangePreview` return `skipped: [{request, reason}]` for parts the model declined (e.g. renaming the player after the story started); the change preview also lists them in `refused` with `path: "request"`. UI: show `skipped` with the edit proposal.

## Guarantees (tested)

- Retrieved and imported text, and the player's request, are quoted as data; the model may only cite facts by id. Unknown citations, canon ids and careers are removed **and reported** in `issues`; unknown fields are reported in `unsupported` (never silently dropped).
- A canon the fanfiction engine rejects blocks the blueprint (`ok:false`, reason starts `canon:`).
- The style profile records choices only: quoted passages of 60+ characters are removed and reported; no exact author imitation.
- Edits cannot change `sources`/`uncertain`; unknown paths refused; diff lists only the touched paths.
- Content rules: no romance or sexual content with anyone under 18 or real people (also enforced later by `ffRomanceAllowed`/`ffCheck`); the player stays in control of their character.

## Preflight estimates (implemented)
Each builds the exact request that would be sent and sends nothing. All return `{ok, reason, inputTokens, maxOutputTokens, requests: 1}`.
- `qcEstimatePreview(input, {universeId | facts})` — same options as `qcPreview`; matches its `estimate`.
- `qcEstimateEdit(blueprint, instruction)` (max output 900).
- `qcEstimateRegenerate(blueprint, section, {instruction})` (max output 900); refuses locked/protected sections like `qcRegenerate`.
- Output caps live in `SFQuick.MAX_OUT` = `{preview: 1800, edit: 900, regenerate: 900}`.

Cancelling any request (`signal`) returns `{ok:false, reason:"cancelled"}` and changes nothing: the current blueprint, its history and any staged proposal stay as they were, and a reply that arrives after the cancel is ignored.

## Editing controls (implemented)
- **Blueprint id.** `qcPreview` gives each blueprint an `id` (the model cannot choose it). Patches can't change `id` or `locked`.
- **Locks.** `qcLock(bp, paths)` / `qcUnlock(bp, paths)` → `{ok, blueprint, locked}`; `bp.locked` is a list of dot paths (top-level field must be editable; `sources`/`uncertain` aren't lockable). A lock covers its parents and children: locking `romance` blocks `romance.pacing`, locking `romance.pacing` blocks setting `romance` whole. AI edits and regeneration never change a locked path — a patch that touches one is refused whole (`reason: "locked: <path> …"`), and the model is told the locked paths. The player's own direct edit can pass `qcApply(bp, patch, {force: true})`.
- **Regenerate one section.** `qcRegenerate(bp, section, {signal, instruction})` → staged proposal like `qcEdit`. `section` is a top-level field from `SFQuick.REGEN` (all except `sources`, `uncertain`); locked sections are refused before any request. The model answers `{"value": …}`; only that section changes.
- **Staged proposals.** One proposal at a time. `qcAccept(proposalId)` → `{ok, blueprint}` (recorded in history); `qcReject(proposalId)` → `{ok, blueprint: previous}` (nothing recorded). A UI that simply keeps the proposal's blueprint and calls any other adapter with it (`qcApply`, `qcEdit`, `qcRegenerate`, `qcLock`, `qcCommit`) has it accepted at that point, so history stays right; `qcUndo()` while a proposal is pending discards it (`{ok, blueprint: previous, discarded: proposalId}`).
- **Undo/redo per blueprint.** `qcUndo(id?)` / `qcRedo(id?)` → `{ok, blueprint}` or `{ok:false, reason}`; default id is the current blueprint. Each blueprint id keeps its own history (up to 50 steps); a new accepted change clears redo. `qcApply` (player edits) and `qcLock` are recorded immediately. `qcCommit` ends the session.

## Adapter details (implemented)

- `qcResearch(query, {characters?: [names], signal})`: `searchWorks` → best match becomes fact `f0`; `wikiFind` → the work's fandom wiki; up to 8 `wikiPage` reads (the work's main pages plus each named character). Character pages get canon ids `char:<work-slug>:<name-slug>` so takeover and locks can be validated. Returns `{ok, reason, work: {title, kind, year, author}, wiki, facts, sources}`; `reason: "cancelled"` on abort; when nothing is found it says so and suggests importing the source.
- `qcPreview(input, {facts?, universeId?, signal})`: with `universeId` uses the imported universe (facts from it unless given); otherwise builds a temporary universe from the research facts (nothing saved). One non-streaming request (max 1,800 output tokens). Sets the creation session context and clears the undo stack.
- `qcEdit` / `qcRegenerate` stage proposals; `qcApply(bp, patch, {force})` (manual edits; same patch shape) applies at once. History, locks and proposals: see *Editing controls*.
- `qcCommit(bp)`: re-validates; saves the research universe under a free id (never overwrites, e.g. `ember-academy-2`), creates the story with `ffCreateStory`, stores `blueprint {game (career started on defaults), director {enabled, settings}}`, `fanfic.setup {memoryRecall, layout}`, `fanfic.styleProfile`, `fanfic.quick {characters, notes, sources, uncertain}`. Any failure restores stories and universes exactly. New playthroughs get the canon, memory recall, cinematic layout, director and gameplay setup.
- Narrator prompt: stories with a style profile get a short "SOURCE STYLE" section (tense, pacing, dialogue, description, tone, structure) with "never copy text from the source".
