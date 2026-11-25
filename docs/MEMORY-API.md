# Memory overhaul API (contract 2) — for Memory Studio, Timeline Explorer and backups

Status: implemented on `memory-overhaul` (site/memory-v2.js + adapter in index.html). Tests: tests/memory_v2_unit.mjs, tests/memory_v2_studio_browser.py.
Sample data for building screens: tests/fixtures/mem2-source.json (all nine layers). `SFMem2.build(fixture)` gives a ready view.

## Record (every layer)

```
{ id, layer, kind, text, who[], where, t, ch, tid, branch, src, conf, pin, lock, since, until, supersedes[], links[], deleted,
  edited?, history? }
```
- `layer`: permanent | working | episodic | semantic | character | relationship | temporal | world | universe (`SFMem2.LAYERS`, in display order).
- `src`: player | canon | narrator | step | digest | import | legacy. Trust order: `SFMem2.TRUST`, where the player is highest.
- `links`: `knows:<factId>`, `believes:<factId>` (character records), `wit:<name>` (witnesses), event ids (relationship records), aliases (canon).
- IDs from the existing store are preserved (event `e12`, fact `f3`, canon `entry-0`, note ids). Derived records use `char:<name>`, `rel:<A> | <B>`,
  `prog:<type>:<name>`, `dead:<name>`, `quest-<n>`, `sched-<n>`, `working-scene`, `era`, `clock`, `setup`, `player`.

## App functions (global, in index.html)

| Function | Returns | Notes |
|---|---|---|
| `memView(se)` | `{v:2, records[]}` | Built fresh from the story plus player overlays. Cheap; call on open or refresh. |
| `memQuery(se, q)` | `records[]` | `q = {layer (string or array), who, text, src, pinned, from, to, deleted, limit}`. Deterministic order: pinned, then layer order, then turn, then id. |
| `memEdit(se, id, patch)` | `true` | Patchable: text, who, where, kind, since, until, conf, links. Marks `src:'player'`. Locked permanent records ignore edits. |
| `memPin(se, id, on)` / `memLock(se, id, on)` | `true` | |
| `memDelete(se, id)` / `memRestore(se, id)` | `true` | Soft delete; locked permanent records can't be deleted. |
| `memAdd(se, record)` | `true` | Player-made memory; the id is generated if missing. |
| `memUndo(se)` | `true` | Undoes the last player operation. |
| `memStatus(se)` | `{mode, pending, checked, ok, failed[], conflicts[], last}` | For the status chip and failed list. |
| `memRetry(se, t)` | `Promise<{ok, why?, src?, conflicts?}>` | Re-checks one reply; queued; no duplicates. |
| `memConflicts(se)` | `[{id, t, items[], src}]` | Open conflicts only. |
| `memResolve(se, conflictId, choice)` | `true/false` | `choice`: free text, for example `keep-narrator`, `keep-step`, `edited`. |
| `SFMem2.knows(view, name)` | semantic records | A character's knowledge boundary. Universe records never count. |
| `SFMem2.stats(view)` | count per layer | |
| `SFMem2.integrity(view)` | `{ok, errors[]}` | Run before showing restored data. |

## Storage

- Player edits: `se.memEdits = {v:1, ops:[{op, id, at, patch|on|record}]}`. Separate from per-reply deltas, so regeneration and rollback can't erase them.
- Nothing in contract 2 writes to `se.mem`. Backups must include `se.memEdits` alongside the fields listed in MEMORY-CONTRACT.md section 4.

## Coming next (engine side, same API)

- Temporal fields on semantic records: `storyFrom`, `storyTo`, `seenAt`, `expiredAt`, `source` (Graphiti-style; see OSS-EVALUATION.md). `memQuery` gains `asOf` (turn).
- Fused retrieval for prompts (BM25 + entity + temporal + importance + pin).
- NPC goals and schedules on character records, advanced by story time.
