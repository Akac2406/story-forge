# Memory record and reconciliation contract (v91)

Owner: Claude (story intelligence). Consumers: ChatGPT's player-facing screens (memory status, retry,
Timeline and Memory Studio, backups). Version: contract 1, introduced in v91 (branch `v91-hybrid-memory`).
Changes to anything below need a note in this file and in `docs/DEV-MANIFEST.md`.

## 1. Where memory lives

| Location | Shape | Notes |
|---|---|---|
| `se.mem` | `{v:1, seq, events[], facts[], secrets[], chars{}, scenes[], scene, checks[], stats}` | Story memory for one playthrough. Schema `v:1`. Built and changed only through `SFMemory` (memory-engine.js). |
| `se.mem.events[]` | `{id, t, ch, tid, src, kind, imp, who[], wit[], where, when, text, open}` | `t` = turn index of the reply; `tid` = reply id; `src` = `"meta"` (from a reply), `"digest"`, `"import"`, `"legacy"`. |
| `se.mem.facts[]` | `{id, text, from[], since, until, sticky, conf}` | Knowledge items. Characters point at them via `chars[name].knows[]`. |
| `se.mem.scene` | `{where, who[], when}` | The current scene. |
| `se.memExtract` | `false` \| `"hybrid"` \| `true` | Memory notes mode per story: narrator only (default), hybrid, separate step. |
| `se.memPrompt` | boolean | Phase 2: the narrator is shown "who knows what". |
| `se.memDiag[]` | `{t, block, keys{EVENTS,LEARNED,SCENE}, issues[], rp?}` | Per-reply diagnostics. `rp` = the quick check's result: `{ok, ms, tok:[in,out], why, dropped[], src, conflicts[]}`. |

### Per reply (`ai` = an assistant turn)

| Field | Meaning |
|---|---|
| `ai.tid` | Stable reply id. |
| `ai.mt` | The narrator's own `[[META]]` block (as written). |
| `ai.rmt` | The quick check's block (never shown to the model). |
| `ai.mx` | The reversible memory delta this reply applied. Undo/apply it with `SFMemory.undo/apply`; never edit it. |
| `ai.msrc` | Hybrid only: `{events, learned, scene}`, each `"narrator"`, `"step"` or `"none"`. |
| `ai.vs[]` | Generated versions. Each keeps its own `mx`, `mt`, `rmt`, `msrc`, so switching versions swaps memory exactly. |

## 2. Reconciliation rules (hybrid)

`memReconcile(narrator, step)` is pure and returns `{rec, src, conflicts}`.

1. Events: the narrator's list wins whenever it has any entries. The step's events are used only when the narrator wrote none.
2. Knowledge (LEARNED): same rule as events.
3. Scene: the step's scene wins when it names a place (in trials it placed scenes and casts far more accurately); otherwise the narrator's.
4. Conflicts are never dropped silently. A different place, or a knowledge item only the step noticed, is listed in `rp.conflicts`
   and returned by `memStatus(se).conflicts`, for the player to review.
5. Nothing outside the reply's own delta is touched. Locked canon (Canon Bible `lock`), player-edited memory and other replies
   are never changed by the quick check. A re-check undoes that reply's previous delta first, so there are no duplicates.
6. Results that arrive after the reply changed (regenerated, edited, deleted, version switched) are discarded (`why: "stale"`).

## 3. Functions for the UI

| Function | Returns | Use |
|---|---|---|
| `memStatus(se)` | `{mode, pending, checked, ok, failed:[{t,why}], conflicts:[{t,items[]}], last:{t,ok,why,ms,src}}` | Memory status chip, "processing" spinner, failed list, conflict review. |
| `memRetry(se, t)` | Promise of `{ok, why?, ms, src?, conflicts?}` | "Retry" on one reply (turn index `t`). Queued behind any pending check; never duplicates. |
| `promptReport(se)`, `activeNotes(...)` | (v87) | Unchanged. |

`why` values: `"timeout"`, `"error"`, `"unreadable"`, `"stale"`, `"not a reply"`.

## 4. Backups

A backup must include, per session: `mem`, `memDiag`, `memExtract`, `memPrompt`, and per reply `tid, mt, rmt, mx, msrc, vs`.
`mx` must round-trip byte-for-byte, or version switching and branching will corrupt memory. Restores must check
`SFMemory.integrity(se.mem).ok` before accepting a session.
