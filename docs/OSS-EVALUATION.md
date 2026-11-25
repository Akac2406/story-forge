# Open-source evaluation for the memory overhaul (2026-11-24)

Constraints (Anna): keep the browser-only PWA and OpenCode/DeepSeek; no extra paid services; no new backend unless agreed;
no wholesale replacement of the memory engine without ChatGPT; check license, security, performance, browser fit, hosting, OpenCode fit.

## Summary

| Project | License | What it needs to run | Fit for Story Forge | Decision |
|---|---|---|---|---|
| Graphiti (Zep) | Apache-2.0 | Python, a graph database (Neo4j and others), an LLM plus an embeddings API | Server-side only; can't run in the PWA | **Inspiration**: temporal fact model |
| Mem0 | Apache-2.0 | Python/TS SDK, a vector store, an embeddings API (or their paid cloud) | Needs embeddings and a store we don't have; the cloud is a paid service | **Inspiration**: extraction and retrieval design |
| Letta (MemGPT) | Apache-2.0 (to re-confirm before any code reuse) | Python server plus database | Server agent framework | **Inspiration**: always-in-context memory blocks with size limits |
| AI Town (a16z) | MIT | Convex backend, LLM, embeddings | Backend-bound; simulation runs continuously | **Inspiration**: NPC identity, plans, schedules; adapt to story time |
| SillyTavern | AGPL-3.0 | Node server | Copyleft: copied code would force AGPL on Story Forge | **Inspiration only**, no code copying |
| Dexie.js | Apache-2.0 | Browser library (IndexedDB) | Browser-native, offline-friendly | **Candidate for direct use later** (storage), only if size or speed needs it |
| InkJS | MIT (to re-confirm) | Browser library | Browser-native | **Candidate** for future gameplay prototypes, not part of the memory overhaul |

No project can be dropped in directly without adding a backend or a paid embeddings service. The plan is to rebuild the
useful ideas in small pure functions inside `memory-v2.js` and `canon-engine.js`, credited in comments where an idea is borrowed.

## What we take from each

### Graphiti: temporal memory
- **Bi-temporal facts.** Each fact edge has when it was true (`valid_at`, `invalid_at`) and when the system learned or expired it (`created_at`, `expired_at`).
- **Invalidate, never delete.** A contradicting fact closes the old one's validity instead of deleting it, so history stays queryable.
- **Our version:** semantic records get `storyFrom`/`storyTo` (story day and turn) plus `seenAt`/`expiredAt` (turn recorded and turn superseded), and `source` (chapter and reply).
  Retrieval asks for "current" (open `storyTo`) or "as of turn N" (history). Contradictions set `storyTo` and link `supersedes`.

### Mem0: extraction and retrieval
- **Multi-signal retrieval.** Keyword (BM25), entity match and semantic similarity are scored in parallel and fused, with time-aware ranking.
- **Simpler extraction.** In April 2026 the open-source pipeline moved to single-pass, add-only extraction: memories accumulate and nothing is overwritten. Duplicates are skipped by hash.
- **Our version:** fused score = BM25 over record text and aliases + entity overlap (present characters, place) + temporal fit (current state, or near the turn asked about) + importance + pin.
  No embeddings in phase 1: OpenCode Go has no confirmed embeddings endpoint, and we won't add a paid one. The scorer has a slot for an optional semantic signal later.
  Extraction stays add-only with hash dedupe; corrections come from the player or from contradiction handling.

### Letta: memory blocks
- **Core memory blocks.** Always-visible, size-limited blocks in context (persona, user, working state), plus searchable archival memory.
- **Our version:** this is our Permanent and Working layers with hard character budgets per block (already in v87 `assemble`).
  No self-editing agent memory; the narrator doesn't get write tools.

### AI Town: NPC behaviour
- **Generative agents.** Each agent has an identity, a plan and a memory stream, and reflects periodically; the simulation runs on a backend continuously.
- **Our version:** NPC records get `goals[]`, `schedule[]` and `agenda`, which advance **only when story time advances** (world days or time skips).
  Updates are deterministic: no AI request per NPC per tick. At most one batched "off-screen update" request when a large time skip happens (Maximum mode only).
  This uses the existing world schedule (`se.worldSchedule`) and Living Worlds plans.

### SillyTavern: lorebooks (inspiration only, AGPL)
- **World Info.** Keyword-activated lore entries with scan depth, recursion, priority and insertion order; a Data Bank for retrieval-augmented generation.
- **Our version:** this already exists in our own code (Canon Bible keyword retrieval with aliases and locked entries, v87).
  We may add recursion, where an activated entry's keywords can activate others with a depth limit, written from scratch.

### Dexie.js: storage
- Apache-2.0 IndexedDB wrapper with dependable transactions and error handling.
- **Our version:** not needed for the overhaul itself. If memory stores grow past what the current localStorage/IndexedDB split handles,
  a Dexie-backed store is the preferred upgrade (local file, no CDN, versioned schema, migration-tested). That would be a separate decision with ChatGPT.

## Security and hosting notes
- Nothing evaluated is loaded from a CDN at runtime. Any future library is vendored into `site/`, pinned and listed in this file.
- No new servers, keys or paid services. OpenCode stays the only model provider.
- AGPL code is never copied. Apache-2.0 and MIT code may be vendored with license and notice files if we ever do.
