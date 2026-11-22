# Memory Engine Phase 0 — safe foundation

This build starts from Story Forge v32 and includes Claude's memory proposal as reference.

- Adds `memory-engine.js` with an additive v1 memory schema, non-mutating legacy migration, relationship-history read API, character/timeline views, statistics and integrity checks.
- Adds `memv2:false` as the default database flag. **No existing sessions are migrated or modified automatically.**
- Existing story generation, storage, and relationship features remain on the v32 code path.
- Phase 1 (META event extraction and reversible per-turn deltas) is **not implemented**. Do not enable `memv2` for production.
- The exported project does not include your browser's locally saved stories. Back them up from the running app before switching builds.

Validation: JavaScript syntax and isolated API checks only. Full browser and saved-story migration tests are pending.
