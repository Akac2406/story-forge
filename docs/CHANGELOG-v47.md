# v47: memory build + visual build combined

Base: deployed v46 (Story memory (beta), copy-only pilot, metadata fill-in, offline cache).
Ported onto it: ChatGPT's v46-visual build (character creator, templates, relationship map,
art references and archives, Studio home tab, Visual Suite with 8 tabs, "Visuals" header pill,
integrated visual styles).

## How it was merged
Three-way merge with v44 as the common ancestor. index.html merged with 0 conflicts.
Kept from the memory side: memtrial.js (v46 trial page, the visual build had the old v44 one),
sw.js (the visual build inherited an empty sw.js from v38 to v44; ours was restored in v45),
memory-engine.js (identical on both sides).

## Fixes made during the merge
- Phone: the 5 home tabs (with the new Studio tab) were 58 px wider than a 390 px screen. They now fit.
- Studio tiles: "1 custom creations" / "1 saved sessions" now read "1 custom creation" / "1 saved story".
- Tests: the Mode pill selector now targets `button.pill:has-text('▾')`, because the Visuals pill comes first.
- App version 47, offline cache sf-v47.

## Testing (simulated replies only, no real model calls)
- All 31 test suites pass, including the new tests/visual_merge_v47.py, which checks at phone and desktop size:
  screen fit, Visual Suite leaves the story untouched, send, metadata kept out of the text,
  regenerate, previous/next version, branching, Story memory (beta) sheet, memory not on globally,
  offline load, and Studio offline.
- No page or console errors.

## Not done
- No live model run on v47. Not deployed: branch visual-merge only.

## Layout sweep (tests/layouts_v47.py)
All 15 UI layouts, each with cinematic reading off and on, at phone and desktop size (60 combinations):
layout applied, no sideways scrolling on home or in a story, story text, Send, Regenerate, Menu and Visuals visible, no page errors.
Observation: most layouts are subtle restyles (borders, button shapes, glow), and cinematic reading frames each reply in a card. None adds art by itself.
