# Creator packages API (Advanced Creator Studio)

Engine: `site/creator-engine.js` (`SFCreator`, pure). Adapters in `index.html` (prefix `cr`). File extension `.sfcreator.json`, format `story-forge-creator` v1, max 8 MB.

A creator package is a reusable blueprint: story setup (`portableStory` fields), chosen character templates, gameplay **setup** (stats at starting values, quests not started, rules, career at its first rank; no progress, log or history) and Story Director settings, plus a reference `{id, name, rev}` to a fanfiction universe (never its content). It never contains playthroughs, memories, keys or credentials (keys like ocKey/apiKey/key/token/password/secret and values like `sk-…`/`Bearer …` are stripped on build and again on open). Images are dropped unless `art: true`, and never included for stories imported from OOC (`story.ooc`).

| Adapter | Returns |
|---|---|
| `crBuild(storyId, {sessionId?, templates?: [names], art?, creator?: {name, note}})` | `{ok, package, removed: [{path, why: credential|image}], size, artBlocked}`; gameplay/director come from `sessionId`'s playthrough, else from the story's blueprint |
| `crDownload(storyId, o)` | same, and downloads the file |
| `crPreview(pkg)` | `{ok, issues[], title, creator, characters, templates[], gameplay: {career, stats, quests, rules} or null, director, universe, art}` |
| `crOpen(pkg)` | `{ok, applied, reason, storyId, templatesAdded, needsUniverse}`; adds a new story with `blueprint: {game, director}` (and `universeRef`); duplicate template names are skipped |

New playthroughs of a story with a `blueprint` start with a fresh copy of its gameplay setup and director settings.

Tests: `tests/creator_engine_unit.mjs` (16), `tests/creator_app_browser.py` (13).
