# v38: stronger end-of-turn [[META]] reminder (one change only)

## Why
The v37 confirmation run (10 turns, real DeepSeek V4.1 Flash through OpenCode Go, 2026-11-21) found these results across 11 replies:
- 6 replies had the marker and the metadata.
- 0 replies had the metadata without the marker.
- 5 replies had no metadata at all.

The 5 replies without metadata used fewer output tokens (427–697, compared with 706–976). Nothing was cut off; the model simply didn't write the block.

v37's display fix held: 0 of 11 replies showed metadata lines in the story. The first 40-turn run had 3 of 41 replies with no metadata, so the rate varies from run to run.

ChatGPT and Claude agreed to test a stronger reminder first. It's cheaper than a repair call, which would add an extra request on 30–45% of turns.

## Change
The note added to each story turn changes from:
"(Reply as instructed, then end with the [[META]] block.)"

to:
"(Reply as instructed. Then end your reply with the line [[META]] followed by the key lines. Never skip it, even for a short reply.)"

Also: VER is now 38 and the cache is now `sf-v38`. Nothing else changed: the parser is the same as v37, and the World Simulator setup note was not touched.

## Next test (needs Anna's approval)
Run the same 10-turn script with the same settings, with the reminder as the only difference.
- Compare how many replies have metadata (marked or markerless) against the v37 baseline of 6 out of 11.
- Confirm no metadata shows in the story.

If replies still often come back without metadata, test a repair call separately. It would extract only facts supported by the reply and must not invent events or knowledge.

## Tests
The full `run_all.py` suite passes.
