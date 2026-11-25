# Living characters API (roadmap phase 6) — engine by Claude, screens by ChatGPT

Engine: `site/character-engine.js` (`SFChar`, pure). Adapter globals in index.html. Tests: `tests/character_engine_unit.mjs` (32), `tests/character_app_browser.py` (16). Fixture: `tests/fixtures/characters.json`.

**v2 (ChatGPT's refinements, all done):** familiarity and rivalry dimensions; relationships are *rebuilt* from player base values plus the events that still exist, so regenerating, deleting or branching away a reply removes its effect; player-approved changes with undo; journals split into did / witnessed / learned / believes / rumor / feels / intends with `source` and `playerKnows`; agendas with priorities, short/long-term goals, competing goals (`tensions`) and upcoming `commitments`; off-screen developments logged only when story days advance and tied to the reply (dropped if it is regenerated); voice warnings are advisory and become `growth` (recorded development) or `mood` (current mood) when explained. Romance eligibility stays in the fanfiction engine (`ffRomanceAllowed`).

## Behaviour
- **Relationships evolve from story events** automatically after each reply (idempotent: an event is applied once per direction).
  Directional records `rel:A>B` with `trust`, `affection`, `respect` (-100..100), `familiarity`, `rivalry` (0..100), `base` (player-set) and `history[{event, t, change, why}]`. At most ±15 per event.
  Being saved or helped raises the target's view of the actor; lies, harm and betrayal lower it; arguments lower both a little; rivalry raises respect.
  Fanfiction stories store them in `se.canon.relationships` (stable ids, player = `player`), other stories in `se.rel2` (by name).
- **Labels:** hostile, wary, neutral, friendly, close, devoted (`chLabel(record)`).
- **Prompt:** fanfiction stories already include present characters' feelings (FANFICTION CANON block). Other stories add a "How the characters in this scene feel" section only when the Story memory "narrator uses story memory" switch is on.
- **Voice check:** after each reply `ai.voice = [{kind:'voice', name, text}]` when a character's spoken line clashes with their speech or temperament (slang from a formal speaker, long speeches from a terse one, shouting from a calm or shy one). No AI request.
- **NPC agendas:** goals and schedules from `se.npcs[name] = {goals[string | {id, text, priority 1-5, term short|long, conflictsWith[]}], schedule[{day, where, doing}]}` and World schedule "Character plan" entries; advanced by story days only.

## Functions
| Function | Returns |
|---|---|
| `chRelationships(se)` | directional records |
| `chEvolve(se)` | `{ok, applied}` (runs automatically; safe to call again) |
| `chHistory(se, a, b)` | `[{event, t, change, why}]` for A's view of B |
| `chLabel(record)` | label text |
| `chJournal(se, name)` | `[{t, kind, text, role: did|witnessed|learned|believes|rumor|feels|intends, source, playerKnows}]` |
| `chNpcs(se)` | `{name: {goals, schedule}}` |
| `chAgenda(se, name, fromDay, toDay)` | `{name, where, doing, goals (by priority), tensions, commitments, developments[{day, text}]}` (pure; opening a screen never advances anything) |
| `chCheckVoice(se, text)` | `[{kind: voice|growth|mood, name, text}]` (advisory) |
| `chSetRelationship(se, a, b, {trust, affection, respect, familiarity, rivalry, kinds, private, knownBy})` | `{ok, applied, reason}` |
| `chUndo(se)` | `{ok, applied, reason}` |
| `chAgendaLog(se)` | `[{day, name, text, tid}]` off-screen developments still valid |
| `chStoryDay(se)` | current story day |

## UI (ChatGPT)
Relationship web (directional arrows, labels, history on tap), character journal, NPC agenda view, and voice warnings in the Continuity Center (`ai.voice` next to `ai.ffc`).

Player-recorded development notes (justify growth): `se.chDev[name] = [text]`; memory character state `development` and `mood` are also used.
