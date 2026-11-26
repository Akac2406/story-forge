# Source Indexing API (v105 target) — contract draft

Owner: Claude (engine + adapters + tests). ChatGPT: import-mode selector, indexing dashboard, progress, evidence inspector, enrichment UI.
Approved by Anna (2026-11-25): Phase 1 (local, no model cost) and Phase 2 (AI deep indexing), including running Phase 2 on her book within the 45% monthly stop.

## Why
The fanfiction import is a basic index: chapter list `{n, title, hash, words}` plus capitalized-name candidates (min 3 mentions, cap 200, empty profiles). Chapter text is dropped, no events or records are made, and Quick Create took the first 15 bare names. Result on a real 502-chapter EPUB: 200 characters, 0 events, 0 records, "source facts are mostly name fragments".

## Import modes
| Mode | Model requests | What it keeps |
|---|---|---|
| `basic` | none | today's index (chapter catalog, name candidates) |
| `smart` (default) | none | + chapter text on this device, character mentions/aliases, search, relevant retrieval |
| `deep` | yes, opt-in, estimated first | + AI analysis per chapter range: summaries, timeline events, character profiles, relationships, powers, terms, style |

## Storage
- Chapter text: IndexedDB `src:<universeId>:<sourceId>` → `[{n, title, text}]` (this device only). `source.text = {stored: true, chapters, chars, at}` in the universe records that it exists.
- Search index: built in memory from the stored text when needed (not persisted), so storage is the text itself.
- Backups: universes (with deep-index records) travel as today. Chapter text is large and copyrighted material the player owns; it is **not** in backups by default. `ffSourceStatus` reports when text is missing on a device; re-attaching the same file restores it (hash match).
- `ffSourceStorage()` → `[{universeId, sourceId, title, chapters, bytes}]` and a total, for a storage view; `ffDropSourceText(universeId, sourceId)` frees it (index and records stay).

## Phase 1 adapters (no model cost)
- `ffImportPreview(file, {mode: "basic"|"smart"|"deep", ...})` — as today; `smart`/`deep` also keep the text on commit.
- `ffAttachSourceText(universeId, file | {bookId}, {signal, onProgress})` → `{ok, matched, total, sourceId, reason}`. Enriches an **existing** universe: chapters are matched by hash to the existing source (≥ 80% match required, else `reason: "this file doesn't match the imported source"`); nothing is replaced; playthroughs untouched. `{bookId}` links a Library copy.
- `ffSourceStatus(universeId)` → `{mode, text: {stored, chapters, missing}, characters, aliases, events, records, deep: {done: [ranges], pending}, readiness: "basic"|"searchable"|"deep", warnings: []}` — readiness warnings for Quick Create ("no searchable text: facts will be names only", "deep index covers chapters 1–40 only").
- Characters: `smart` re-scores candidates with the text — mention count, chapters seen (first/last, spread), aliases (single names folded into full names, honorific/possessive variants), likely non-names flagged (places, titles, sentence-start words) and kept but marked `kind: "candidate"`; no hard cap of 200 (ranked; the top 400 kept). Existing characters are never removed or renamed; new data goes in `chars[id].stats = {mentions, first, last, chapters}`.
- `ffSearchSource(universeId, query, {maxChapter, limit, perChapter})` → `[{chapter, title, excerpt, score}]`: ranked passages (phrase matches > rare terms > names), at most `perChapter` per chapter for diversity, never past `maxChapter`.
- Quick Create: for an imported universe with stored text, `qcPreview` facts = the player's named characters (with mention stats) + ranked passages for the concept/character/preferences terms (ids like `c12.1` = chapter 12, passage 1). Facts stay data, cited by id; evidence shows `Chapter 12` instead of `u0`.
- During play (ChatGPT's point): when the scene mentions a name, place or term the index knows, the narrator prompt gets a short **SOURCE PASSAGES** section (≤ 2,500 / 1,600 / 1,000 characters by the money-saving setting), only from chapters at or before the playthrough's position (spoiler-safe), no extra requests. Off for character chats; a per-story switch.

## Phase 2 adapters (AI deep indexing)
- `ffDeepEstimate(universeId, {from, to})` → `{requests, inputTokens, maxOutputTokens, batches}` from the real text (batches of whole chapters up to ~24k characters).
- `ffDeepIndex(universeId, {from, to, signal, onProgress})` → `{ok, done: [n], failed: [{n, why}], added: {events, chars, records}}`. Per batch the model returns JSON; it is validated and merged:
  - chapter summaries → `u.summaries[n]`;
  - timeline events `ev:<u>:<n>` with `ch`, `order`, `who`, `title`, `imp`;
  - character profiles (core, abilities, affiliations, relationships) merged into existing characters (`canon: "source"`), aliases added;
  - powers/curses/terms/locations/factions as records `{kind, text, ch, spoilerAt: ch, source: {chapter}, confidence}`;
  - a style profile (descriptive choices only, never quoted text).
- Checkpoints: `u.deep = {v, done: [n], failed, at}` saved after every batch; pause = stop between batches; resume skips done chapters; re-running a range replaces only records it created (`src: "deep"`); manual and protected records are never touched; duplicates are merged by normalized title/term.
- Spoilers: every record carries its chapter; retrieval and Quick Create filter by `maxChapter` / playthrough position.
- Existing playthroughs adopt an enriched universe explicitly (`ffAdoptRevision(se, rev)`); until then they keep their pinned revision.

## Tests (planned)
Unit: chunking, scoring, alias folding, candidate flags, passage ranking/diversity/spoiler cut, deep-merge validation and de-duplication. Browser (mock model): import modes, attach by hash (match / mismatch), storage report, Quick Create facts from passages, play-time passages, deep index with pause/resume/failure/re-run, revision adoption, backups.
