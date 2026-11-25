# Story Forge development manifest

The single place for what is live, what is in progress and who owns what. Both assistants update it with every batch.

## Authorization (Anna, 2026-11-25 00:08 MT)

Claude and ChatGPT continue through the whole agreed roadmap without waiting between routine batches: coordinate, implement missing APIs,
integrate UI, run regression tests, fix bugs, move to the next phase. **Stop and ask Anna only for:** paid API usage beyond existing
authorization, potentially destructive changes, major architecture decisions that can't be safely reversed, and production deployment or an official release.
Preserve existing stories, artwork, settings, credentials and backups. Keep production stable.
Paid testing: the memory-overhaul OpenCode authorization (stop at 45% monthly, ledger in USAGE-LEDGER.md) remains; fanfiction-specific paid trials still need Anna.

## Release-number rule

- Only the branch that publishes to `main` assigns the release number (`VER` in index.html = `sf-vNN` in sw.js).
- Work is named by feature, not number. The new release is `main`'s `VER + 1` at release time.

## Live and branches

| | |
|---|---|
| Live (production) | **92** (released 2026-11-25 with Anna's approval): menu reorganisation, fanfiction engine + first screens, real-world/romance/competition, memory v2 engine + opt-in recall, living characters engine. |
| Test address | https://deploy-preview-7--celebrated-brigadeiros-580c41.netlify.app (draft PR #7 = `memory-overhaul`) |
| Integration branch | `memory-overhaul`: Claude merges, runs the full suite, pushes |
| ChatGPT branch | `ui-overhaul` (fast-forwarded to `memory-overhaul` after each integration) |
| Claude branch | `fanfic-engine` (merged; new engine work goes straight to `memory-overhaul`) |

## Ownership

| Area | Owner |
|---|---|
| Engines (`memory-engine.js`, `memory-v2.js`, `canon-engine.js`, `fanfic-engine.js`, future `*-engine.js`), prompt assembly, generation pipeline, adapters in index.html, trial page, engine tests, integration and full-suite runs | Claude |
| Screens (`fanfic-ui.js/.css`, future `*-ui.js/.css`), `menuSheet` and sheet UI, navigation, Memory Studio, Timeline Explorer, backups UI, visual design | ChatGPT |
| Contracts (`MEMORY-CONTRACT.md`, `MEMORY-API.md`, `FANFIC-CONTRACT.md`, future contracts), fixtures, this manifest | Both |

Workflow per batch: ChatGPT commits to `ui-overhaul`; Claude merges into `memory-overhaul`, runs `tests/run_all.py` (includes `js_syntax_check`) and new browser tests, fixes integration bugs, pushes, fast-forwards `ui-overhaul`, and reports. UI changes go through adapter functions only.

## Roadmap status

| # | Phase | Engine (Claude) | UI (ChatGPT) | State |
|---|---|---|---|---|
| 1 | Novel menu cleanup + navigation polish | — | 8 categories, search, favorites, last category | ✅ integrated |
| 2 | Fanfiction overhaul (contract v2) | ✅ indexing, revisions, butterfly, rules, characters, knowledge, relationships, fates, prompt, checks | ✅ first screens (Source Library, Studio, Canon Manager, Timeline & Fates, Inspector, Continuity) | 🔄 UI depth + polish |
| 3 | Real-World Alternate Reality Creator (section 14) | ✅ types, public figures, safeguards, checks | ✅ first screen | 🔄 |
| 4 | Idol and career simulation | ✅ seeded ranking + recorded results | ✅ Competition Studio first screen | ⏭ career modules (engine: stats, milestones, schedules) |
| 5 | Romance Preferences | ✅ eligibility gate, prompt, checks | ✅ first screen | 🔄 |
| 6 | Living Characters and Relationships | ⏭ relationship evolution from events, personality drift checks, NPC agendas | ⏭ relationship web, character journals | **next** |
| 7 | Memory 2.0 + Memory Studio | ✅ nine-layer view, overlays, recall, contradictions, temporal | ⏭ Memory Studio screens | UI pending |
| 8 | Persistent Universes + Crossovers | partial (universe store, revisions) | ⏭ universe library, crossover config | later |
| 9 | World Simulation + Gameplay Designer | partial (NPC schedules, progression) | ⏭ | later |
| 10 | Advanced Creator Studio | — | ⏭ | later |
| 11 | Cinematic + Visual Novel | existing v49/v53/v54 modules | ⏭ | later |
| 12 | Story Director | ⏭ pacing and focus engine | ⏭ | later |
| 13 | Appearance and customization | — | ⏭ | later |
| 14 | Final stability, performance, compatibility | ✅ suite + long-run + large-universe harness | ⏭ | end |

## Integration log

| Date | Commit | What | Result |
|---|---|---|---|
| 2026-11-24 | b2b10ed | ui-overhaul e35a6e6 (menu) + fanfic-engine | full suite pass; menu parity 50/50; 17 old tests adapted via `tests/menu_helper.py` |
| 2026-11-25 | release 92 | memory-overhaul b083875 + version bump | full suite pass; upgrade 91 -> 92 check 26/26 (keys, stories, art, offline, deadlines/branches, world export) |
| 2026-11-25 | 66e674c | ui-overhaul c69ceb5 (10 commits: Source Library, management screens, competition, favorites, search, last category) | **bug fixed:** `fanfic-ui.js` missing `}` in drawFavorites (whole UI file failed to load); added `tests/js_syntax_check.mjs`, `tests/fanfic_ui_screens.py` (16 checks); helper adapted for favorites panel; full suite pass |

## Known issues / notes

- "Manage favorites" repeats every menu item as a checkbox above the categories (collapsed). Consider moving it into Advanced & Settings to keep the drawer short.
