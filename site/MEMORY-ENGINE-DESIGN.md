# Story Forge: Memory & Continuity Engine
Design and implementation proposal, v1. Target codebase: Story Forge v30 (`app/index.html`).

> **Scope.** This is a design only. No source files have been changed. Nothing here changes the UI or the relationship system (bond meters, relationship features) that is being built separately. Where the two touch, this document defines a **read-only interface** the memory engine uses.

---

## 0. Summary

Story Forge already has several memory layers: rolling notes, chapter summaries, a fact list, long-term memories, canon notes, reference passages and character profiles. Each works on its own, but together they have five structural weaknesses:

1. **Memory is mostly free text.** Facts, summaries and notes are prose with no links back to *when* or *why* something became true. Nothing can be undone precisely, and nothing can be checked mechanically.
2. **Characters share one omniscient memory.** Every NPC effectively knows every fact in the prompt. Nothing records who learned what.
3. **Retrieval is keyword-only and mixed into one big system prompt.** Old but important events get lost when they don't share words with the current scene. And because the dynamic parts sit inside the system prompt, **prompt caching is mostly defeated**, which matters a lot for cost.
4. **Undo, regenerate, rewind and branch are lossy.** Stats and age are snapshotted, but facts, memories, cast changes, quests and the story record are not. Branching before the last memory checkpoint throws away all long-term memories.
5. **Storage is one big JSON record in localStorage.** Long stories approach the browser quota (about 5 MB), and there are no versioned snapshots to recover from corruption.

The proposed engine replaces these with these parts:
- an **event ledger**, the single source of truth for what happened;
- **derived views**: facts, character state, knowledge, summaries;
- a **context budgeter** that assembles prompts in a cache-friendly order;
- **turn-level memory deltas**, so every change can be undone exactly;
- **per-session storage in IndexedDB**, with snapshots and a full backup.

It is built **additively behind a flag** with a lossless migration, so no saved story is lost.

---

## 1. How memory works today

Function names refer to `app/index.html`.

| Layer | Where it lives | Written by | Read by | Notes |
|---|---|---|---|---|
| Raw history | `se.turns[]` | `send()` | `buildMsgs()` via `rawFrom()` | Up to `2*BUD()` chars (48k, 24k or 12k chars by Save money level) |
| Rolling notes | `se.temp` (bullets, under 250 words) | `summarize()` (cheap model) | `buildMsgs()` | Replaced each time and lossy; turns before `se.upto` survive only here |
| Long-term memories | `se.mems[] {t,x}` | `summarize()` when `temp` grows and the record is off | `buildMsgs()` (budget 6000/3000/1500 chars) | No turn anchor, so branching can't tell old from new |
| Chapter summary | `chaps[k].sum` | `digest()` when a chapter is done | `recText()` | Good, but prose only |
| Fact list | `se.facts[]` (strings, up to 70) | `digest()` rewrites the **whole list** each chapter | `recText()` | Facts can silently disappear when the model rewrites the list; no provenance |
| Older chapters | `se.saga` | `foldRec()` | `recText()` | Folding loses detail |
| Contradictions | `chaps[k].conf[]` | `digest()` (CONFLICTS) | `confNote()` banner | Only after a chapter ends; no fix action |
| Canon notes | `st.entries[] {k,t,a}` | builder, editor, imports | `loreFor()` keyword match | Static, shared by every session of a story |
| Reference passages | IDB `ref:*` chunks | `addRef()`, `wikiImport()` | `refPick()` (keyword with IDF) | Good engine, reusable |
| Wiki lookups | `sf-wiki` cache | `wikiPick()` | `buildMsgs()` | |
| Characters | `se.cast{name:{r,l,t,a,b,ch,u,pic}}` | `applyMeta()` CAST / BONDS | `buildMsgs()` (top 40/25/12 by recency) | Traits are overwritten freely, so personality can drift |
| Per-turn state | `[[META]]` lines | model | `applyMeta()` | STATS, CAST, GOAL, DEAD, STATUS, BONDS, QUESTS, TOPICS, INFO, COUNTERS, CHAPTER, NEXT… |
| Undo data | `ai.ps` (stats before), `ai.pl` / `ai.ln` (life), `ai.st2`, `ai.vs` (versions) | `send()`, `regen()` | `regen()`, `branchAt()`, `verSw()` | Nothing else rolls back |

**Prompt order today.** `buildMsgs()` puts everything in **one system message**: rules, mode, formats, title and canon, the turn-specific canon notes from `loreFor`, the cast list, wiki notes, reference passages, user notes, story record, memories, temp, stats, "This is turn N", the META spec. Then come the history and the action. Because turn-specific content (wiki notes, passages, temp, "turn N") sits *inside* the system prompt, the prompt prefix changes every turn. Automatic prefix caching on DeepSeek, OpenAI and Gemini then misses almost entirely.

---

## 2. Design principles

1. **Events are the truth; everything else is derived.** Facts, summaries, knowledge and character state are views computed from or linked to events. A view can always be rebuilt.
2. **Every change is tied to a turn.** Each AI turn records the memory delta it caused, so regenerate, rewind, delete and branch can undo it exactly.
3. **Stable first, dynamic last.** Prompts are assembled so the long, unchanging part comes first and is byte-identical between turns, which keeps it cached.
4. **Cheap extraction now, careful review later.** Each reply adds about 60 META tokens of structured events. Deeper review runs once per chapter on the cheap model, as it does today.
5. **Additive and reversible.** A new `se.mem` object sits alongside the existing fields. Old fields stay readable and keep being written during the transition. One flag turns the engine on or off.

---

## 3. Data model (additive)

All new data lives in one object per session, `se.mem`, with a schema version.

```js
se.mem = {
  v: 1,                       // schema version of the memory engine
  seq: 0,                     // id counter
  events: [                   // the ledger, in story order
    { id:"e12", t:34,          // turn index of the AI reply that produced it
      ch:3,                    // chapter index at the time
      when:"Return day 2, night",  // in-story time label, if known
      where:"Veillard east wing",
      who:["Lenox","Lumia"],   // participants
      wit:["Riette"],          // witnesses who are not participants
      kind:"reveal",           // action|reveal|promise|betrayal|injury|death|item|travel|bond|secret|decision
      imp:4,                   // importance 1–5
      text:"Lumia admits privately that she forged the healer's report.",
      open:true,               // an unresolved thread (promise, secret, threat)
      src:"meta"               // meta|digest|player|import
    }
  ],
  facts: [                    // lasting truths, each with provenance
    { id:"f7", text:"Lenox lost his memories of his wife in the northern war.",
      from:["e2"], since:2, until:null, sticky:false, conf:0.9 }
  ],
  secrets: [                  // information with restricted knowledge
    { id:"s3", text:"The healer's report was forged by Lumia.", from:["e12"],
      knownBy:["Lumia","Riette"], suspects:["Julian"] }
  ],
  chars: {                    // per-character memory, separate from se.cast (UI data)
    "Lenox": {
      kernel:{ core:"guarded, dutiful, proud; tender only in private",
               voice:"short declaratives; formal address; never apologizes first",
               values:"duty to the duchy; loyalty to those who saved him",
               lines:["Expect nothing more from me."] },   // pinned and rarely changed
      state:{ mood:"cold", where:"study", status:"alive", goal:"get his memories back" },
      knows:["f7","s1"],      // fact and secret ids this character knows
      beliefs:[{text:"Lumia saved my life", true:false, from:["e1"]}],
      mem:["e3","e12"]        // personal memory: events they took part in or witnessed
    }
  },
  scenes: [ { id:"c9", t0:30, t1:36, text:"…80-word scene capsule…", ev:["e11","e12"] } ],
  checks: [ { id:"k4", t:36, kind:"dead-speaks", text:"Marek speaks but died in e9", ok:null } ],
  stats:{ cacheHit:0, inTok:0, cachedTok:0 }  // for tuning the budgeter
};
// Per turn (on the AI turn object):
ai.mx = { add:["e12","f7"], set:{ "chars.Lenox.state.mood":["warm","cold"] }, learn:[["Riette","s3"]] };
```

**Relationship features (owned by the ChatGPT workstream).** The engine does **not** write `se.cast[n].b` or any relationship UI data. It records **relationship events** (`kind:"bond"`, with `who:[A,B]`) and offers a read-only function, `memRelHistory(se, A, B, n)`. The relationship system can call it to show or justify meter changes. The engine also reads bond values to decide how much relationship history to include in a prompt.

---

## 4. Components

### 4.1 Event extraction (every turn, cheap)
Add META lines, which are parsed in `applyMeta()`:
```
EVENTS: up to 3 important things that happened in this reply, each as
        importance 1-5 | kind | who, who | where | one-sentence description | witnesses
        separated by ;  — or none
LEARNED: who found out something important in this reply, as Name: what they learned
         (how), separated by ;  — or none
SCENE: where | who is present | time of day or story time
```
- At Save money level 2 (Maximum), request only `EVENTS` and only with importance 3 or higher.
- **Fallback.** If a reply has no META, `digest()` extracts events for the chapter in its existing review call, marked `src:"digest"`.
- **De-duplication.** An event whose who/kind/text overlaps an existing one within the same 6 turns (token overlap ≥ 0.7) is merged, not added.

### 4.2 Character memory and personality consistency
- **Kernel.** For each major character, a `kernel` (core traits, voice, values, 1–3 signature lines) is built **once**. Sources are `st.cast0` (OOC imports), canon notes and the first `CAST` profile, or a single cheap model call. **CAST updates can't change the kernel.** They update only `state` (mood, where, attitude). The kernel changes only when the player edits it or a chapter review proposes a change *and* links it to an event (character growth).
- **Voice samples.** Pick the best 1–3 lines a character actually said: short, distinctive, high-importance scenes. Store them in `kernel.lines` so the model has real examples of how the character speaks.
- **Prompt.** Kernels of **characters present in the scene** (from `SCENE`, the action text and the last reply) go in the stable part of the prompt. Absent characters get a one-line kernel, or nothing.

### 4.3 Canon and world continuity
- **Fact provenance.** `digest()` no longer rewrites the whole fact list. It returns **operations** instead:
  ```
  FACT+: new lasting fact (cite events e12, e14)
  FACT~: f7 → corrected text (why)
  FACT-: f3 (no longer true because e20)
  ```
  This keeps facts from silently disappearing, gives each fact `from` / `since` / `until`, and makes branching exact.
- **Sticky facts.** World rules, power-system limits, deaths and canon facts from `st.entries` with `a:true` are marked `sticky`. They are always included and can never be removed by the model, only by the player.
- **Story canon versus session canon.** `st.entries` remains the static canon of the world. `se.mem.facts` is what has become true *in this playthrough*. Where they disagree, session facts win, and the prompt says so (for example, "in this timeline, Glenn survived").

### 4.4 NPC knowledge tracking
- Each `secret` and important `fact` has `knownBy`.
- Knowledge updates come from the meta lines: participants and witnesses of an event learn it, and `LEARNED:` lines add more.
- **Knowledge-boundary block.** For each NPC present in the scene, the prompt lists up to 3 secrets that NPC **does not** know but that relate to the scene:
  ```
  Knowledge limits (characters must not act on what they don't know):
  - Lenox does NOT know: the healer's report was forged.
  - Lumia does NOT know: Riette saw her burn the letter.
  ```
  Listing what a character must *not* know is more reliable than listing everything they do know, and it's cheaper.
- **The player character** knows what they witnessed. The narrator may still show dramatic irony in narration, but never through NPC dialogue or actions.
- **Beliefs** let NPCs hold false beliefs (for example, "Lumia saved my life", marked false). This drives drama without contradicting the canon.

### 4.5 Hierarchical summaries and important-event memory
The current flow is turns → `temp`, chapters → `sum`, then folded into `saga`. Proposed:
1. **Scene capsules.** When `summarize()` condenses old turns, it writes one 60–90-word capsule per scene (scenes split at `SCENE` changes), linked to that scene's events. These replace the free-form `temp`. `temp` stays as a compatibility mirror.
2. **Chapter summary.** As today, plus the fact operations above.
3. **Arc summaries.** `foldRec()` folds old chapter summaries into arc paragraphs. It **never** folds high-importance events (`imp ≥ 4`) or open threads; those stay in the ledger and stay retrievable.
4. **Important-event memory.** Events with `imp ≥ 4` or `open:true` are always candidates for retrieval (see 4.7), regardless of age.

### 4.6 Relationship memories (feeds the relationship system without changing it)
- Every `kind:"bond"` event (gift, betrayal, confession, rescue, insult) is stored with both names.
- `memRelHistory(se, A, B, n)` returns the n most important bond events between two characters. The relationship system can show these as reasons ("Trust +6: you defended her at the banquet").
- In the prompt, for **pairs present in the scene**, include the 2–3 most important shared memories plus the current bond value, read from `se.cast[n].b`. Example: *"Lenox and you: bond 38/100; key moments: he called you a stranger at the gates (e3); you tended his wound in silence (e15)."* This gives NPCs history-aware reactions instead of reacting only to a number.

### 4.7 Retrieval during generation
Candidates are events, scene capsules, facts and reference chunks. Each candidate's score is:
```
score = 3.0·entityOverlap(scene entities, item.who/wit)
      + 1.5·bm25(query terms, item.text)        // reuse refTerms() + IDF logic from refPick()
      + 1.2·imp/5
      + 1.0·open                                 // unresolved threads
      + 0.8·recencyDecay(Δturns, half-life 40)
      + 0.7·samePlace
      − 2.0·alreadyInRawHistory                  // don't resend what the model can already see
```
- **Query** = action, the last reply's last 1,500 characters, scene entities, the current goal and open quests.
- **Diversity:** at most 2 items from the same chapter, unless their importance is 5.
- **Output** goes into a "Relevant past events" block, each line tagged with time and chapter so the model can place it: `[Ch 3 · Return day 2] Lumia admits she forged the report.`
- **Embeddings** are optional later. The scorer has a slot for `cosine(embedding)`. Keyword scoring with entity overlap is strong enough to start and costs nothing.

### 4.8 Context budget and prompt caching (cost)
A new `assemblePrompt(se, st, hist, action)` replaces the body of `buildMsgs()`. It keeps the same signature and returns the same `messages` array shape.

**Section order, from most stable to least stable:**
```
[system]  1. Narrator rules, mode prompt, formats, safety          ← identical every turn
          2. World: title, canon line, setting, style, lore, sticky facts
          3. Story canon notes with a:true
          4. META spec (no turn numbers in here)                    ← end of the cached prefix
[history] 5. Raw recent turns (rawFrom)                             ← grows, so the prefix still matches
[user]    6. Dynamic "context for this turn" block:
             character kernels and states for those present · knowledge limits ·
             relevant past events · relationship memories · scene state ·
             keyword-matched canon notes · reference passages · wiki notes · research ·
             story record (current facts) · stats, counters, status, quests ·
             "This is turn N" and endings
          7. The player's action and the instruction "(Reply as instructed…)"
```
- Steps 1–4 change only when settings or the story change, so they're cached. Turns at the start of step 5 stay the same until `rawFrom` drops them.
- **Provider notes.** DeepSeek (OpenCode and OpenRouter), OpenAI and Gemini 2.5+ cache matching prefixes automatically. Anthropic models on OpenRouter need explicit `cache_control` breakpoints on blocks 4 and 5. Add these in `ask()` only when `model` starts with `anthropic/`.
- **Expected savings.** On OpenCode's DeepSeek pricing, cached input is about 2% of the normal input price ($0.006 versus $0.30 per million tokens). With a 6–8k stable prefix, a typical 14k-token turn could cost roughly **35–50% less**. Verify this with `usage.prompt_tokens_details.cached_tokens`, which the app already reads in `ocCost()`. Log it to `se.mem.stats` and show a cache-hit percentage in Save money.
- **Budgeter.** Each dynamic section has a priority and a share. Unused budget flows to the next section. Sizes are by Save money level:

| Section | Full | Recommended | Max saving |
|---|---|---|---|
| Kernels (present) | 1800 | 1200 | 700 |
| Knowledge limits | 600 | 450 | 300 |
| Past events | 2400 | 1500 | 800 |
| Relationship memories | 700 | 450 | 250 |
| Facts (non-sticky, ranked) | 3000 | 2000 | 1200 |
| Canon notes (matched) | 4000 | 2500 | 1200 |
| Reference passages + wiki | 6000 | 3600 | 2000 |

  These are character counts, matching the existing conventions. Raw history keeps today's `2*BUD()` rule, but **subtracts** turns already covered by retrieved capsules.
- **Lean history option.** At "Max saving", keep only the last 2 turns raw and rely on capsules plus retrieval. This cuts tokens substantially. Leave it off by default.

### 4.9 Branching timelines
With every item anchored to a turn (`t`), and facts carrying `since`/`until`, branching becomes exact:
```
branchMem(mem, cut):
  events  = events.filter(e => e.t < cut)
  facts   = facts.filter(f => f.since < cut).map(f => f.until >= cut ? {...f, until:null} : f)
  secrets = recompute knownBy from events < cut and LEARNED deltas < cut
  chars   = replay per-turn deltas (ai.mx) up to cut, starting from the kernels
  scenes  = scenes.filter(s => s.t1 < cut)
```
- Replaces the lossy logic in `branchAt()`, which today drops `mems`, `temp` and `facts` when the cut is before the last checkpoint.
- **Branch tree.** `se.root`, `se.parent` and `se.cut` already exist in part (`root`, `parent`). Add `cut`. Storage is a full copy for v1, which is simple and robust. A shared-prefix version is a possible later optimization.
- **Regenerate, rewind and delete** use the same mechanism. Before replacing or removing an AI turn, apply the inverse of its `ai.mx`. Kept versions (`ai.vs`) store their own `mx`, so swapping versions with `verSw()` applies the right memory too.

### 4.10 Contradiction and continuity detection
Three tiers, from cheapest to most expensive:
1. **Instant rule checks** after each reply, no model call, in `memLint(se, st, reply)`:
   - a character in `se.dead` or with `state.status="dead"` speaks (in `Name | "…"` lines, or a name next to a speech verb);
   - an NPC states or acts on a secret they don't know (keyword match between dialogue and the secret's text);
   - a counter or stat moves against the rules, or by more than the allowed step;
   - a sticky fact's key words are negated near the same names (simple negation patterns);
   - the location jumps without a time skip (from `SCENE`).

   Hits are saved to `se.mem.checks` and shown in the existing continuity-note style.
2. **Per-chapter review**, which already exists in `digest()`, now gets structured output: `CONFLICT: f7 vs turn 36 — description`. These can be linked to facts.
3. **On-demand deep check** using a `/check` command, or automatically after a tier-1 hit. One cheap-model call compares the last reply against the relevant facts and knowledge limits, and suggests a fix. The fix offers "Regenerate with this correction" (reusing the `/impersonation` style of `se.imp` correction) or "Accept and record as new canon" (adds a `FACT~`).

### 4.11 Reliable storage and recovery
- **Per-session storage.** Move `se.turns` and `se.mem` into IndexedDB as `sess:<id>`. `DB.sessions[]` then keeps only a small index (id, title, updated, counts). This avoids the localStorage quota, which long stories with pictures and thumbnails will hit. `save()` writes the index to localStorage and the session body to IDB.
- **Snapshots.** Keep a ring of the last 3 versions of each session body (`snap:<id>:<n>`), written at most every 10 minutes, plus one before every migration, branch or bulk edit. Add a "Restore an earlier copy" action. The UI wording for it is up to the UI owner.
- **Integrity.** On load, check that events are sorted by `t`, every id referenced by a fact exists, and every `ai.mx` matches. If a check fails, use the last good snapshot and keep the broken copy as `broken:<id>`.
- **Full backup.** Add a backup option that includes IDB content (reference texts, books, pictures, session bodies) as a ZIP. `zipStore()` already exists. **Exclude** `key`, `ocKey` and `syncPass`. This also fixes the current backup including the sync passphrase.
- **Sync.** `syncMerge()` merges by `updated`. With per-session bodies, sync each session body separately, to stay under KV value limits and to merge more precisely.

---

## 5. Existing functions that change

| Function | Change | Risk |
|---|---|---|
| `blankDB()` / `norm()` | Add `DB.schema`, `DB.memv2` flag; run migration (§6) | Low |
| `save()` | Split into index plus per-session IDB bodies (phase 7 only) | **Medium**: test heavily |
| `buildMsgs()` | Becomes a wrapper around `assemblePrompt()`; same return shape | Medium |
| `applyMeta()` | Parse `EVENTS`, `LEARNED`, `SCENE`; write deltas into `ai.mx`; protect kernels | Low |
| `send()` | Create `ai.mx`; run `memLint()` after a reply; log cache usage | Low |
| `regen()`, `verSw()` | Undo or redo `ai.mx` for the replaced or selected version | Medium |
| `turnMenu()` delete / rewind | Undo the deltas of removed turns | Medium |
| `summarize()` | Write scene capsules; keep `temp` as a mirror | Low |
| `digest()` | Fact operations instead of rewriting the list; event fallback; structured conflicts | Medium |
| `foldRec()` | Never fold `imp ≥ 4` or open events | Low |
| `recText()` | Reads facts from `se.mem.facts` when the engine is on (string fallback) | Low |
| `loreFor()`, `refPick()` | Move their output to the dynamic block; share the scoring helpers | Low |
| `branchAt()` | Use `branchMem()`; set `cut` | Low |
| `syncMerge()` / backup in `vSettings()` | Per-session merge; full backup; drop `syncPass` | Medium |
| `ask()` | `cache_control` for `anthropic/*`; return `cached_tokens` | Low |
| `tokEst()` / `saverSheet()` | Account for cached tokens (shows a cache-hit %) | Low |

**New functions:** `memInit`, `memMigrate`, `memApplyDelta`, `memUndoDelta`, `memExtract` (META parsing), `memScore`, `memRetrieve`, `assemblePrompt`, `kernelBuild`, `knowledgeLimits`, `memRelHistory`, `memLint`, `branchMem`, `memSnapshot`, `memRestore`, `memIntegrity`, `fullBackup`.

**Untouched:** all view functions (`vHome`, `vStory`, `vChat` layout), `castSheet` and bond UI, relationship features, themes, formats, read aloud, library, importers, the world builder and the simulator setup.

---

## 6. Migration without losing saved stories

1. **Flag first.** Add `DB.memv2 = false` by default. The new code runs only when it's true, or per session as `se.memv2`. Old code paths stay intact.
2. **Snapshot before migrating.** Write `snap:<id>:pre-mem` for every session before touching it.
3. **Lossless conversion.** `memMigrate(se)` builds `se.mem` from what exists:
   - `se.facts[]` becomes `mem.facts`, with `from:[]`, `since` set to the chapter of their first appearance (or 0), and `sticky:false`.
   - Each `chaps[k].sum` becomes one `digest` event per chapter (`imp:3`), and each `chaps[k].conf` becomes `checks`.
   - `se.mems[]` become events with `kind:"memory"`, anchored at `t = se.upto`.
   - `se.cast` becomes `mem.chars[n].state` and the starting kernel (traits, looks); `st.cast0` provides kernels and quotes for imported stories.
   - `se.dead` sets `chars[n].state.status = "dead"` and adds a sticky fact.
   - `se.quests` (open ones) become events with `open:true`.
4. **Keep old fields.** `se.facts`, `se.temp`, `se.mems` and `chaps[].sum` keep being written as mirrors during the transition, so turning the flag off returns exactly the old behavior. Remove the mirrors only after a full release cycle.
5. **Lazy, per session.** Migrate a session when it is first opened with the flag on, not all sessions at startup. A failure falls back to the old path and logs to `se.mem.migrateErr`.
6. **Schema version.** `se.mem.v` lets future changes migrate step by step (`v1 → v2`).

---

## 7. Implementation plan (phases)

Each phase ships on its own, behind the flag, with Playwright tests in `tests/` that follow the existing pattern: mock `openrouter.ai`, drive the UI, and print `ERRORS: []`.

| Phase | Deliverable | Functions | Tests |
|---|---|---|---|
| **0. Scaffolding** | Flag, schema, `memInit` / `memMigrate`, snapshots before migration | `norm`, new mem* helpers | Old saved data loads unchanged; migration of a real long session is lossless (diff the old fields) |
| **1. Event ledger and deltas** | META `EVENTS`/`LEARNED`/`SCENE`; `ai.mx`; undo on regenerate, rewind and delete | `applyMeta`, `send`, `regen`, `verSw`, `turnMenu` | Regenerate 3× then pick version 1, and the ledger matches version 1; rewind removes exactly those events |
| **2. Prompt assembly and caching** | `assemblePrompt` with stable prefix and dynamic block; `cache_control`; cache-hit logging | `buildMsgs`, `ask`, `tokEst` | Byte-identical prefix across two turns; cached-token count read from mocked usage; prompt contains all old sections |
| **3. Retrieval** | `memScore` / `memRetrieve`; budgeter; "Relevant past events" block | new, plus `refPick` helpers | An important event from 200 turns ago is retrieved when its characters reappear; budget limits respected |
| **4. Characters and knowledge** | Kernels, voice lines, protected traits; `knowledgeLimits`; beliefs | `applyMeta`, new | A CAST update can't change a kernel; an NPC without knowledge appears in the "does NOT know" list |
| **5. Summaries and facts** | Scene capsules; fact operations in `digest`; fold protection | `summarize`, `digest`, `foldRec`, `recText` | Facts never disappear without a `FACT-`; `imp ≥ 4` events survive folding |
| **6. Continuity** | `memLint` tier 1; structured conflicts; `/check` with a fix action | `send`, `digest`, command handler | A dead character speaking is flagged; a secret leak is flagged |
| **7. Branching** | `branchMem`; exact branch at any turn | `branchAt` | Branching at turn 10 of a 300-turn story keeps exactly the events, facts and knowledge from before turn 10 |
| **8. Storage and recovery** | Per-session IDB bodies; snapshot ring; integrity check; full backup ZIP without secrets | `save`, load path, `vSettings` backup, `syncMerge` | Quota simulation; corrupted body is restored from a snapshot; backup has no `key`, `ocKey` or `syncPass` |

**Suggested order:** 0 → 1 → 2 (fastest cost win) → 3 → 4 → 5 → 6 → 7 → 8. Phase 8 can move earlier if any user's data nears the localStorage quota.

---

## 8. Interfaces for the other workstreams

These are read-only functions, so the UI and relationship work can use the engine without depending on how it works inside:
```js
memRelHistory(se, a, b, n=3)   // → [{id,text,when,imp,kind}] shared bond events, most important first
memCharView(se, name)          // → {kernel, state, knows:[text], beliefs:[text], recent:[events]}
memTimeline(se, filter)        // → events for a timeline or "story so far" view
memChecks(se)                  // → open continuity flags
memStats(se)                   // → {events, facts, cacheHitPct, lastSnapshotAt}
```
Write access stays inside the engine. The relationship system keeps owning `se.cast[n].b` and its UI.

---

## 9. Open questions for the owner
1. Should continuity flags only warn (as today), or also offer an automatic regenerate?
2. Should "Max saving" use the lean-history option (fewer raw turns, more capsules) by default?
3. Should the full backup be the default backup, or a separate button? It can be large with books and pictures.
4. When a player edits a reply by hand, should the engine re-extract its events? Proposal: yes, with one cheap call when the edit is saved.
