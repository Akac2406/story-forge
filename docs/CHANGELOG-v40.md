# v40: show the model its own recent metadata in the history

## Why (cause found)
| Version | Replies with metadata |
|---|---|
| First 40-turn run (v36) | 38 of 41 |
| v37 | 6 of 11 |
| v38 (stronger reminder) | 4 of 11 |
| v39 (key template in the last message) | 3 of 11 |

The drop began with v37, the version that stopped metadata lines from showing in the story. From then on, the earlier replies in the conversation history sent to the model no longer contained metadata, so DeepSeek copied the pattern it saw and stopped writing it.

In the first run, the visible "leaked" lines had kept the pattern alive, which explains its 34 replies that had metadata without the marker. The prompt wording was never the cause.

## Change
- Each story reply's metadata block is now saved separately as `ai.mt`. The story text shown on screen still contains none of it.
- `mt` is kept with regenerated versions and follows version switching. If a regeneration fails, the earlier version's `mt` is restored.
- When building the history for the model, the last 3 replies are sent with their own metadata attached. Older replies are sent as plain text, which keeps the extra tokens small (about 3 × 150).
- "The last 3 replies" means the last 3 that have metadata, so the examples never run out even after a few misses.
- Diagnostics record `hm`, the number of earlier metadata blocks each request carried, so we can see whether misses cluster when there are none.
- The v39 key template in the last message stays. VER is now 40 and the cache is now `sf-v40`.

## Tests
- New `tests/history_meta_v40.py`, 8 checks:
  - the last 3 replies carry their own metadata and older replies don't;
  - stored text stays clean, and nothing shows in the story;
  - regenerating and switching versions keep the right metadata;
  - after a version switch, the request includes only the selected version's metadata, with no duplicates;
  - `hm` is logged.
- The full `run_all.py` suite passes.

## Next (needs Anna's approval)
- Run the same 10-turn test.
- **Target:** at least 9 of 11 replies with metadata, 0 visible in the story.
- **One caveat:** if the opening reply has no metadata, there is nothing to show the model at first. The v39 template covers that case.
