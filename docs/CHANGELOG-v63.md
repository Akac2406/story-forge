# v63: art and relationships interface update

Built from the v57 package (v56 Illustrated Reader + optional encrypted OpenCode key sync).
Changed files: index.html, sw.js (cache sf-v63), illustrated-reader.css, relationship-map-v52.js,
visual-customization-v48.js. New interface options: icon style and artwork, icon shape, navigation labels,
navigation position (top, bottom, desktop sidebars), dialog position, navigation style, panel shape,
spacing and interface font; reader player controls.
Unchanged: memory-engine.js, memtrial.js, site/trial/, key storage, sync and backup code.

Checks before release (no model calls): full suite 33 pass, 4 skipped (need screenshot/EPUB fixtures);
all 19 offline-cache files exist; simulated upgrade from live v56 at the same address keeps the saved
OpenCode key, connector and provider, clears the old cache, and opens offline with no failed requests.
