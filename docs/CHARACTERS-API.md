# Living characters API (roadmap phase 6) — engine by Claude, screens by ChatGPT

Engine: `site/character-engine.js` (`SFChar`, pure). Adapter globals in index.html. Tests: `tests/character_engine_unit.mjs` (18), `tests/character_app_browser.py` (9).

## Behaviour
- **Relationships evolve from story events** automatically after each reply (idempotent: an event is applied once per direction).
  Directional records `rel:A>B` with `trust`, `affection`, `respect` (-100..100) and `history[{event, t, change, why}]`. At most ±15 per event.
  Being saved or helped raises the target's view of the actor; lies, harm and betrayal lower it; arguments lower both a little; rivalry raises respect.
  Fanfiction stories store them in `se.canon.relationships` (stable ids, player = `player`), other stories in `se.rel2` (by name).
- **Labels:** hostile, wary, neutral, friendly, close, devoted (`chLabel(record)`).
- **Prompt:** fanfiction stories already include present characters' feelings (FANFICTION CANON block). Other stories add a "How the characters in this scene feel" section only when the Story memory "narrator uses story memory" switch is on.
- **Voice check:** after each reply `ai.voice = [{kind:'voice', name, text}]` when a character's spoken line clashes with their speech or temperament (slang from a formal speaker, long speeches from a terse one, shouting from a calm or shy one). No AI request.
- **NPC agendas:** goals and schedules from `se.npcs[name] = {goals[], schedule[{day, where, doing}]}` and World schedule "Character plan" entries; advanced by story days only.

## Functions
| Function | Returns |
|---|---|
| `chRelationships(se)` | directional records |
| `chEvolve(se)` | `{ok, applied}` (runs automatically; safe to call again) |
| `chHistory(se, a, b)` | `[{event, t, change, why}]` for A's view of B |
| `chLabel(record)` | label text |
| `chJournal(se, name)` | `[{t, kind, text, role: did|witnessed|learned|feels}]` |
| `chNpcs(se)` | `{name: {goals, schedule}}` |
| `chAgenda(se, name, fromDay, toDay)` | `{name, where, doing, goals, developments[{day, text}]}` |
| `chCheckVoice(se, text)` | voice issues |

## UI (ChatGPT)
Relationship web (directional arrows, labels, history on tap), character journal, NPC agenda view, and voice warnings in the Continuity Center (`ai.voice` next to `ai.ffc`).
