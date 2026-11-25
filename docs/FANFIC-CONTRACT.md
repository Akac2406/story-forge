# Fanfiction overhaul — shared contract (v2, agreed by Claude and ChatGPT, 2026-11-24)

Status: **✅ agreed** (ChatGPT review of draft 1, all sections; refinements below folded in). Not implemented yet.
Build order agreed with Anna: 1) novel menu cleanup (ChatGPT), 2) fanfiction overhaul (both), 3) characters and relationships,
4) finish the memory overhaul. Completed memory work (contract 2, hybrid, player overlays, nine layers) stays and is the foundation.
Paid testing: the earlier approval covers the memory overhaul only. Fanfiction real-model trials need Anna's separate approval.

## 0. Principles

1. **One source library, many playthroughs.** A source universe is imported and indexed once (`DB.universes[id]`) and never changed by play.
   Each playthrough keeps its own overlay (`se.canon`): rules, exceptions, event status, fates, relationships. Built on memory contract 2: universe = layer 9, playthrough = layers 1–8.
2. **Stored and indexed locally; sent only when needed.** Source text is indexed in the browser and stored on the device. During generation, the relevant canon context leaves the device for the configured model provider (OpenCode). No whole-chapter transmission by default.
   Generated scenes must be original: no reproducing source passages (an originality check is part of testing).
3. **Narrative history is the truth.** Scores (trust and so on) are optional summaries of recorded events.
4. **Deterministic first, AI second.** Indexing, dependency tracking and rule checks are code. Model-assisted extraction is optional and batched.
5. **Nothing is silently invented.** Uncertain extractions are marked `canon:'uncertain'` and never treated as fact until confirmed.

## 1. Source universe (`DB.universes[id]`) ✅

Refinements: stable ids for sources, characters, events (`src:<slug>`, `char:<universe>:<slug>`, `ev:<universe>:<n>`); source **revisions** (`rev`, history kept);
incremental imports extend a universe; duplicate detection by chapter hash; explicit source-conflict records. **A playthrough pins the universe revision it started on** (`se.canon.rev`) and never changes silently when the source is revised; upgrading is an explicit, previewed action.

```
{ v:1, id, name, created, updated,
  sources: [{ id, title, kind:'novel'|'manga'|'anime'|'wiki'|'notes', priority:1..n, lang, chapters:[{n, title, hash, words}], coverage:{from,to}, indexedAt }],
  aliases: { "char:<universe>:<slug>": ["Name", "Title", "Translation"], ... },   // keyed by stable id
  records: [ UniverseRecord ],                                           // memory contract 2 records with layer 'universe'
  events:  [ CanonEvent ],
  chars:   { [charId]: CharIdentity },
  rules:   { powers:[PowerRule], world:[text] } }
```

`UniverseRecord` = contract-2 record plus `{ ref:[SourceRef], canon:'source'|'fanon'|'uncertain', spoilerAt:{src, ch}, knownBy?:[charId] }`.
`who` = who the fact is about; `knownBy` = who knows it. Secrets are known only by `knownBy`; other facts default to `who`, plus common knowledge (no `who`) once revealed.
`SourceRef` = `{ src, ch, para?, conf }`. Excerpts shown to the player are at most about 25 words.

## 2. Canon events and dependencies (butterfly effect) ✅

Refinements: each prerequisite is evaluated as `met` | `unmet` (may still happen) | `unknown` | `impossible`. A temporarily unmet condition never invalidates an event; only `impossible` does.
A **protected** event whose prerequisites become impossible creates a conflict for the player to resolve; it never forces an implausible outcome. Cycle detection on import.
`ffImpact(se, eventId, change)` previews downstream effects before a manual divergence.

```
CanonEvent { id, title, summary, src, ch, order (chronology index), when (in-world date text), who[], where,
             importance 1..5, requires:[eventId], needs:[{kind:'alive'|'at'|'knows'|'rel'|'has', who, value}], leadsTo:[eventId] }
```

Playthrough status (`se.canon.events[id]`):
`{ status:'unchanged'|'approaching'|'altered'|'prevented'|'delayed'|'replaced'|'impossible'|'protected', t, why, by:[recordIds], replacedBy? }`

Engine rules (deterministic):
- An event is `approaching` when the story position is within a few chronology steps.
- It becomes `impossible` when a required event is prevented, or a `needs` condition fails (for example a needed character is dead), unless it is protected.
- A changed status spreads down `leadsTo` in the same pass.
- The narrator is told only about upcoming events that are still possible, with the canon rules that apply to each.

## 3. Canon rules and exceptions ✅

Precedence (highest first): 1) what has already happened in this playthrough (established outcomes are never rewritten); 2) approved exceptions; 3) individual locks; 4) category rules; 5) story-mode defaults.
A lock that contradicts an established outcome becomes a conflict, not a rewrite. All changes are recorded (`ffHistory`) and reversible where practical (`ffUndo`).

```
rules: { history, personalities, appearances, powers, family, friendships, romance, fates, majorEvents, minorEvents, chronology, organizations, protagonistAchievements, ending }
       each 'locked' | 'adaptive' | 'free'          (defaults by story mode)
locks: [{ kind:'event'|'char'|'rel'|'fact', id }]      exceptions: [{ id, target, text, approved:true, t }]
```

These feed the existing v87 canon modes and the protected PLAYER INSTRUCTIONS AND LOCKED CANON block, which is never trimmed.

## 4. Story mode and perspective ✅

Refinements: modes combine; options for inherited memories; **player identity overlay**; explicit foreknowledge; configurable starting age; mode, rule and POV changes allowed mid-story (recorded).
**Takeover keeps these as separate records:** the canon identity (read-only), the player-controlled version, inherited memories, foreknowledge, and the personality developed in play.
Timeline sync tracks separately: source chapter, playthrough chapter, in-world date, character ages, last completed canon event, next possible canon event, incompatible events.

```
mode: { types:['oc'|'self'|'takeover'|'transmigration'|'reincarnation'|'regression'|'fixit'|'whatif'|'divergence'|'au'|'crossover'|'rolereversal'|'parallel'|'nextgen'|'prequel'|'sequel'|'missing'|'slice'|'ensemble'|'altending'],
        start:{src, ch, order}, takeover?: charId, player:{name, desc, origin} }
pov:  { mode:'first'|'second'|'thirdLimited'|'omniscient'|'multi', who? }
position: { ch, order }                 // where the playthrough sits on the canon timeline
```

## 5. Characters ✅

Refinements: stable character ids (not display names); age progression; identity provenance; explicit evidence for every knowledge item. A source revelation becoming available does **not** mean every character knows it.

`CharIdentity` (source, read-only), keyed by stable id `char:<universe>:<slug>`:
`{ id, name, aliases[], core:{personality, values, temperament}, speech:{tone, vocabulary, mannerisms, lines[] (short paraphrased examples)}, appearance, abilities[], affiliations[], ambitions[], arcs:[{fromCh, toCh, summary}] }`

Playthrough development is stored as memory records (character layer, `src: narrator|step|player`), each tied to the events that justify it.
**Knowledge boundary:** a character knows source facts revealed up to the story position (`spoilerAt`) that they plausibly witnessed, plus playthrough facts linked `knows:`.
Regressors and transmigrators get an explicit `foreknowledge` list, nothing else.

## 6. Relationships ✅

Refinement: **directional.** `rel:A>B` and `rel:B>A` are separate records (A may trust B without it being returned); each character keeps independent preferences and boundaries. Romance optional, fictional, age-appropriate, non-explicit.

Original draft shape (now per direction):

`{ id:'rel:<charIdA>><charIdB>', a:<charId>, b:<charId>, kinds:['family'|'friend'|'rival'|'mentor'|'romance'|'ally'|'enemy'], baseline (canon), trust?, affection?, respect? (-100..100, optional), history:[eventIds], private:bool, knownBy[] }`
Covers NPC-to-NPC relationships. Romance is optional, fictional and age-appropriate. Private developments are not known to others unless `knownBy` says so.

## 7. Fates ✅ (`se.canon.fates[charId]`)

`{ original:text, target:'preserve'|'adapt'|'protected'|'free', current:text, changedAt?, why?, by:[recordIds] }`
"Protected" warns before an irreversible outcome; it does not remove every obstacle.

## 8. Crossovers ✅

Refinement: character ids, event ids and abilities are namespaced by universe; incompatible world rules are resolved explicitly.

`se.canon.universes = [{ id, role:'primary'|'secondary', authority:1..n }]`, `se.canon.link:'portal'|'reincarnation'|'merged'|'parallel'`,
`powers:[{ from, to, rule:'separate'|'translated'|'hybrid'|'custom', scale:'original'|'normalized'|'custom', note }]`, timeline `aligned:true|false`.
Characters start knowing only their own universe.

## 9. Functions (engine, Claude) — signatures for the UI ✅

Added for the UI (ChatGPT request): `ffDefaults(mode)`, `ffListUniverses()`, `ffImportPreview(file, opts)` (with progress callback and cancel), `ffSearch(se, query)` (spoiler-filtered),
`ffSetMode(se, patch)`, `ffSetPosition(se, pos)`, `ffSetPOV(se, pov)`, `ffHistory(se)`, `ffUndo(se)`, `ffImpact(se, eventId, change)`, `ffRelationships(se, query)`, `ffValidate(se)`,
`ffExport(se, opts)` (credentials excluded by default), `ffRestorePreview(data)` (validates before anything is written). All mutations return `{ok, applied, reason, ...}` as in contract 2.
Rule presets live only in the engine (`ffDefaults`); the UI shows and edits them.

Original list:

| Function | Purpose |
|---|---|
| `ffIndex(file, opts) -> Promise<{universe, report}>` | Local EPUB/TXT/PDF-text indexing: chapters, names, aliases, candidate facts and events marked `uncertain`. Optional batched model pass (paid; Anna's approval). |
| `ffUniverse(id)`, `ffSaveUniverse(u)` | Read and write the source library. |
| `ffState(se)` | `{position, events:[{id, title, status, why}], fates, rules, upcoming[]}` for the Timeline & Fates screens. |
| `ffSetRule(se, key, value)`, `ffLock(se, kind, id, on)`, `ffException(se, target, text)` | Canon rules. Results use the `{ok, applied, reason}` shape from contract 2. |
| `ffSetFate(se, name, target)`, `ffEventStatus(se, id, status, why)` | Manual overrides (player-trusted). |
| `ffCanonFor(se, ctx)` | Scene canon retrieval within the spoiler boundary (used in prompt assembly). |
| `ffCheck(se, replyText)` | Rule and continuity check on a reply: rule breaks, forced impossible events, out-of-character signs, spoilers. No AI request. |

## 10. Who changes what ✅

| Area | Owner |
|---|---|
| Menus and sheets (`menuSheet` and the sheet UI in index.html), new `fanfic-ui.js/.css`, Fanfiction Studio, Timeline & Fates, inspectors, Memory Studio | ChatGPT |
| New `fanfic-engine.js`, `memory-v2.js`, `canon-engine.js`, prompt assembly (`buildMsgs`), send/memory pipeline in index.html, trial page, engine tests | Claude |
| This contract, MEMORY-API.md, fixtures | Both; changes noted in DEV-MANIFEST.md |

Branches: ChatGPT `ui-overhaul` and Claude `fanfic-engine`, both from `memory-overhaul`. Claude merges into `memory-overhaul` after both suites pass.
The test address (PR #7) shows the merged result. No version number until a release Anna approves.

## 11. Testing ✅

Added: UI navigation parity (no control lost), keyboard access, mobile layouts, migration, backup/restore, regeneration, source-revision isolation, branch isolation.

Integration cases (ChatGPT, agreed): empty universes and new playthroughs; existing stories without `se.canon`; partially indexed sources and cancelled imports;
invalid or outdated source references; rejected mutations that must not change saved data; large universes (hundreds of characters, thousands of events);
backup and restore with pinned revisions; mid-story changes to rules and perspective.

Status 2026-11-24 (late): engine parts 1-6 done and wired into the app on `fanfic-engine`: characters and takeover identity, knowledge (`knownBy`), directional relationships, fates, all mutations with history/undo, prompt canon block (`ffCanonFor`, only for stories with `se.canon`), reply check (`ffCheck` -> `ai.ffc`), validate/export/restore preview, and every `ff*` adapter function in section 9 plus `ffKnows`, `ffIdentity`, `ffSetRelationship`. Tests: fanfic_engine_unit (59), fanfic_app_browser (21), fanfic_large_universe (400 characters / 3,000 events: about 33 ms). Earlier status: engine parts 1-2 done on `fanfic-engine` (`site/fanfic-engine.js`, 27 unit checks): indexing, incremental imports with revisions and conflicts, presets, butterfly evaluation, conflicts for protected events, impact preview, cycles, precedence, spoiler-filtered search.

Simulated fixtures first: a small invented universe (no copyrighted text) covering OC insertion, takeover, regression, a prevented event spreading to its
dependents, a protected fate, spoilers, NPC-to-NPC relationships, a crossover power rule and an originality check. Then long-run simulations. Real-model trials only with Anna's approval.

## 12. Answers (agreed)

- Menu (top level): Story & Chapters · Canon & Fanfiction · Characters & Relationships · Memory & Continuity · World & Gameplay · Story Director · Appearance & Media · Advanced & Settings.
  Canon & Fanfiction holds Source Library, Character Integration, Canon Management, Timeline & Fates, Butterfly Effects, Crossovers. Relationships and Story Director stay top-level (original stories use them too). Irrelevant and unbuilt controls are hidden.
- Rule presets: engine `ffDefaults(mode)`; UI displays and edits.
- Images: local IndexedDB blobs with stable ids; explicit permission before any image goes to a model; originals preserved; OpenCode vision unverified.

## 13. Build order (agreed)

ChatGPT, in the `ui-overhaul` branch: 1) navigation overhaul (inventory every control first), 2) Fanfiction Studio, 3) Timeline, fates, relationships, divergence review, Memory Studio, 4) integration and responsive polish.
Claude, in the `fanfic-engine` branch: 1) universe store + import/indexing with revisions, 2) events/dependencies/butterfly + rules precedence, 3) characters, takeover identity, knowledge boundaries, directional relationships, fates, 4) prompt integration (`ffCanonFor`, `ffCheck`) + fixtures + long-run tests.
UI can build against contract-compatible fixtures without waiting: `tests/fixtures/fanfic-ember.json` (invented universe; checked by `tests/fanfic_fixture_check.mjs`) on branch `fanfic-engine`.

## Original open questions (draft 1)

1. Menu category names: is "Canon & Fanfiction" where Source Library, Character Integration, Canon Management, Timeline & Fates, Relationships and Story Direction live?
2. Do default rule presets per story mode belong in the UI (ChatGPT) or the engine (Claude)? Proposal: engine provides `ffDefaults(mode)`, UI shows and edits them.
3. Visual references (manga/anime images): store in IndexedDB as blobs keyed by universe; images are never sent to the model unless the player asks (vision via OpenCode is untested).


## ID conventions (all examples above)

Characters `char:<universe>:<slug>` · events `ev:<universe>:<n>` · sources `src:<slug>` · universe records `fact:<universe>:<slug>` / `fanon:<universe>:<slug>` · relationships `rel:<charIdA>><charIdB>` (directional) · fates keyed by charId. Display names are never used as keys.
