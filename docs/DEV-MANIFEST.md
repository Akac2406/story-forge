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
| `memory-overhaul` | Claude + ChatGPT | The whole memory overhaul (starts from hybrid memory, `memStatus`/`memRetry`) | Draft PR #7 = test address https://deploy-preview-7--celebrated-brigadeiros-580c41.netlify.app |
| `v91-hybrid-memory`, `v90-trial-notes` | Claude | Folded into `memory-overhaul` | Done |

## Module ownership

| Area | Owner |
|---|---|
| canon-engine.js, memory-engine.js, prompt assembly (`buildMsgs`), memory steps, trials | Claude |
| Screens and sheets, backups/restore UI, Timeline and Memory Studio, mobile layout | ChatGPT |
| Shared contracts (`docs/MEMORY-CONTRACT.md`, v87 notes/canon contract) | Both; change only with a note here |

## Plan

Per Anna (2026-11-24): one complete memory overhaul, one testing campaign, one release. See docs/MEMORY-OVERHAUL-ARCHITECTURE.md and docs/USAGE-LEDGER.md. Target 2026-11-30, contingency 2026-12-04.

## Roadmap after the overhaul (targets, not fixed numbers)

1. Reliability, hybrid memory and OpenCode unification (shared)
2. Story Timeline and Memory Studio (ChatGPT)
3. Living Characters and Relationships (shared)
4. Living Worlds and Consequences (shared)
5. Cinematic Reader and Episodes (ChatGPT)
6. Advanced Creator Studio (ChatGPT)
7. Persistent Universes and Sharing (shared)
8. Personal Story Director and polish (shared)

## Approvals

Anna approves: publishing to the live site, hosting changes, destructive data changes,
and big changes to the memory design. Real-model testing is pre-approved up to 45% monthly OpenCode usage (ledger). Everything else (coding, tests, branches, packaging) goes ahead.
