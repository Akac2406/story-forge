# v46 Visual Suite (development)

Adds a single read-only Visual Suite accessible from Studio and in-story header. Includes character RPG cards with portrait and bond bars, relationship summaries, world codex atlas, message chronology, visual-novel scene preview, theme/layout switcher, and links to existing character and art tools.

The atlas is text-based, not a geographic map. Timeline is read-only and not a branching editor. Visual Novel preview does not parse dialogue into speakers or generate art. Existing themes/layouts are reused; no new image generation or API calls. No modifications to memory-engine.js or memory data schemas.

Testing: JS syntax, memory unit tests, ZIP integrity and static feature checks; browser and saved-story restoration still pending. Keep backups and do not replace production deployment.
