# Story Forge memory overhaul — architecture proposal (draft 1, 2026-11-24)

Author: Claude. For review by ChatGPT, then implementation. Branch: `memory-overhaul`.
Test address: https://deploy-preview-7--celebrated-brigadeiros-580c41.netlify.app (draft PR #7; production untouched).
Goal: one complete memory overhaul, one coordinated testing campaign, one stable release. Planning target 2026-11-30, contingency 2026-12-04.

## 1. What exists today (audit of live v90 + branch)

| Existing system | Where | Reuse |
|---|---|---|
| Event ledger with reversible per-reply deltas (`mx`), version swap, branch trimming, integrity check | memory-engine.js (`SFMemory`) | Core of Episodic memory. Keep the delta model: it is what makes regenerate, rollback and branches safe. |
| Facts, secrets, per-character `knows[]`, character kernel/state | memory-engine.js | Semantic and Character memory. |
| Scene tracking (`mem.scene`) | memory-engine.js | Working memory. |
| Canon Bible (locked entries, priorities, aliases, timeline markers), User Notes (must/should/style, scopes), canon modes, divergences, protected prompt block with size caps | canon-engine.js (`SFCanon`), v87–v88 UI | Permanent memory and instruction enforcement. Already protected from truncation. |
| Phase 2 knowledge view (who knows / doesn't know / believes) | `SFCanon.knowledge` | Character knowledge boundaries in the prompt. |
| Hybrid extraction, reconciliation, provenance, conflicts, `memStatus`/`memRetry` | index.html (v91 branch) | Intelligent hybrid extraction. |
| Chapter digests and recaps (`se.chaps`, digest) | index.html | Compression tier for long stories. |
| Deadlines, quests, inventory, deaths (`se.dead`), world days, Review card | index.html | World and Temporal memory (state + consequences). |
| Era settings, story setup, style samples | index.html, canon-engine.js | Temporal (era) and Permanent memory. |
| World Simulator export/import, relationship map UI, cast portraits | index.html, relationship-map-v52.js | World / Universe memory and Relationship view. |
| Trial page with scripted scenarios, real-model runs, Go usage estimate (`ocPct`) | memtrial.html/js | Testing campaign harness (extend for long runs and A/B). |

Conclusion: no rewrite. The overhaul adds a unified schema over these parts, a retrieval and budgeting layer, and validation.

## 2. The nine layers as one store

One per-session store `se.mem` (schema v2) plus one shared store per universe. Every record shares one header:

```
{ id, layer, kind, text, who[], where, t (turn), ch (chapter), tid (reply), branch, src: narrator|step|player|canon|digest|import,
  conf (0-1), pin (bool), lock (bool), since, until, supersedes[], links[] }
```

| Layer | Holds | Built from | Lifetime |
|---|---|---|---|
| 1. Permanent | Locked canon, User Notes, story setup, player character, style rules | Canon Bible, notes, setup | Never compressed or dropped; player-only edits |
| 2. Working | Current scene, who is present, open threads, last few beats | Scene tracking + last replies | Replaced every reply |
| 3. Episodic | Events with importance, witnesses, consequences | Event ledger (`mx` deltas) | Kept; old low-importance events fold into chapter digests |
| 4. Semantic | Facts about the world and people, with validity ranges | Facts, LEARNED, digests | Kept; superseded facts linked, not deleted |
| 5. Character | Per character: kernel (personality, voice, values), state (mood, place, status), knows / believes / doesn't know | chars{}, knowledge view | Kept; personality changes need evidence events |
| 6. Relationship | Pairwise bond scores and history (trust, affection, rivalry), with the events that moved them | bond events, relationship map | Kept |
| 7. Temporal | Story clock (world days, chapter), era constraints, deadlines, timeline markers, branch points | worldDays, deadlines, era, markers | Kept; drives "can this happen yet" checks |
| 8. World | Places, factions, items, inventory, deaths, consequences that persist | inventory, deaths, quests, World Simulator | Kept |
| 9. Universe | Canon and facts shared across stories in one universe (characters, places, history) | World export/import, promoted records | Shared store, versioned; story-local divergences stay local |

Branch isolation: every record carries `branch`; a branch sees its ancestors' records up to the branch point (already true for `mx` deltas; extend to all layers).

## 3. Write path (after every reply)

1. Narrator reply with its own memory lines (unchanged prompt contract).
2. Local validation: missing keys, malformed lines, dead characters acting, era violations, knowledge leaks (who said what they can't know).
3. Hybrid quick check (per mode): fills scene, cast and gaps; reconciles under the rules in MEMORY-CONTRACT.md (narrator wins events/knowledge; step wins scene; conflicts flagged).
4. Layer routing: events → Episodic; LEARNED → Semantic + Character.knows; bond/relationship events → Relationship; time/deadline/item/death → Temporal/World.
5. Duplicate prevention (same reply re-check undoes its delta first; cross-reply near-duplicates merged with `supersedes`).
6. Contradiction detection against Permanent and Semantic layers → divergence record (existing v87 format) for the player to accept or fix.

## 4. Read path (prompt assembly)

Budgeted retrieval, in this priority order (already partly in `SFCanon.assemble`):

1. Permanent (protected, never trimmed; hard stop if over its cap, as in v87).
2. Working memory.
3. Character cards for characters present (kernel + state + knowledge boundary).
4. Relationships among present characters.
5. Retrieved Episodic and Semantic records: scored by keyword/alias match to the current scene and player action, importance, recency, pin, open threads.
6. Temporal and World constraints relevant to the scene (era rules, deadlines due, items held, who is dead).
7. Chapter digests for the long past.

Budgets scale with the existing saver setting (Full / Recommended / Lean). Compression: digests replace raw events beyond a window; character cards are summarised; nothing in layer 1 is compressed.

## 5. Operating modes (per story)

| Mode | Extraction | Retrieval | Cost |
|---|---|---|---|
| Light | Narrator only | Working + Permanent + small retrieval | No extra requests |
| Balanced (default after testing) | Hybrid | Full retrieval, knowledge boundaries | +1 small request per reply |
| Maximum | Hybrid + continuity review | Full + validation feedback | +2 small requests per reply |

## 6. Shared interfaces (to agree before dependent work)

1. Record schema v2 (section 2) and migration v1 → v2 (lossless, reversible, integrity-checked).
2. `SFMem2` engine API (pure functions): `route(parsed)`, `retrieve(se, ctx, budget)`, `reconcile`, `validate`, `branchView(se, branch)`, `compress(se)`, `stats(se)`.
3. Studio API (for ChatGPT): `memQuery(se, {layer, who, text, from, to, branch})`, `memEdit(se, id, patch)` (player edits become `src:'player'`, highest trust), `memPin(se, id, on)`, `memLock`, `memDelete` (soft, undoable), `memStatus`, `memRetry`, `memConflicts(se)`, `memResolve(se, conflictId, choice)`.
4. Backup manifest: schema versions, session list, per-session `mem` + diagnostics + reply fields, universe store, checksum; restore validates integrity before accepting.
5. Universe store: `DB.universes[id] = {v, name, records[], stories[]}`; promote/demote record between story and universe.

## 7. Assignments and workload

| Workstream | Lead | Estimate |
|---|---|---|
| Schema v2, migration, routing, branch views | Claude | 1.5 days |
| Retrieval and budgeting, compression, prompt assembly | Claude | 1.5 days |
| Validation: contradictions, knowledge boundaries, era/timeline, personality drift | Claude | 1 day |
| Relationship and World/Temporal state engines | Claude (engine) + ChatGPT (views) | 1 day |
| Universe store and promotion | Shared | 0.5 day |
| Memory Studio: search, edit, pin, lock, inspect, conflicts review | ChatGPT | 2 days |
| Timeline Explorer with branch view | ChatGPT | 1 day |
| Backups, restore preview, migration safety UI | ChatGPT | 1 day |
| Operating mode settings, status/retry UI | ChatGPT | 0.5 day |
| Simulated long-run harness (30/100/250/500/1,000 turns), A/B old vs new engine | Claude | 1 day |
| Real-model campaign, fixes, reruns | Both | ongoing |

Parallel from day 1: ChatGPT builds Studio/Timeline/backup screens against the Studio API with stub data while Claude builds the engine behind it.

## 8. Testing campaign

- Simulated first: per-component unit tests; full-system runs at 30, 100, 250, 500 and 1,000 turns with scripted replies (memory size, prompt size, speed, integrity, branch isolation, regenerate safety, migration round-trip).
- Real-model (DeepSeek via OpenCode Go): A/B old vs new engine on Cedar Ridge, Glass Orchard and new long scenarios (100–250 turns), scoring notes adherence, canon contradictions, knowledge leaks, personality and relationship consistency, era consistency, retention of early facts, latency and usage.
- Usage: ledger in `docs/USAGE-LEDGER.md`; stop real-model testing at 45% monthly total.

## 9. Agreed requirements from ChatGPT's review (2026-11-24)

1. Regeneration safety: player corrections (`src:'player'`) survive regenerating or rolling back an earlier reply; they are stored outside per-reply deltas and re-applied on top.
2. Knowledge isolation: universe facts are world truth, not character knowledge. No NPC "knows" a universe fact unless a record says so.
3. Compression: summaries replace originals only in prompts; originals stay in the store and visible in Memory Studio.
4. Existing stories: no new extra AI requests are switched on automatically. Existing stories keep their current mode until the player changes it.
5. Hybrid: the step fills individual missing events only after deduplication and accuracy are tested; until then it fills only when the narrator wrote none.
6. Backups exclude credentials; restores are atomic and integrity-checked.

## 10. Blockers and limits (honest)

- Real-model runs use Anna's key, which only exists in her browser. They run on the test address after she enters her key there once, and they need her computer awake with Chrome open while they run.
- My workspace cannot keep work running after a reply ends. Unattended work means scheduled sessions (each starts fresh from this manifest), and real-model runs still need her computer on.
- Usage is measured by the app's estimate plus readings from the OpenCode dashboard. If they disagree badly, real-model testing pauses.
