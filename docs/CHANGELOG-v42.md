# v42: run the repair in the background; add a no-reasoning switch for testing

## Why
In the v41 replay, the repair worked on 1 of the 11 missing replies. The other 10 hit the 25-second deadline.
- The one that worked took 22.3 seconds and used 723 input / 2,403 output tokens. The block itself is about 150 tokens, so DeepSeek V4.1 Flash on OpenCode spent about 2,200 tokens on hidden reasoning.
- Its content was fully supported by the story text: the salt tide mark, scrubbed floor, Calder crates, greased bolt, river draft, cellar, night and Ilse all appear in the reply.
- The same hidden reasoning is the likely cause of the slow and failing chapter recaps.

## Changes (all still off by default)
- **The repair runs in the background after the turn.** The story appears immediately.
  - At most one repair per story is in flight at a time (`RPQ`).
  - The background limit is now 90 seconds (`DB.repairWait`).
  - The stale-result checks are unchanged. A late repair is never applied to a newer turn, a changed version or another branch.
- **New trial switch `DB.ocLite`, for OpenCode helper calls only (currently just the repair).** Story turns are never affected.
  - `"effort"` sends `reasoning_effort: "none"`.
  - `"thinking"` sends `thinking: {type: "disabled"}`.
  - Whether the gateway honours either one is not known yet; the probe will measure it.
- **Trial page:** before scoring a turn, it waits for that turn's pending repair.
- VER is now 42 and the cache is now `sf-v42`.

## Tests
- `tests/repair_v41.py` now has 19 checks. New ones:
  - the turn doesn't wait for the repair;
  - if the player moves on first, the repair is discarded as stale and the newer turn is untouched;
  - each `ocLite` mode is added only to the repair request, never to the story turn.
- The full `run_all.py` suite passes.

## Next (needs Anna's approval), as agreed with ChatGPT
1. **Probe, at most 3 requests:** run the same repair prompt on one reply that timed out, three ways:
   - with no switch;
   - with `"effort"`;
   - with `"thinking"`.

   Compare time taken, completion tokens, whether the request was accepted, and whether the block is usable and supported by the story. A request being accepted doesn't prove the switch took effect.
2. If one switch clearly cuts reasoning, re-run the 11-reply replay with it, then review each entry against the story text.
3. Only after that, consider using the same switch for chapter recaps.
