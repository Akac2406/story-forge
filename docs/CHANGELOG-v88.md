# v88 — sturdier EVENTS parsing and trial-check fixes

Follow-up to the live DeepSeek V4.1 Flash memory trial (The Glass Orchard, 40 turns, 2026-11-24).

## Memory engine (`site/memory-engine.js`)
- New `splitEvents()` used by both `parseMeta` and `validateMeta`. It finds where each event starts
  (an importance followed by a kind, or a kind right after a witness field) instead of splitting on `;`.
  It now handles the mistakes the model made in the trial:
  - `;` written before the witnesses (used to create a fake one-field event);
  - witness `none` glued to the next event with its importance missing (used to give `importance "none"`);
  - events chained with `|` and no `;` (used to keep the first event and silently drop the rest while
    counting it as valid — about 9 events were lost this way);
  - a `;` inside a description (used to cut the description in half);
  - witness lists separated by `;`.
- Unknown kinds map to the nearest known kind (`clue` → reveal, `conflict` → threat, …).
- Repaired events are counted as "recovered" in diagnostics instead of malformed.
- SCENE "who" accepts `;` as well as commas.
- On the trial's own metadata: 57/58 events read correctly, up from 39/62.

## Narrator prompt (`site/index.html`)
- The EVENTS instruction now says every event starts with its importance, `;` goes only between events,
  and gives a two-event example.

## Trial page (`site/memtrial.js`, `site/trial/scenario.json`)
- Name matching skips titles, so "Brother Aled" matches "Aled" (all Aled checks failed before).
- Turn 39 now records that Corwin learns about the copy, which ends the secrets window; "Corwin read the
  copy twice" is no longer flagged as a leak.

## Tests
- `tests/memory_phase1_unit.mjs`: new case built from the trial's real separator mistakes (20 pass).
- `trial_sim_check.py`, `memory_phase2_v87.py`, `phone_trial_check.py`: pass.
