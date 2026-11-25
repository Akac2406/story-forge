# Presentation API (Cinematic / Visual Novel, Appearance & Customization)

Engine: `site/presentation-engine.js` (`SFCinema`, `SFAppearance`; pure). Adapters in `index.html`. Built on the existing systems, not alongside them: appearance settings live in the v48 store (`sf.visual.v48`, same `{version:1, global, stories, devices, custom}` shape) and v48 now exposes `SFVisualV48.reload()`, `palette(name)` and `KEY` so the adapters and the v48 screen never overwrite each other; scene artwork comes from the v54 scene presets (`sf-v54-scene-presets`) and portraits from `se.cast[name].pic`, by reference only.

All mutations return `{ok, applied, reason}`. Presentation never changes story text, canon, memory, character knowledge, gameplay or credentials. Image data is never stored by these adapters: background/portrait values must be references (`v54:<sessionId>`, `cast:<name>`, `art:…`, `idb:…`, `story:…`); `cvArt(se, ref)` resolves one to an image URL for display.

## Cinematic (per playthrough, `se.cv`)

| Adapter | Notes |
|---|---|
| `cvLayouts()` | 8 layouts `{id, name, caps}`: novel, visual-novel, cinematic, rpg, chat, screenplay, illustrated, immersive. `caps`: portraits, background, dialogueBox, reveal (+ letterbox, hud, bubbles, sluglines, plates, hideUI) |
| `cvPresets()` | 11 presets `{id, name, settings}` (quiet-novel, classic-vn, noir, storybook, jrpg, neon-city, gothic, messenger, screenplay, immersive-theatre, calm) |
| `cvState(se)` | `{settings, layout, scene, cast, preset}` effective; `reducedMotion` forces transition none, typewriter → fade-in, removes moving overlays |
| `cvSet(se, patch)` | settings: layout, lighting (neutral dawn day dusk night candle storm neon underwater), overlay (none rain snow fog embers petals film-grain vignette scanlines), transition (none fade dissolve slide wipe flash), dialogueBox (classic minimal parchment glass comic terminal), nameplate, narration (plain italic boxed centered), textReveal (instant typewriter fade-in), revealSpeed 5–120, autoAdvance, autoDelay 1–30 s, fullscreen, hideUI, reducedMotion |
| `cvApplyPreset(se, id)` | merges the preset's settings; keeps scene and cast |
| `cvScene(se)` / `cvSetScene(se, {background, lighting, overlay, transition, caption})` | falls back to the v54 artwork and caption for this playthrough |
| `cvCast(se)` / `cvSetCharacter(se, name, {expression, position, scale 0.5–1.5, visible, portrait})` | expression: neutral happy sad angry surprised afraid thoughtful smug tired determined; position: far-left left center right far-right offscreen |
| `cvReset(se)` | clears presentation only |
| `cvArt(se, ref)` | image URL for a reference, or null |

## Appearance (global, device and story scopes)

Scopes: `"global"`, `"mobile"`, `"desktop"`, `"story"` (this playthrough's story) or `"story:<id>"`. Precedence as in v48: global, then story, then device.

| Adapter | Notes |
|---|---|
| `apThemes()` | 30 v48 themes `{id, name, palette: [bg, card, accent]}` (custom palettes included) |
| `apLayouts()`, `apFormats()` | 16 interface layouts, 8 reader formats (v48) |
| `apIcons()` | 14 icon families `{id, name, style}` (line, rounded, solid, duotone, pixel, sketch, ink, runic, neon, engraved, geometric, sticker, glyph, blueprint); `style` gives stroke, fill, corner, weight and family-specific traits for rendering |
| `apState(se, device?)` | effective settings; `reducedMotion` forces motion none, `contrast: high` forces transparency 0 |
| `apSet(se, patch, scope)` | keys: theme, layout, format, motion (none subtle full), icons, bg/card/accent/text (#rrggbb), font, fontScale 0.8–1.4, spacing (compact cozy roomy), transparency 0–0.6, borders (none thin bold), radius 0–24, nav (bottom top side floating), panel (right left bottom overlay), reducedMotion, contrast (normal high), background (artwork reference). `null` clears a key. Theme/layout/format must exist (or be a v48 "Use …" value). |
| `apReset(se, scope)` | clears that scope |
| `apPresets()`, `apSavePreset(name, settings)`, `apApplyPreset(se, id, scope)`, `apDeletePreset(id)` | presets keep only appearance keys |
| `apExportPreset(id)` → `{format:"story-forge-appearance", version:1, name, settings}`; `apImportPreview(data)` → `{ok, issues, name, settings}` (unknown keys ignored and reported); `apImport(data)` saves it as a preset |

Tests: `tests/presentation_engine_unit.mjs` (26), `tests/presentation_app_browser.py` (24).
