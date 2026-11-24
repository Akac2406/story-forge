# v85 stabilization report (development build)

## Scope
Source: user-supplied `story-forge-v84-chapter-audio(1).zip`. No production deployment, GitHub updates, paid API calls, or memory-engine modifications.

## Change made
- Service worker cache namespace advanced from `sf-v84` to `sf-v85`.
- Precache list now includes `listen.html`, `manifest.webmanifest`, and `icon-512.png` so the chapter audio player, install manifest, and large PWA icon are included in offline application assets.
- Verified every precache asset exists in the package, and `sw.js` passes Node syntax checking.

## Verification
- All five packaged Node-based test scripts passed: memory_phase1_unit (19 passed, 0 failed), scene_backup_v55, story_setup_and_deadlines, unknown_v43, and chapter_audio_seek.
- Full Python Playwright regression suite attempted. Browser tests are **unverified** in this environment: Playwright's bundled Chromium was absent; substituting system Chromium launches but navigation to local HTTP test servers is blocked (`net::ERR_BLOCKED_BY_ADMINISTRATOR`). These are test-environment failures, not evidence of app failures.
- No user stories or API keys were accessed: those live in browser storage, not the ZIP.

## Outstanding before production approval
1. Run `python tests/run_all.py` on a machine permitting Playwright to visit localhost (install browser with `python -m playwright install chromium` if needed).
2. Exercise offline `listen.html`, chapter audio seeking, service-worker update behavior, mobile customization, save/restore and import/export in a real browser.
3. Confirm memory engine compatibility in the actual browser; do not alter Claude's implementation without approval.
4. Compare source against the current GitHub branch before merging.

This is a limited stabilization build, **not** a full v85 regression-certified release.

## Follow-up stabilization pass — static cache safety
- Restricted service-worker fetch interception to the 22 precached app-shell paths. Dynamic and private paths, query-string URLs, non-GET methods, cross-origin requests, and range requests now bypass the service worker entirely.
- Cache updates now accept only successful, non-redirected, non-opaque static responses. Offline fallback remains available for cached app-shell files.
- Added `tests/v85_sw_scope.mjs`, a Node VM regression test covering allowlisted assets, dynamic/private bypass, query strings, POST, range, cross-origin, and offline fallback.
- Updated the offline asset test parser to handle the compact manifest format.
- Verified the five original Node suites plus the new service-worker suite and offline manifest test; all passed.
- Browser/Playwright regression and live user-data verification remain outstanding. No production deployment, GitHub update, paid API call, or memory-engine modification.
