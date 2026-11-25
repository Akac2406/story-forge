# Quick Create API (Intelligent Fanfiction Creation) — draft contract

Status: engine done (`site/quick-create-engine.js`, `SFQuick`, pure; `tests/quick_create_unit.mjs` 19 checks; fixture `tests/fixtures/quick-create.json`). App adapters (`qc*`) are next; shapes below are the contract the UI can build against. No paid calls in tests (mock provider).

## Flow

1. **Research** `qcResearch(query, {signal})` → `{ok, reason, work: {title, kind, year}, facts[], sources[]}` — uses the app's existing lookups (`searchWorks`: AniList and similar; `wikiApi`: fandom wiki / Wikipedia via the connector). The OpenCode model cannot browse, so it never "looks things up" itself. Each fact: `{id, text, source: {title, url (https only)}, confidence: confirmed|uncertain}`. Or, for an imported universe, facts come from it (`SFQuick.factsFromUniverse`).
2. **Preview** `qcPreview({sourceTitle, concept, character, preferences?, universeId?, facts?}, {signal})` → `{ok, reason, blueprint, issues[], unsupported[], canon (summary), estimate: {inputTokens, maxOutputTokens}, usage}` — one bounded request (prompt ≤ 24k chars, ≤ 40 facts of ≤ 400 chars). Nothing is saved.
3. **Edit** `qcEdit(blueprint, instruction, {signal})` → `{ok, reason, blueprint, diff: [{path, from, to}], issues}` — the model returns `{set: {path: value}, remove: [path]}`; only those paths change; edits that break the canon are refused and the blueprint is unchanged. `qcUndo()` steps back through accepted edits (session-only stack). Manual edits use the same patch shape: `SFQuick.applyPatch(bp, patch, ctx)`.
4. **Commit** `qcCommit(blueprint, {universeId?})` → `{ok, applied, reason, storyId}` — atomic: universe (from the import, or a small one built from research facts), story via `ffCreateStory`, gameplay/director/memory setup as the story blueprint (every new playthrough starts from it), cinema layout and appearance for that story. All or nothing: any failure restores the previous state.

## Blueprint fields

`title, premise, opening` (own words), `modes, player {name, desc, age}, takeover, start {ch}, pov {mode}, romance {pref, pacing}, rules, locks, exceptions, fates, foreknowledge` (validated by `SFFan.newCanon`, same as the Advanced wizard), `characters [{name, role, desc, canonId?}]`, `notes [{text, cite: [factId]}]`, `gameplay {career}`, `director {...}`, `memory {recall}`, `appearance {layout}`, `styleProfile {pov, tense: past|present, pacing: slow|measured|fast, dialogue: sparse|balanced|heavy, description: spare|moderate|lush, tone, structure}`, `sources [factId]`, `uncertain [text]`.

## Guarantees (tested)

- Retrieved and imported text, and the player's request, are quoted as data; the model may only cite facts by id. Unknown citations, canon ids and careers are removed **and reported** in `issues`; unknown fields are reported in `unsupported` (never silently dropped).
- A canon the fanfiction engine rejects blocks the blueprint (`ok:false`, reason starts `canon:`).
- The style profile records choices only: quoted passages of 60+ characters are removed and reported; no exact author imitation.
- Edits cannot change `sources`/`uncertain`; unknown paths refused; diff lists only the touched paths.
- Content rules: no romance or sexual content with anyone under 18 or real people (also enforced later by `ffRomanceAllowed`/`ffCheck`); the player stays in control of their character.
