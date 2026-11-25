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
| `memQuery(se, q)` | `records[]` | `q = {layer (string or array), who, text, src, pinned, from, to, asOf, deleted: false|true|'only', limit}`. `asOf` = turn: hides later memories and facts not yet true. Deterministic order: pinned, then layer order, then turn, then id. |
| `memEdit(se, id, patch)` | `{ok, applied, reason, record}` | Patchable: text, who, where, kind, since, until, conf, links. Marks `src:'player'`. Locked permanent records ignore edits. |
| `memPin(se, id, on)` / `memLock(se, id, on)` | `{ok, applied, reason, record}` | |
| `memDelete(se, id)` / `memRestore(se, id)` | `{ok, applied, reason, record}` | Soft delete; locked permanent records can't be deleted. |
| `memAdd(se, record)` | `{ok, applied, reason, record}` | Player-made memory; the id is generated if missing. |
| `memUndo(se)` | `{ok, applied, reason, record}` | Undoes the last player operation. |
| `memStatus(se)` | `{mode, pending, checked, ok, failed[], conflicts[], last}` | For the status chip and failed list. |
| `memRetry(se, t)` | `Promise<{ok, why?, src?, conflicts?}>` | Re-checks one reply; queued; no duplicates. |
| `memHistory(se, id)` | `[{op, at, patch, on}]` | Full player edit history for one record, oldest first. |
| `memConflicts(se)` | `[{id, t, items[], src}]` | Open conflicts only. |
| `memResolve(se, conflictId, choice, {edit:{id, patch}}?)` | `{ok, reason, edit}` | Marks the conflict resolved. Memory changes only if you pass `edit` (applied through memEdit, undoable). |
| `SFMem2.knows(view, name)` | semantic records | A character's knowledge boundary. Universe records never count. |
| `SFMem2.stats(view)` | count per layer | |
| `SFMem2.integrity(view)` | `{ok, errors[]}` | Run before showing restored data. |

Mutations never throw. `applied:false` means nothing was stored; `reason` is `locked`, `unchanged`, `not found` or `nothing to undo`.

## Storage

- Player edits: `se.memEdits = {v:1, ops:[{op, id, at, patch|on|record}]}`. Separate from per-reply deltas, so regeneration and rollback can't erase them.
- Nothing in contract 2 writes to `se.mem`. Backups must include `se.memEdits` alongside the fields listed in MEMORY-CONTRACT.md section 4.

## Engine functions added (pure, `SFMem2`)

| Function | Returns | Notes |
|---|---|---|
| `supersede(edits, oldId, newId, t)` | edits | The newer fact replaces the old from turn `t`; the old one stays (history) with `until`, `expiredAt`, `expiredBy`. |
| `query(view, {current:true})` | records | Only facts still true (no `until`). |
| `retrieve(view, {text, present[], where, t, layers?, limit?, max?})` | `[{record, score, why}]` | Fused recall; skips deleted and not-yet/no-longer-true; deterministic; within `max` characters. |
| `render(hits)` | text | Grouped by layer with `[turn N]` tags (what the narrator sees). |
| `contradictions(view)` | `[{kind, ids[], text}]` | `dead-acts`, `fact`, `canon`. Rule-based, no AI request. Show in Conflict Center next to `memConflicts`. |
| `npcState(view, day)` | `[{name, goals[], where, doing, since}]` | NPC schedule position for a story day. Source: `src.npcs = {Name: {goals[], schedule:[{day, where, doing}]}}`. |

Semantic records also carry `storyFrom`, `storyTo`, `seenAt`, `expiredAt`.
Per-story switch `se.memRecall` (Story memory sheet): adds recalled memories to each prompt. Off by default.

## Coming next (engine side, same API)

- Memory operating modes (Light / Balanced / Maximum) grouping the switches.
- Real-model A/B of recall on long scenarios.
- Storage for NPC plans (`se.npcs`) editable in the UI.
