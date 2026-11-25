# Fanfiction overhaul — shared contract (draft 1, Claude, 2026-11-24)

Status: **proposal for agreement with ChatGPT.** Nothing here is implemented yet. Agreed items get marked ✅.
Build order agreed with Anna: 1) novel menu cleanup (ChatGPT), 2) fanfiction overhaul (both), 3) characters and relationships,
4) finish the memory overhaul. Completed memory work (contract 2, hybrid, player overlays, nine layers) stays and is the foundation.
Paid testing: the earlier approval covers the memory overhaul only. Fanfiction real-model trials need Anna's separate approval.

## 0. Principles

1. **One source library, many playthroughs.** A source universe is imported and indexed once (`DB.universes[id]`) and never changed by play.
   Each playthrough keeps its own overlay (`se.canon`): rules, exceptions, event status, fates, relationships. Built on memory contract 2: universe = layer 9, playthrough = layers 1–8.
2. **Everything stays local.** Source text is indexed in the browser and stored on the device. Prompts get short, scene-relevant canon notes and excerpts, never whole chapters.
   Generated scenes must be original: no reproducing source passages (an originality check is part of testing).
3. **Narrative history is the truth.** Scores (trust and so on) are optional summaries of recorded events.
4. **Deterministic first, AI second.** Indexing, dependency tracking and rule checks are code. Model-assisted extraction is optional and batched.
5. **Nothing is silently invented.** Uncertain extractions are marked `canon:'uncertain'` and never treated as fact until confirmed.

## 1. Source universe (`DB.universes[id]`)

```
{ v:1, id, name, created, updated,
  sources: [{ id, title, kind:'novel'|'manga'|'anime'|'wiki'|'notes', priority:1..n, lang, chapters:[{n, title, hash, words}], coverage:{from,to}, indexedAt }],
  aliases: { "Raon Zieghart": ["Raon", "Young Master Raon"], ... },        // names, translations, titles
  records: [ UniverseRecord ],                                           // memory contract 2 records with layer 'universe'
  events:  [ CanonEvent ],
  chars:   { [name]: CharIdentity },
  rules:   { powers:[PowerRule], world:[text] } }
```

`UniverseRecord` = contract-2 record plus `{ ref:[SourceRef], canon:'source'|'fanon'|'uncertain', spoilerAt:{src, ch} }`.
`SourceRef` = `{ src, ch, para?, conf }`. Excerpts shown to the player are at most about 25 words.

## 2. Canon events and dependencies (butterfly effect)

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

## 3. Canon rules and exceptions (`se.canon.rules`, `se.canon.locks`, `se.canon.exceptions`)

```
rules: { history, personalities, appearances, powers, family, friendships, romance, fates, majorEvents, minorEvents, chronology, organizations, protagonistAchievements, ending }
       each 'locked' | 'adaptive' | 'free'          (defaults by story mode)
locks: [{ kind:'event'|'char'|'rel'|'fact', id }]      exceptions: [{ id, target, text, approved:true, t }]
```

These feed the existing v87 canon modes and the protected PLAYER INSTRUCTIONS AND LOCKED CANON block, which is never trimmed.

## 4. Story mode and perspective (`se.canon.mode`, `se.canon.pov`)

```
mode: { types:['oc'|'self'|'takeover'|'transmigration'|'reincarnation'|'regression'|'fixit'|'whatif'|'divergence'|'au'|'crossover'|'rolereversal'|'parallel'|'nextgen'|'prequel'|'sequel'|'missing'|'slice'|'ensemble'|'altending'],
        start:{src, ch, order}, takeover?: name, player:{name, desc, origin} }
pov:  { mode:'first'|'second'|'thirdLimited'|'omniscient'|'multi', who? }
position: { ch, order }                 // where the playthrough sits on the canon timeline
```

## 5. Characters

`CharIdentity` (source, read-only):
`{ name, aliases[], core:{personality, values, temperament}, speech:{tone, vocabulary, mannerisms, lines[] (short paraphrased examples)}, appearance, abilities[], affiliations[], ambitions[], arcs:[{fromCh, toCh, summary}] }`

Playthrough development is stored as memory records (character layer, `src: narrator|step|player`), each tied to the events that justify it.
**Knowledge boundary:** a character knows source facts revealed up to the story position (`spoilerAt`) that they plausibly witnessed, plus playthrough facts linked `knows:`.
Regressors and transmigrators get an explicit `foreknowledge` list, nothing else.

## 6. Relationships (memory relationship layer, extended)

`{ id:'rel:A | B', a, b, kinds:['family'|'friend'|'rival'|'mentor'|'romance'|'ally'|'enemy'], baseline (canon), trust?, affection?, respect? (-100..100, optional), history:[eventIds], private:bool, knownBy[] }`
Covers NPC-to-NPC relationships. Romance is optional, fictional and age-appropriate. Private developments are not known to others unless `knownBy` says so.

## 7. Fates (`se.canon.fates[name]`)

`{ original:text, target:'preserve'|'adapt'|'protected'|'free', current:text, changedAt?, why?, by:[recordIds] }`
"Protected" warns before an irreversible outcome; it does not remove every obstacle.

## 8. Crossovers

`se.canon.universes = [{ id, role:'primary'|'secondary', authority:1..n }]`, `se.canon.link:'portal'|'reincarnation'|'merged'|'parallel'`,
`powers:[{ from, to, rule:'separate'|'translated'|'hybrid'|'custom', scale:'original'|'normalized'|'custom', note }]`, timeline `aligned:true|false`.
Characters start knowing only their own universe.

## 9. Functions (engine, Claude) — signatures for the UI

| Function | Purpose |
|---|---|
| `ffIndex(file, opts) -> Promise<{universe, report}>` | Local EPUB/TXT/PDF-text indexing: chapters, names, aliases, candidate facts and events marked `uncertain`. Optional batched model pass (paid; Anna's approval). |
| `ffUniverse(id)`, `ffSaveUniverse(u)` | Read and write the source library. |
| `ffState(se)` | `{position, events:[{id, title, status, why}], fates, rules, upcoming[]}` for the Timeline & Fates screens. |
| `ffSetRule(se, key, value)`, `ffLock(se, kind, id, on)`, `ffException(se, target, text)` | Canon rules. Results use the `{ok, applied, reason}` shape from contract 2. |
| `ffSetFate(se, name, target)`, `ffEventStatus(se, id, status, why)` | Manual overrides (player-trusted). |
| `ffCanonFor(se, ctx)` | Scene canon retrieval within the spoiler boundary (used in prompt assembly). |
| `ffCheck(se, replyText)` | Rule and continuity check on a reply: rule breaks, forced impossible events, out-of-character signs, spoilers. No AI request. |

## 10. Who changes what (avoid overlapping edits)

| Area | Owner |
|---|---|
| Menus and sheets (`menuSheet` and the sheet UI in index.html), new `fanfic-ui.js/.css`, Fanfiction Studio, Timeline & Fates, inspectors, Memory Studio | ChatGPT |
| New `fanfic-engine.js`, `memory-v2.js`, `canon-engine.js`, prompt assembly (`buildMsgs`), send/memory pipeline in index.html, trial page, engine tests | Claude |
| This contract, MEMORY-API.md, fixtures | Both; changes noted in DEV-MANIFEST.md |

Branches: ChatGPT `ui-overhaul` and Claude `fanfic-engine`, both from `memory-overhaul`. Claude merges into `memory-overhaul` after both suites pass.
The test address (PR #7) shows the merged result. No version number until a release Anna approves.

## 11. Testing

Simulated fixtures first: a small invented universe (no copyrighted text) covering OC insertion, takeover, regression, a prevented event spreading to its
dependents, a protected fate, spoilers, NPC-to-NPC relationships, a crossover power rule and an originality check. Then long-run simulations. Real-model trials only with Anna's approval.

## 12. Open questions for ChatGPT

1. Menu category names: is "Canon & Fanfiction" where Source Library, Character Integration, Canon Management, Timeline & Fates, Relationships and Story Direction live?
2. Do default rule presets per story mode belong in the UI (ChatGPT) or the engine (Claude)? Proposal: engine provides `ffDefaults(mode)`, UI shows and edits them.
3. Visual references (manga/anime images): store in IndexedDB as blobs keyed by universe; images are never sent to the model unless the player asks (vision via OpenCode is untested).
