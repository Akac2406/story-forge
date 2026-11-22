# v43: stricter repair rules, and "unknown" never overwrites what's known

## Why
- **Probe (3 requests, the same prompt on reply 41):**

  | Setting | Time | Tokens (in / out) | Result |
  |---|---|---|---|
  | No switch | 24.6 s | 692 / 2,700 | usable but thin |
  | `reasoning_effort: "none"` | 2.7 s | 666 / 206 | usable |
  | `thinking: disabled` | 2.8 s | 666 / 248 | usable |

  Both switches are accepted and clearly take effect. `"effort"` was chosen.
- **11-reply replay with `"effort"`:** 11 of 11 returned a usable block, in 2.4–4.2 s, using 646–743 input / 191–334 output tokens.
- **Manual review of 4 replies (27, 41, 45, 55):**
  - Replies 27 and 41 were fully supported by the story text.
  - Reply 45 had all its events supported, but SCENE carried over "manor hall" when the reply reads like Orla's sickroom.
  - Reply 55 had 2 events and its LEARNED entry supported, but one event named Vey Calder when the story text only says "a man's boots crossed and re-crossed". That's an unsupported attribution.

## Changes
- **New repair rules:**
  - Name a character only when the reply names them or clearly identifies them. Otherwise write unknown, and never guess from the character list.
  - Keep the previous scene only if the reply clearly continues there. If the reply moves somewhere unclear, write unknown for the location.
- **Memory engine:**
  - `unknown` and `unclear` now count as empty, the same as "none". They're dropped from participant lists, and a LEARNED entry for "unknown" is ignored.
  - A SCENE with an empty or unknown location or time keeps the stored location and time, while "who's present" still updates. This applies to replies with their own metadata too, which is safer: an unclear location no longer erases a known one.
- VER is now 43 and the cache is now `sf-v43`.

## Tests
- New `tests/unknown_v43.mjs` (4 checks).
- The memory unit tests (19) and the full `run_all.py` suite pass.

## Next (needs Anna's approval), as agreed with ChatGPT
1. Re-run the 11-reply replay with `"effort"` (about 11 requests).
2. Review every entry by hand against the story text, aiming for no unsupported entries.
3. Then do a 40-turn run with repair on.
4. Use `ocLite` for chapter recaps only after that.
