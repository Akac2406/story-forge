# Story Forge development manifest

The single place for "what is live, what is in progress, who owns what". Update it in every release commit.

## Release-number rule

- Only the integration branch that publishes to `main` assigns the final release number (`VER` in index.html and
  `CACHE = "sf-vNN"` in sw.js, always equal).
- Work in progress is named by feature, not number (for example `hybrid-memory`, not `v91`). The number is set at release.
- Before releasing: check the current `main` tip and its `VER`. The new release is `VER + 1`, even if a roadmap said otherwise.
- Never publish two builds with the same number: phones keep the old offline copy if the cache name doesn't change.

## Current state (2026-11-24)

| | |
|---|---|
| Live version | 90 (`main` d92a784) |
| Live site | https://celebrated-brigadeiros-580c41.netlify.app |
| Provider | DeepSeek via OpenCode Go only (Cloudflare Worker connector) |
| Memory notes default | Narrator only; hybrid and separate step are opt-in per story |

## Active branches

| Branch | Owner | Contents | Status |
|---|---|---|---|
| `v91-hybrid-memory` | Claude | Hybrid memory notes, `memStatus`/`memRetry`, contract docs | Simulated tests pass; paid trial not run |
| `v90-trial-notes` | Claude | v90 trial results in docs | Folded into `v91-hybrid-memory` |

## Module ownership

| Area | Owner |
|---|---|
| canon-engine.js, memory-engine.js, prompt assembly (`buildMsgs`), memory steps, trials | Claude |
| Screens and sheets, backups/restore UI, Timeline and Memory Studio, mobile layout | ChatGPT |
| Shared contracts (`docs/MEMORY-CONTRACT.md`, v87 notes/canon contract) | Both; change only with a note here |

## Roadmap (renumbered: targets, not fixed numbers)

1. Reliability, hybrid memory and OpenCode unification (shared)
2. Story Timeline and Memory Studio (ChatGPT)
3. Living Characters and Relationships (shared)
4. Living Worlds and Consequences (shared)
5. Cinematic Reader and Episodes (ChatGPT)
6. Advanced Creator Studio (ChatGPT)
7. Persistent Universes and Sharing (shared)
8. Personal Story Director and polish (shared)

## Approvals

Anna approves: paid API trials, publishing to the live site, hosting changes, destructive data changes,
and big changes to the memory design. Everything else (coding, free tests, branches, packaging) goes ahead.
