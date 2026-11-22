# Story Forge v44 + Character/Art UI integration (development build)

Base: user-supplied Claude v44. The v44 memory engine, repair logic, tests, and reports are retained.

Added from the separate v40 UI workstream: expanded character profiles; character templates; relationship map; original image imports; portable art archives; art style reference presets.

No paid API calls, deployment, or migration of stored user data were performed. AI image generation is NOT connected. World atlas, persistent universes, visual novel, and full RPG redesign are NOT implemented in this build.

The character templates and art style presets are additive DB fields. Existing playthroughs are not rewritten by the integration script.

**Risk:** Browser end-to-end tests and real saved-story restore tests have not been performed. Use a separate browser profile or installation and retain original backups.

## Checks performed
- Combined inline JavaScript syntax: `node --check` passed.
- Claude v44 `memory-engine.js` byte-for-byte unchanged.
- Memory-engine unit tests: **19 passed, 0 failed**.
- Static feature-presence assertions: passed.
- Full browser test suite: **not passed / not completed** because the Playwright browser executable is not installed in this environment.
