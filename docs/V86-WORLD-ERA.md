# v86 integrated era and visual canon development patch
Base: v85 stabilization R2. Version and offline cache updated to 86. No changes to memory-engine.js.

- Story editor and AI world builder: optional era, date, region, genre, technology, rules, dialogue, magic, strict/flexible/unrestricted, cover upload and approved visual profile.
- Existing editable stories can access settings from story information. Existing unconfigured stories retain their prior narrator prompt.
- Optional user-triggered OpenRouter vision analysis of uploaded cover; model ID entered by user; suggestions reviewed and applied explicitly, preserving populated fields. No automatic paid calls.
- Persistent profile included in narrator, simulator setup, world builder, creative idea and scene/portrait prompts; world exports and templates retain profile.
- Tracked elapsed days use existing explicit skip records; ISO dates get calculated calendar dates. No automatic inference of elapsed narrative time or independent NPC simulation.
- Lightweight warnings for a limited set of modern terms in strict early eras; disabled when custom exceptions or visual context are present. Not a comprehensive validator or automatic rewrite.

Verification: seven Node test scripts passed (including new world era test), precache check passed, inline JS syntax passed, memory engine SHA256 unchanged. Chromium launched but localhost navigation blocked by administrator policy; browser UI and actual paid vision/story generation remain unverified. No deployment or real API calls. Additional location/character/scene reference analysis, autonomous NPC era simulation, and automatic narrative calendar progression remain future work. Development build only.
