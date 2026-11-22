# v39: put the key template in the last message (option B), replacing the v38 reminder

## Why
In the v38 10-turn run, with the stronger reminder as the only change, 4 of 11 replies had metadata (all with the marker) and 7 had none. v37 had 6 of 11. The reminder didn't help.

Replies without metadata were not cut off. They had 332–474 output tokens compared with 753–1851, and similar prose length (207–294 words).

ChatGPT and Claude agreed to try option B next: show the actual keys next to the instruction, which costs no extra request.

## Change
- Each story turn's final note now ends with the exact list of keys expected for that turn. The list is copied from the same turn's system instructions, so it always matches (STATS, CAST, BONDS, EVENTS, NEXT and so on):

  (Reply as instructed. After the story text, always finish with this block, one line per key, in the formats from your instructions. Write none where nothing changed:
  [[META]]
  STATS: …
  …
  NEXT: …)

- **Safety net:** if the model copies a placeholder literally, a value of "…" or "..." is now treated as empty, both in `applyMeta` and in the memory engine's `NONE` pattern.
- VER is now 39 and the cache is now `sf-v39`. The parser is the same as v37.

## Target for the next 10-turn run (needs Anna's approval)
- At least 9 of 11 replies with metadata.
- 0 metadata lines visible in the story.
- No invented events or knowledge.
- Compare with v37 (6 of 11) and v38 (4 of 11).

If more than 2 of 11 still come back without metadata, test option A separately: one repair request per missing reply, no retry, and carry on normally if the repair fails.

## Tests
The full `run_all.py` suite and the memory unit tests pass.
