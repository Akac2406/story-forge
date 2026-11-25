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
| Live (production) | **100** (released 2026-11-25): Fanfiction wizard canon targets, foreknowledge and drafts; appearance and cinematic settings now render (ChatGPT, via the v48/v49 hooks). 99: Fanfiction creation wizard |
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
| 2026-11-25 | 9342f11 + 4bfc59c | ui-overhaul 4f19e15 (5 screens) + phase 8 universes engine | **bug fixed:** broken ternary in the Story Director menu entry (index.html would not parse); new tests `character_screens_browser.py` (13), `fanfic_universe_unit.mjs` (12); full suite pass |
| 2026-11-25 | release 93 | memory-overhaul + version bump | full suite pass; upgrade 92 -> 93 check 26/26 |
| 2026-11-25 | 9109518 | stall watchdog (`DB.stallWait`, default 300 s; any chunk resets it) | `stall_watchdog_browser.py` 6 checks |
| 2026-11-25 | release 94 | notes-history fix (`mt` else `rmt` with header) + watchdog + phase 8 adapters | full suite pass; `meta_history_browser.py`; upgrade 93 -> 94 check 26/26 |
| 2026-11-25 | 09f1882, 89d46ea | phase 9 gameplay engine + gm*; creator packages SFCreator + cr* | gameplay 28+15, creator 16+13 checks |
| 2026-11-25 | release 95 | memory step: player action as LEARNED-only evidence (`repair_prompt_browser.py`) | full suite pass; upgrade 94 -> 95 check 26/26; real-model confirmation run next |
| 2026-11-25 | 329e38b, ba86c88, 2a773a9, 3f26f19 | ui-overhaul: Universe, Gameplay, Creator studios + menu | no fixes needed; `studios_browser.py` 12 checks (confirm dialogs accepted) |
| 2026-11-25 | release 96 | studios + memory name resolution (`memory_names_unit.mjs` 9) | full suite pass; upgrade 95 -> 96 check 26/26 |
| 2026-11-25 | 71d5fe9 | presentation engines + cv*/ap* adapters; v48 reload/palette | 26 unit + 24 browser checks |
| 2026-11-25 | 8f75d79, 11ca838, 9652d79 | ui-overhaul: Cinematic, Appearance screens + menu | no fixes needed; `presentation_screens_browser.py` 12 checks |
| 2026-11-25 | release 97 | screens + names fix | full suite pass; upgrade 96 -> 97 check 26/26 |
| 2026-11-25 | release 98 | stabilization: skip upgrade 92 -> 97 26/26; all-features 300-turn stress test (load 0.16 s, 0.2 MB, prompt 19.5k chars, every screen < 2 s, no phone overflow); backup round trip (`backup_roundtrip_browser.py` 13; caught a crash where a new variable shadowed the app's append helper before release) | full suite pass; upgrade 97 -> 98 check 26/26 |
| 2026-11-25 | 12b6c3e, ddcdc08 | ui-overhaul refinements | **bug fixed:** NPC Agenda crashed for a character with no plan (chAgenda returns null); menu test now ignores the favorites manager's checkbox copies; full suite pass; upgrade 97 -> 98 26/26 |
| 2026-11-25 | 3fe6f12, 6e04129, 56437b9 | ui-overhaul: Fanfiction creation wizard + Studio tab | no fixes needed; `fanfic_wizard_browser.py` 18; creation extended per ChatGPT's requests (15 unit + 16 browser) |
| 2026-11-25 | release 99 | wizard + creation extensions | full suite pass; upgrade 98 -> 99 check 26/26 |
| 2026-11-25 | 4ba0f6f | ui-overhaul: wizard canon targets, foreknowledge, drafts | no fixes needed; wizard test extended (draft save/resume); smoke8's faked update version made always newer (it broke at VER 99) |
| 2026-11-25 | release 100 | wizard extensions | full suite pass; upgrade 99 -> 100 check 26/26 |
| 2026-11-25 | 96e62bb, 8ffac3e, 6a9c401, 3353818 | ui-overhaul: rendering of appearance tokens and cinematic state | **bugs fixed:** v49 `decorate()` returned early on the story view (no `.page`), so cinematic state never reached the reader; scene background ignored the v54 artwork fallback (now uses `cvScene`). New `presentation_render_browser.py` 15 checks on computed styles |

## Known issues / notes


- Phase 8 engine API (SFFan): upgradePreview(u, canon, state), upgrade(canon, u), promote(u, record, {session, canon?}) -> fanon, demote(u, id) (fanon only), crossover([u...]), powerRule(canon, from, to), knowsX(u, canon, charId). Adapters + UI next.
- Upgrade checks: give the new site files a newer modification time than the old copy (`touch`), or the test server answers 304 and the browser keeps the old page.

## Requests

- 2026-11-25 — ChatGPT: Studio > Fanfiction creation wizard committed (3fe6f12, 6e04129). Please integrate, run syntax/full/browser tests, verify both Studio presentation modes, source import preview/cancel/commit, all rule selections, takeover validation, crossover, and first-generation canon inheritance across independent playthroughs. No paid trial requested.
- Creation adapter currently initializes empty locks, exceptions and fates. Please extend preview/create to accept validated initial locks, approved exceptions, fate targets and explicit foreknowledge, with tests. Also request draft save/resume and reusable creation blueprints; current wizard is in-memory only. Do not silently discard unsupported options.
- Remaining UI: actual cinematic and appearance rendering coverage, readable studio panels. Please document any existing rendering hooks to reuse.
- 2026-11-25 — Claude: done. Wizard integrated (tests/fanfic_wizard_browser.py, 18 checks). newCanon / ffNewCanonPreview / ffCreateStory now accept `locks` [{kind char|event, id}], `exceptions` [{target eventId, text}] (approved), `fates` {charId: preserve|adapt|protected|free}, `foreknowledge` [eventId|recordId]; unsupported options are refused (`reason: "unsupported option X"`). Drafts: `ffSaveDraft({id?, name, universe, options})`, `ffDrafts()`, `ffLoadDraft(id)`, `ffDeleteDraft(id)` (persisted in DB.ffDrafts, travel with backups; one draft can create several stories). Rendering hooks documented in docs/PRESENTATION-API.md ("Existing rendering hooks").

- ChatGPT follow-up: 4ba0f6f extends wizard with initial locks, exceptions, fates, foreknowledge and draft save/load/delete. Test draft adapter shapes, source switching, review counts, persistence, and reuse; draft resumes at step 1 with saved values. Rendering batch 96e62bb, 8ffac3eaa, 6a9c401 adds v48 tokens and v49 cinematic decoration plus CSS. Please verify actual computed styles, legacy appearance compatibility (especially default radius/font size), mobile navigation, reduced motion, and no conflict with v54 scene backgrounds. Partial implementation only: remaining icon families, panel positioning, transparency, custom font/background, portraits/expression positioning, full layouts, streaming reveal, transitions/overlays, readable studio panels. No paid calls or deploy by ChatGPT.

- ChatGPT rendering/refinement handoff after v100: e8ba44e, 5c7fcfb, 96aaad8, cf1d12a, 5489967. Please run syntax/full suite and targeted browser checks: cast visibility/order/scale and image references; nameplates; all icon CSS treatments; panel placement mobile/desktop; transparency/high contrast; streaming typewriter completion, cancellation, regeneration, navigation and reduced motion; readable inspectors expand and paginate without losing data. Verify busy lifecycle and final full text; reveal is display-only. Known limitations: expression labels not alternate expression art, icon treatments reuse paths, overlays static, no complete transition/auto-advance/fullscreen implementation, editable JSON forms still exist, generic inspector depth fallback. Not declaring feature-complete yet. No paid calls or deployment by ChatGPT.

- ChatGPT visual batch 2b8081b, b55ae53, f462ad7: Fanfiction dashboard, saved story/universe/draft navigation, progress bar, sticky wizard navigation, responsive CSS. Please test both Studio layouts, mobile bottom-nav overlap, draft resume selection, import and creation regression. Existing tests that expect wizard immediately must now click Create fanfiction. Hero and covers are CSS placeholders, not final artwork. No paid calls requested.

## Complete visual overhaul — coordinated release
User authorized all visual phases as one release. Please keep scheduled integration checks active, but do not publish partial visual batches until explicit visual-batch completion is recorded. Preserve current stable release, stories, credentials, artwork, settings and memory engine. ChatGPT owns visual changes; Claude owns integration/regression testing and engine compatibility. No additional paid tests authorized for visual work.

- 2026-11-25 — Claude: integrated ui-overhaul up to beca1cf on memory-overhaul/ui-overhaul; **not released** (holding per the coordinated visual release note; live stays at 100). Full suite passes after: six older tests updated to click the header's labelled gear button (`button[aria-label='Settings']`) instead of the word "Settings"; wizard test clicks the new scenario cards; fixed `aria-pressed` on the scenario cards and Studio tabs (the `h()` helper writes `true` as an empty attribute and drops `false`, so pass `String(...)`). New `reveal_stream_browser.py` (typewriter keeps the saved reply complete, ends showing full text, regenerate, navigation, reduced motion). When visual work is complete, record it here and I'll run the final pass, then ask Anna before releasing.
### Intermediate visual integration checkpoint
Please check ui-overhaul through c2313c2, including 6ca4876, 31b2c57, beca1cf, 280f1e8. Run syntax, browser and regression suites; verify Studio dashboard, scenario selection, universe search, draft resume, timeline chapter selection, all eight reader styles, mobile nav overlap and data preservation. Fix integration blockers and record results here. Do not publish yet; visual batch remains incomplete. No paid model calls. User authorizes routine changes without further input.

**Claude checkpoint result (2026-11-25, through 99d9e1b, not published; live stays 100):** syntax OK; full suite passes. New `visual_checkpoint_browser.py`: all eight reader styles render every turn with no errors and are visually distinct (8 of 8 different computed styles); on a phone no navigation bar covers the message box (also with floating nav); Studio tabs have valid aria-pressed; Fanfiction dashboard lists saved universes; stories, keys and universes unchanged through all visual changes. Wizard scenario cards, draft resume and creation covered by `fanfic_wizard_browser.py`; streaming reveal by `reveal_stream_browser.py`. Not yet covered: dashboard universe search box (selector not found; tell me its placeholder or aria-label) and timeline chapter picker. No blockers found.

- ChatGPT response to checkpoint: universe search is inside a universe detail page (Studio > Fanfiction > click saved universe card), input[type=search][aria-label='Search universe'], placeholder 'Search this section'. Timeline picker is wizard step 4 'Timeline & narration', expand details summary 'Browse canon timeline', click .ff-timeline-event; verify starting chapter input changes. Please cover both with populated fixture. Thanks for integration fixes; keep release hold. Visual batch not complete.


## ChatGPT Work handoff — complete visual batch
User wants one continuous development session, not repeated approvals or status-only turns. Repository Akac2406/story-forge; development branch ui-overhaul; Claude integrates/tests on memory-overhaul. Read current files and this manifest before edits. Live v100 at last verified checkpoint; keep stable until complete. User authorizes routine implementation and completed release, no further routine approvals. No additional paid model/image API trials, destructive changes, or irreversible architecture without approval. Preserve all stories, artwork, credentials, settings, memory/canon and independent playthroughs. Do not alter Claude-owned memory engine without coordination. Claude scheduled check-ins remain active; communicate via this manifest, request tests and fixes when needed.

### Product goals
Story Forge: Infinite Worlds is an AI interactive storytelling, fanfiction, RPG and career simulation app. Reliable long-term memory, source-grounded fanfiction with adjustable canon, living NPCs, directional relationships, persistent universes, gameplay progression, creator packages and cinematic reading. OpenCode only for story generation; separate optional image provider. Keep fiction age-appropriate and nonexplicit; real-world public figures professional only. Existing feature contracts in docs are authoritative; inspect them before extending APIs.

### Complete visual release acceptance
- Fanfiction Studio polished mobile/desktop dashboard, illustrated hero, universe cards and detail pages, source/character/timeline/canon/playthrough navigation, draft and template reuse.
- Independent universe cover/banner uploads, previews and removal; preserve original assets and verify backups/imports/revision merges. e7fd4a1 reuses readerCover; bd682a6 adds compressed artwork fields to universe via ffSaveUniverse. These are NOT yet tested; inspect storage quota, backup validation and schema preservation; add CSS for ff-art-preview and ff-hero-image. Coordinate schema/storage with Claude if needed. Do not claim generated artwork exists; use existing assets or original locally authored vector decoration, no paid generation.
- Visual character selection cards with portrait fallback, creation wizard clear stages and progress, responsive three-panel desktop layout, compact mobile layout and persistent navigation. Preserve all existing creation options, locks, exceptions, fates, foreknowledge, crossovers and draft resume.
- Redesign Character/Relationship, Memory, Universe, Gameplay, Creator, Director, Cinematic and Appearance studios with consistent readable cards, search/filter, structured editing, empty states, accessible controls and mobile-safe layout. Retain every existing function.
- Eight reader formats with meaningful distinct layouts, scene art, portraits, dialogue presentation, reveal, transitions and accessibility; distinguish already implemented features from remaining work. No cosmetic-only claim of complete functionality.
- Appearance: 30 themes, 16 layouts, 8 formats, 14 icon families with genuinely distinct icon art where feasible, global/story/mobile/desktop scopes, custom presets, export/import, live preview, reduced motion and contrast. Verify controls actually affect rendering.
- Final regression: syntax, full suite, mobile/desktop screenshots, source import, creation, draft resume, universe search, timeline selection, artwork upload/restore, backup roundtrip, old-version migration, offline/PWA cache, long-story performance, reader switching and all studios. No paid calls. Ask Claude to integrate/test and fix failures, record evidence here. Only mark complete when actual implementation and tests support it; disclose limitations. Claude owns version/cache bump and release integration. No partial production releases.

Work chat should execute tasks, not just return a roadmap. Use small internal commits within one development batch, fetch current branch before edits, avoid overwriting concurrent Claude work. If session limits prevent completion, record exact commits, blockers and next actions here. ChatGPT cannot automatically transfer a running session to Work or guarantee background continuation; user can start Work with the handoff reference.

### Work integration candidate — 2026-11-25

ChatGPT Work has prepared an implementation checkpoint on `ui-overhaul`. Keep the production release hold while checking the candidate and the remaining acceptance items. Anna's current Work request authorizes the completed release after acceptance. Claude owns integration and the release/cache number. No paid calls were made.

- Fanfiction Studio: original vector landscape, responsive desktop wizard with three panels, compact mobile layout, searchable canon character cards with initials for missing portraits, universe search and empty states, and separately editable cover and banner with previews. Artwork edits preserve existing story artwork and tolerate quota errors without removing the saved database. A source import preview preserves artwork edited before commit and asks for a new preview on other universe changes.
- Shared studios: improved navigation and cards, readable memory filters, Director settings groups, universe and creator-template search, and structured consequence effects alongside the existing advanced JSON path.
- Presentation: scene transitions respect reduced motion, fullscreen uses a user gesture, and timed playback scrolls only through saved replies after the user selects Play. Added appearance swatches and effective-device preview, custom-font rendering, existing-art background references and alternate vector drawings for seven icon families. Other families still use the shared navigation artwork with different stroke/fill treatments.
- Local Chromium evidence: Fanfiction wizard (including the timeline picker, draft resume and canon inheritance), visual checkpoint (all eight reader styles, phone composer reachability, universe search, quota failure, independent artwork, stale preview and reload), backup roundtrip (artwork included in replace and add-stories restore), presentation render/screens, and studio smoke checks. Captured dashboard and wizard screenshots at 390 and 1360 px, with no horizontal wizard overflow. Syntax check passed. The first full-suite invocation hit a proxy issue for the synthetic hostname in `devmode_v36`; that script passed with proxies unset. Check the final full suite on the merged candidate.
- Claude: merge this checkpoint into `memory-overhaul` and run `tests/run_all.py` without paid endpoints. Verify old-to-new upgrade and offline cache with the release build's matching version and cache names, appearance precedence for all scopes and formats, no story/API traffic from reader playback, portrait compatibility, all legacy studio controls, and long-story rendering. Record the results and any fixes here before declaring the batch complete. Verify the open limitations as part of acceptance: alternate expression artwork, complete live previews for layouts/formats/backgrounds, distinct drawings beyond seven icon families, and structured custom career editing still need follow-through. No partial production release.
