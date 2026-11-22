# v41: metadata repair (trial setting, off by default)

## Why
The v40 40-turn run had metadata in 30 of 41 replies. The first 13 replies all had it. All 11 misses came after the input passed about 8,000 tokens, even though each request carried 3 examples in its history.

ChatGPT and Claude agreed this meets the threshold for testing a repair request.

## Behaviour (only when `DB.metaRepair` is true; it's false by default and has no UI outside the trial page)
- **When it runs:** only when a story reply has no metadata at all. A block that is present but partly broken stays on the normal validation path.
- **The request:** one non-streaming request using the cheapest model (DeepSeek on OpenCode), up to 700 output tokens.
  - It has a deadline of `DB.repairWait`, 25 seconds by default.
  - There's no retry, and the Stop button cancels it.
  - If it fails, the turn continues as before.
- **What it may use:** the reply is the only evidence. The current scene and cast list are given only to work out pronouns and nicknames.
  - A LEARNED entry is allowed only if the reply shows the character found it out.
  - The model must write none rather than invent anything.
- **Allowlist:** only EVENTS, LEARNED and SCENE are kept. Anything else (NEXT, GOAL and so on) is dropped. If none of the three keys can be read, the repair counts as unreadable and nothing is recorded.
- **Bound to the exact reply:** the result is thrown away as stale if, before it returns:
  - the reply's text or selected version changed;
  - the session gained turns;
  - a branch was made.
- **Undoable:** a valid repair replaces that reply's empty memory change, so undo, delete and regenerate still work.
- **Kept out of the examples:** the repaired block is stored as `ai.rmt`, not `ai.mt`, so it is not sent back to DeepSeek as a history example. This keeps the trial measurement clean.
- **Diagnostics:** each turn records `rp = {ok, ms, tok, why}`. The trial report adds a "Missing blocks repaired" row so repaired and native results are reported separately.

## Trial page
- New checkbox: **Repair missing metadata** (trial setting).
- New button: **Replay repair on missed replies**. It needs `opencode` typed in the box. It runs the repair in dry mode on every reply from the finished trial that had no metadata. Memory isn't changed. The extracted block, timing and tokens for each reply are saved in the report, ready to review against the story text.

## Tests
- New `tests/repair_v41.py`, 16 checks:
  - off by default;
  - one request per missing block;
  - the prompt rules;
  - the allowlist;
  - kept out of the history examples;
  - undo;
  - unreadable replies, timeouts, stale results and Stop;
  - partial blocks not repaired;
  - dry replay.
- The full `run_all.py` suite passes.

## Next (needs Anna's approval)
1. Run the replay on the 11 missed replies from the v40 40-turn run: about 11 requests, roughly 0.3% of the 5-hour window. Review each repaired event, scene and learned fact against the story text, and report:
   - usable repairs;
   - unsupported entries;
   - failures;
   - time taken and tokens used.
2. If that looks good, do a full run with the setting on.
