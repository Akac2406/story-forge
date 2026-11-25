# Gameplay API (roadmap phase 9)

Engine: `site/gameplay-engine.js` (global `SFGame`, pure, no model calls). App adapters in `index.html` (prefix `gm`). State lives per playthrough in `se.game`; nothing is stored until the first change. Off by default.

Every mutation returns `{ok, applied, reason, fired, result}`. `fired` lists consequence rules that triggered because of the change. Rejected changes never touch saved data. `gmUndo(se)` reverts the last change, including any consequences it caused.

## Settings

| Adapter | Notes |
|---|---|
| `gmState(se)` | Current game (defaults if none): `{enabled, seed, day, stats{}, xp, level, curve, quests[], rules[], fired[], career, log[]}` |
| `gmEnable(se, on)` | Adds or removes the GAMEPLAY STATE prompt section. `reason: "unchanged"` if already in that state. Disabling keeps the game. |
| `gmSet(se, {curve?, seed?})` | `curve: {base 100, growth 1.5, max 50}` controls XP per level. |
| `gmBlock(se)` | The prompt section text (empty when off). |
| `gmLog(se, n)` | Last n log entries `{kind, t, day, text}` (kinds: change, xp, quest, advance, fail, consequence, activity, career, rule, stat). |
| `gmUndo(se)` | Reverts the last change. |

## Stats, XP, quests, consequences

| Adapter | Notes |
|---|---|
| `gmDefineStat(se, {id, name, min=0, max=100, start=min, hidden?})` | Hidden stats are tracked but not shown to the narrator. |
| `gmChange(se, id, delta, why?)` | Clamped to min/max. `reason: "no change"` when clamped to the same value. `result: {id, delta, value}` |
| `gmXp(se, n, why?)` | `result: {level, up}` |
| `gmAddQuest(se, {id, title, steps: [string], reward?: {xp?, <stat>: delta}})` | Quests start active. |
| `gmAdvanceQuest(se, id, step?)` | Next step if `step` is omitted. Completing the last step applies the reward once. |
| `gmFailQuest(se, id, why?)` | |
| `gmAddRule(se, {id, when: {stat, op, value}, effect: {stats?, fail?, unlock?}, note?, repeat?})` | `op`: `<`, `<=`, `>`, `>=`, `==`. `stat` can also be `level` or `day`. Fires once when the condition becomes true; `repeat: true` re-arms it when the condition turns false. |

## Careers

| Adapter | Notes |
|---|---|
| `gmCareers()` | `[{id, name, stats[], ranks[], activities: [{id, name, needRank}]}]`. Built in: `idol`, `athlete`, `musician`. |
| `gmStartCareer(se, id, {custom?, seed?, start?})` | Adds the career's stats (start 20; stamina 80) and its first rank. One career per playthrough. `custom` takes the same shape as a built-in module: `{id, name, stats: [[id, name, min, max, start]], ranks: [{id, name, need: {stat: min}}], activities: {id: {name, gain: {stat: [lo, hi]}, cost: {stat: n}, needRank?}}}`. |
| `gmActivity(se, activityId)` | One week (7 story days). Gains are random within `[lo, hi]` but seeded: the same playthrough, week and activity always give the same numbers, so regenerating a reply never re-rolls results. Refusals: `needs rank <name>`, `too tired: rest first`. `result: {got: {stat: change}, rank, up}`; rank rises only when every requirement of the next rank is met. |

Idol module: stats Vocal, Dance, Rap, Visual, Variety, Stamina, Fans, Stress; ranks Trainee → Pre-debut (vocal 40, dance 40) → Rookie (vocal 55, dance 55, fans 5000) → Rising star (fans 50000) → Top idol (fans 500000, vocal 80, dance 80); activities vocal_lesson, dance_practice, rap_session, photoshoot, variety_show (Rookie), fan_meeting (Pre-debut), rest.

Competitions stay in the fanfiction engine (`ffRank`, `ffRecordCompetition`): recorded results are never re-rolled and are never automatic wins.

## Prompt

When enabled, the system prompt gets a GAMEPLAY STATE section: career and rank, visible stats, level and XP, active quests with progress, the last three consequences, and the rule "never invent wins, promotions or stat changes the game has not recorded".

Tests: `tests/gameplay_engine_unit.mjs` (28), `tests/gameplay_app_browser.py` (15).
