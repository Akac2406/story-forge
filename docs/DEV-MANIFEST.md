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
| Live (production) | **102** (released 2026-11-25): post-release reliability fixes. 101: complete visual overhaul (official release) |
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

### Work visual implementation follow-through

- Completed the follow-on implementation listed in the checkpoint: all 14 navigation families have separate vector paths, the effective layout/format and referenced background render in the appearance preview, expression artwork can reference existing cast or scene art with default-portrait fallback, and the custom career form defines stats, ranks and activities. Advanced JSON remains available for modules with multiple requirements or effects. The expression-art map is additive in presentation state. No engine or generation pipeline changes.
- Local staged upgrade from production v100 to an unreleased v101 fixture preserved the story, cover reference, credentials, appearance, memory and canon and reopened offline with the old cache replaced. The 300-turn stress check, staged offline shell, artwork and backup roundtrip, visual browser tests and studio checks passed. The initial regression run passed all scripts it could execute except the environment's synthetic-host proxy failure, which passed in isolation with proxies unset. The final proxy-free regression run was started against the updated candidate. The EPUB and screenshot-fixture scripts require their inputs.
- Claude: use the latest `ui-overhaul` head, run the final integration regression and verify the released asset/cache mapping. This supersedes the implementation gaps listed at the checkpoint. Preserve the production hold until Claude has recorded release acceptance and resolved any integration findings. Anna has authorized the completed release. No additional paid API usage.

- Additional Work evidence: the locally staged v100 → v101 upgrade and offline reload passed again on the follow-through commit. Tested optional EPUB import/export and legacy screenshot import/cropping using generated fixtures with all model calls stubbed. Two legacy scripts were opening a collapsed menu item directly. They now use the existing menu test helper and pass with fixtures. The crop test creates its own output directory. No production version or cache changes on this branch.

### Work acceptance evidence — implementation ready for integration

All 90 repository regression scripts passed across local Node/Chromium runs, including the four fixture-dependent EPUB and screenshot scripts run separately with synthetic fixtures. The verified visual tree is `1301133`; it fast-forwards cleanly from both `memory-overhaul` and production `main`. The staged upgrade replaced the service-worker cache and reopened offline with the fixture's story, cover, credentials, settings, memory and canon intact. No paid endpoints were used. Claude's remaining gate is the integration run and official version/cache assignment. Production is still v100.

### Release candidate 101 — visual overhaul (Claude, 2026-11-25)

Integrated ui-overhaul through 81e7f46 on memory-overhaul. Version assigned: **101** (`VER=101`, cache `sf-v101`). Reviewed ChatGPT's test edits (additions only, no weakened assertions) and confirmed no engine files changed; every adapter called exists. Full suite passes (all scripts); upgrade checks 100 -> 101 and 92 -> 101 both 26/26 (keys, stories, artwork, offline, deadlines/branches, world export). Published as v101 on 2026-11-25 after Anna approved.

## Requests — v101 post-release reliability (ChatGPT source review of 7466312)

Bug-only batch; no new features or recall-default change without approval. Agree with pre-send watchdog and adaptive memory-step timeout. Please verify these source-derived candidates (not yet reproduced in browser):
1. Studio > Fanfiction > Universe: start import preview, then select another universe before indexing finishes. Source selector clears pending but does not increment epoch or abort controller; old preview can finish against detached controls. Invalidate on universe change, Back, dashboard exit; test delayed completion and no unintended commit.
2. Reader > Appearance & Customization: change transparency on a studio panel. fanfic-ui.css later .ff-ui .ff-panel{background:var(--card)} overrides earlier transparency rule; verify computed background and fix cascade, including high contrast.
3. Reader > Cinematic: select rain plus scene background. Inline log background-image overrides rain CSS; fog/vignette box-shadow also overrides lighting shadow. Verify composition, preserve artwork and readability; static overlays themselves are planned polish.
4. Reader > Cinematic: select typewriter, stream a long reply at low speed, stop/regenerate/navigate or finish. paintLast reveal RAF loops even when caught up while busy; verify full final text, no stale frame overwrites, no continuous DOM fill when caught up, no scroll stealing. No paid calls needed, use mock stream.
5. Reader > Cinematic: enable transition, open/close menu or rerender unchanged scene. sceneKey is on log DOM node; new log may replay transition unnecessarily. Test unchanged vs changed scene and reduced motion. Auto-advance is saved-reply playback, not generation; fullscreen is browser-native. Test playback stops on navigation and when tab hidden, fullscreen controls on unsupported browsers.
6. Studio > Fanfiction: save draft, resume, change universe, review. Confirm target-specific locks/exceptions/fates/knowledge reset only on actual universe change, no stale crossover or misleading summary; test switching scopes in Appearance (mobile -> global/story on desktop) and actual effective preview.
7. cvArt in index.html resolves v54: and cast: only, despite documented art:/idb:/story: references. Verify UI accepts only resolvable refs or reports unsupported reference clearly; no silent blank artwork. Expression art already implemented with base portrait fallback.

v101 has transitions, saved-reply auto-advance, native fullscreen, expression artwork, distinct main-navigation SVG paths for 14 families. Static atmospheric effects and extending icon designs to every control are polish, not release bugs. No code changes requested beyond verified fixes; no paid tests by ChatGPT.

### Release 102 — post-release reliability (Claude, 2026-11-25)

Fixed and covered by tests (`presend_watchdog_browser.py`, `reliability_102_browser.py`):
- Pre-send steps (memory snapshot, scene save, story check, memory tidy-up, references, wiki) have a time limit (`DB.prepWait`, 120 s) and error handling; a failing tidy-up used to drop the send silently (likely the trial wedge).
- Memory-step time limit adapts to provider speed (1.5x the last reply, 90–240 s) and the player is told when notes are skipped.
- ChatGPT's list: (1) switching universes cancels an in-flight import (`epoch`/abort in the wizard); (2) typewriter + Stop keeps and shows the whole reply; (3) studio panels honour transparency; (4) lighting and fog/vignette stack via `--sf-cv-light`/`--sf-cv-veil`, rain layers over scene artwork via `--sf-cv-rain`; (5) menus no longer replay the scene transition (last scene remembered per playthrough, not on `#log`); (6) draft universe switch resets only universe-specific choices (reviewed); (8) `cvArt` resolves `story:<id>`, and background/portrait references that resolve to nothing are refused with a reason. (7) editing-scope previews are covered by ChatGPT's presentation test.
Full suite pass; upgrade 101 -> 102 check 26/26.
