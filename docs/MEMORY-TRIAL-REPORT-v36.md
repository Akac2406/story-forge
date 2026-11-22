# Memory engine trial: v36 report

> ## ⚠️ No real-model testing has been done yet
> Every result in this report comes from **automated simulations** with a scripted stand-in model. **No OpenRouter calls were made.**
> - The build workspace can't reach openrouter.ai: the network proxy refused the connection, even for the free model list.
> - Real calls also need your API key and your approval of the cost.
>
> The harness is ready for you to run the **live** trial on your own computer (see "How to run the real-model trial").

## 1. What was built

| Item | What it does |
|---|---|
| **Development-only memory mode** | `memDevEnable(sessionId)` turns memory on for **one** playthrough by setting `se.memv2` and `se.memDev`. It works only on `localhost`/`127.0.0.1`, or with `?dev=1` in the address. Elsewhere it refuses and changes nothing. `DB.memv2` (global) is never touched. The harness checks it is still `false` at the end of every run. |
| **Per-turn diagnostics** | While memory is on for a story, each reply appends one record to `se.memDiag` (capped at 300): whether the META block and each key were present, valid and total entry counts, whether a list was split over several lines, specific issues (for example `EVENTS #2: has 4 of 6 fields`), any parser exception, and the first 1,500 characters of the META block. **Recording never interrupts the story.** A parser error is logged and the reply is kept. |
| **`SFMemory.validateMeta(raw)`** | A read-only checker used by the diagnostics. It never changes what is stored. |
| **Trial scenario** (`tests/realmodel/scenario.json`) | An original 40-turn story, *The Glass Orchard*, with no private data. Five characters, one central secret, six locations, a promise, a death, a betrayal and a confession. Each turn lists the expected location, who should be present, events, who should learn the secret, and who must **not** know it yet. |
| **Trial harness** (`tests/realmodel/run_trial.py`) | Plays the scenario in a **fresh, throwaway browser profile** on a private local port. It runs a regenerate test (2 extra versions, then back to version 1), a branch test and a cancellation test (budget pause) mid-story, then writes a Markdown and JSON report. `--mode sim` uses the stand-in model, and `--mode live` makes real calls (see §5). |
| **`tests/trial_sim_check.py`** | Runs both simulation profiles inside the normal test suite. |

### Parser fixes found by the simulation
1. **Bold keys** (`**EVENTS:** 2 | …`): the closing `**` stayed on the value, so importance became the default 3 and `** none` counted as a malformed entry. **Fixed**, with a unit test.
2. **Lists split over several lines** (a key on its own line, then bulleted or numbered entries): earlier versions read only the key's own line and lost the rest. **Fixed.** Lines are read up to the next `KEY:` line, and the diagnostics flag these turns as "recovered".
3. **Importance written as a word** (`high`, `critical`, `minor`…) used to fall back to 3. **Fixed** with a word-to-number mapping. Unknown words still fall back to 3 and are reported as malformed.

## 2. Simulated results (not real models)
The stand-in model has two profiles:
- **clean:** always well-formed.
- **messy:** deliberately makes the mistakes models commonly make. That means bold keys, lists split over lines, importance as words, missing fields, a missing SCENE (about 10% of turns), a missing META block (about 5%), restated earlier events, and **one deliberate knowledge leak** at turn 16.

| Check | clean | messy |
|---|---|---|
| META block present | 40/40 | 39/40 |
| EVENTS / LEARNED key present | 40/40 | 39/40 |
| SCENE key present and well-formed | 40/40 | 35/40 |
| EVENT entries well-formed | 24/24 | 22/27 (5 unrecoverable: missing fields or unknown importance) |
| LEARNED entries well-formed | 5/5 | 6/6 |
| Lists split over lines (recovered) | 0 | 5 |
| Scene location correct | 25/25 | 23/25 (both misses on turns with no SCENE line) |
| Expected characters present | 17/17 | 14/17 (all misses on turns with no SCENE line) |
| Expected event recorded | 15/15 | 15/15 |
| Expected knowledge recorded | 5/5 | 5/5 |
| No knowledge leaks | 6/6 | **5/6: the injected leak was caught** |
| Restated events stored twice | 0 | **0 of 4 injected** (de-duplication worked) |
| Regenerate ×2, then back to v1: memory identical | ✅ | ✅ |
| Branch keeps only earlier memory, original untouched | ✅ | ✅ |
| Cancel (budget pause): reply and memory intact, no request sent | ✅ | ✅ |
| Parser exceptions / failed replies / page errors | 0 / 0 / 0 | 0 / 0 / 0 |
| Memory integrity check | ✅ | ✅ |
| Global `memv2` still off | ✅ | ✅ |

**What this shows:** the app records, undoes and diagnoses memory correctly, and it survives badly formatted metadata without breaking the story.
**What it doesn't show:** how often DeepSeek or Gemini actually make these mistakes. Only the live trial can measure that.

## 3. Real-model results (LIVE, DeepSeek V4.1 Flash through OpenCode Go)
**One real run was made on 2026-11-21, 18:45–19:27 Mountain time.**
- **Where it ran:** the phone trial page, on Anna's Netlify site, in her Chrome (driven by Claude with her approval).
- **What it played:** 40 turns plus the opening, 2 regenerations, a branch, and a cancel.
- **Requests:** 81, all to her OpenCode connector, none to OpenRouter.
- **Estimated Go use:** 2.2% of the 5-hour window, 0.9% weekly, 0.4% monthly. That's higher than the 0.5–1% I predicted, because chapter recaps and memory upkeep also run on DeepSeek.
- **Real stories:** confirmed unchanged byte-for-byte. Memory stayed off globally.

### Main finding: DeepSeek usually leaves out the `[[META]]` marker line
| How each reply ended (41 replies) | Count |
|---|---|
| `[[META]]` marker plus key lines (expected format) | 4 |
| Key lines (CAST / EVENTS / LEARNED / SCENE / NEXT…) **without** the marker | 34 |
| No metadata at all | 3 |

- **Not cut off:** the metadata wasn't truncated. The 34 marker-less replies end with a complete NEXT line, and the 3 bare replies end on a normal sentence after 230–250 words (333–484 output tokens, well under the limit).
- **It wasn't lost before parsing either.** The lines were in the reply, but v36 (and every earlier version) only looks for the literal `[[META`. As a result:
  - the memory engine recorded nothing on those turns;
  - existing features (STATS, CAST, BONDS, suggestions and so on) were also skipped;
  - **the metadata lines showed up in the story text.**
- **This affects normal play, not only the memory trial.** Anyone using DeepSeek through OpenCode has probably seen "EVENTS: … SCENE: … NEXT: …" at the end of replies.

### Results as recorded by v36 (marker only)
- **Operations:** all passed. Regenerate ×2 then back to version 1 restored memory (3 versions). Branch kept only earlier memory and left the original untouched. Cancel before sending kept the reply and memory.
- **Per-turn checks:** mostly MISS, because 37 of 40 turns had no block the parser recognised.
- **Other:** 0 failed replies, 0 parser exceptions, 0 duplicate events, integrity OK.

### The same real replies re-read with the v37 parser (no new requests)
| Check | Result |
|---|---|
| Metadata found | 38/41 (93%) |
| EVENTS / LEARNED / SCENE keys present | 38 / 38 / 38 of 41 |
| EVENT entries well-formed | 96/97 (99%) |
| Scene location correct | 23/25 (92%) |
| Expected characters present | 13/17 (76%) |
| Expected events recorded | 15/15 (100%) |
| Expected knowledge recorded (keyword match) | 2/5. In the 3 misses the right character "learned" something, but phrased without the word "water". |
| No knowledge leaks | 6/6 (100%) |

- **Location misses:** turn 7 has the model in "Lady Orla's bedchamber" where the script says chapel. Turn 17 has "the public quay on the delta" where the script says dock or river, which is arguably correct.
- **How the replay was done:** it ran in the browser on the stored replies. It scores each turn's parsed lines; it doesn't rebuild the full memory state, so treat it as a close estimate.

### Other observations
- **Slow chapter recaps:** they paused the story for several minutes on OpenCode. One pause before turn 19 lasted about 7 minutes. 5 of 10 chapter recaps failed twice and were skipped.
- **Run time:** the whole run took 41 minutes, not the 15–25 I estimated.

### v37 confirmation run (LIVE, 10 turns, 2026-11-21, about 20:05 Mountain time)
- **Run:** 10 turns plus the opening, 0 failed replies, 13 requests, all to the connector. About 0.1% of the 5-hour window was used.
- **Safety:** real stories unchanged, memory off globally.
- **Metadata across 11 replies:** marked 6, markerless 0, missing entirely 5.
- **Display fix:** 0 of 11 replies showed metadata lines in the story. Suggestions were read, and 13 events were recorded.
- **Knowledge:** turn 10 knowledge was correct on both the exact-keyword and paraphrase checks, with no leaks.
- **Recaps:** the recap deadline was reached while one recap was pending, and the story did not stall.
- **What's next:** see CHANGELOG-v38.md for the reminder being tested.

### v38 run (LIVE, 10 turns, 2026-11-21, about 20:20 Mountain time)
- **What changed:** only the stronger reminder.
- **Metadata across 11 replies:** marked 4, markerless 0, missing 7. That's no improvement on v37's 6 of 11.
- **Display fix:** 0 of 11 replies showed metadata lines in the story.
- **Run:** 13 requests, all to the connector, about 0.1% of the 5-hour window.
- **Safety:** real stories unchanged, 0 failed replies.
- **Next:** v39 (see CHANGELOG-v39.md).

### v39 run (LIVE, 10 turns, 2026-11-21, about 20:35 Mountain time)
- **What changed:** the key template in the final message.
- **Metadata across 11 replies:** marked 3, missing 8.
- **Display:** 0 metadata lines shown in the story, and no "…" placeholders were stored.
- **Run:** 13 requests, all to the connector, about 0.1% of the 5-hour window.
- **Safety:** real stories unchanged, 0 failed replies.
- **Diagnosis:** the cause is history imitation, not prompt wording (see CHANGELOG-v40.md).

### v40 run (LIVE, 10 turns, 2026-11-21, about 20:55 Mountain time): target met
- **Metadata across 11 replies:** marked 11, markerless 0, missing 0.
- **Keys:** EVENTS, LEARNED and SCENE were present in all 11 replies, with 0 validation issues.
- **Earlier metadata blocks sent with each request (`hm`):** 0, 1, 2, then 3 for every request after that.
- **Display:** 0 metadata lines visible in the story, and no placeholder values stored.
- **Memory:** 20 events and 16 facts recorded. Suggestions were read.
- **Checks:**
  - scene location 7/8;
  - characters present 4/5;
  - expected events 4/4;
  - knowledge 1/1 on both the exact-keyword and paraphrase checks;
  - leaks 0 of 2.
- **Run:** 13 requests, all to the connector, about 0.14% of the 5-hour window.
- **Safety:** real stories unchanged, memory off globally, 0 failed replies.
- **Comparison (replies with metadata):** v37 6/11, v38 4/11, v39 3/11, v40 11/11.
- **Decision (Claude + ChatGPT):** v40 is the baseline. Keep the template, and leave the repair call unbuilt.
- **Next:** a full 40-turn run with regenerate, branch and cancel. It should also:
  - review the scene misses against the story text;
  - check that the metadata sent back comes only from the selected version and the active branch, and never from cancelled or superseded replies.

### v40 full run (LIVE, 40 turns, 2026-11-21, 21:02–21:14 Mountain time)
- **Run:** 63 requests, all to the connector, about 1.2% of the 5-hour window. The recap deadline kept it to 11 minutes, compared with 41 for the first run.
- **Safety:** real stories unchanged, memory off globally, 0 failed replies, integrity OK, 0 duplicates.
- **Operations:** regenerate, branch and cancel all passed.
- **Payload audit:** of 43 story requests, every metadata example sent back came from the currently selected reply version, and none from superseded or cancelled replies.
- **Metadata across 41 replies:** 30 present (29 marked, 1 markerless) and 11 missing.
  - Replies 0–12 were all present.
  - All misses came after the input passed about 8,000 tokens, with 3 examples in history.
- **Display:** 0 metadata lines visible in the story, and no placeholder values stored.
- **Accuracy:**
  - location 19/25;
  - characters present 9/17;
  - events 12/15;
  - knowledge 4/5 on both the exact-keyword and paraphrase checks;
  - leaks 0/6.

  Several of the misses fall on turns with no metadata, where the scene simply carried over from the previous turn.
- **Next:** the metadata repair trial (see CHANGELOG-v41.md).

### v44 full run with repair on (LIVE, 40 turns, 2026-11-21, about 22:40 Mountain time)
- **Run:** 66 requests, all to the connector, about 1.5% of the 5-hour window. 0 failed replies, integrity OK, 0 duplicates.
- **Operations:** regenerate, branch and cancel all passed.
- **Payload audit:** of 43 story requests, 0 metadata examples came from superseded or cancelled replies.
- **Disconnect:** Chrome disconnected right at the end, so the trial page's final summary step didn't run. The results were read from the stored trial state afterwards.
- **Metadata across 41 replies:**
  - The model wrote it itself in 22; 19 were missing.
  - Repairs: 19 tried, 18 applied in 2.2–3.7 s each, 1 stale (the opening reply; a trial-timing artifact).
  - **Combined coverage: 40 of 41.**
  - 0 metadata lines visible in the story.
- **Removed by the name check:** "an unnamed man" (reply 5), plus Brother Aled and "servants" (reply 53), who don't appear in that reply.
- **Accuracy:**
  - location 21/22;
  - characters present 12/13;
  - events 10/11;
  - knowledge 2/3, exact and paraphrase;
  - leaks 0/5.

  That's better than the v40 run (19/25, 9/17, 12/15).
- **Review of all 18 applied repairs against the story text:**
  - 0 unsupported people and 0 unsupported facts.
  - One minor issue: an ambient event in reply 5 lists the people present as participants.
  - 14 of 18 locations are stated in the reply. The other 4 are carried over, but match the details in the reply.
- **New observation:** the model wrote its own metadata in only 22 of 41 replies (30 of 41 in the v40 run). The opening reply had none, and repaired blocks are kept out of the history, so the early turns had no examples to copy.
- **Next (agreed with ChatGPT, needs Anna's approval):**
  1. A run on a different story, with repaired blocks still kept out of history.
  2. Then an A/B test of a separate trial flag that uses one repaired opening block as a temporary history example until the model writes its own.

## 4. Recommended fixes
**Done in v37:** read metadata even when the marker is missing (see CHANGELOG-v37.md).

**Still to decide:** (a) a gentle prompt reminder to start the block with `[[META]]`, which is a prompt change and Anna's call; (b) make chapter recaps on OpenCode faster or time-limited; (c) loosen the trial's knowledge keyword check.

**Done in v36** (from the simulation): the three parser fixes above.

**To decide after the live trial:**
1. **Scenes go stale when SCENE is missing.** The scene simply stays as it was. If real models skip SCENE often, either (a) remind the model briefly when it's missing, or (b) infer the location from EVENTS `where`. Neither was done yet, because that would change the prompt and could overlap Phase 2.
2. **Malformed EVENTS entries are dropped.** Entries with missing fields are reported and skipped. If real models do this often, add a fallback that keeps the description when only the "where" field is missing.
3. **Knowledge leaks.** The engine records whatever the model says a character learned. Spotting impossible learning (a character who wasn't present) belongs to the continuity checks (design §4.10, Phase 6). The trial now measures this.
4. **Other META keys with bold formatting.** `GOAL:` and other keys handled by the existing `applyMeta()` can keep a leading `**`. This is cosmetic and outside the memory engine, so it was left unchanged for this phase.

## 5. How to run the real-model trial: DeepSeek through OpenCode (Windows)
**I didn't run it.** This workspace can't reach outside services, and it uses your subscription, so you start it yourself.
```powershell
cd story-forge-v36-memory-trial
pip install playwright
python -m playwright install chromium
$env:OPENCODE_API_KEY = "your OpenCode key"                       # this window only; never saved to a file
$env:STORYFORGE_CONNECTOR = "https://your-connector.workers.dev"   # the same address as in the app's Settings
python tests\realmodel\run_trial.py --mode live --provider opencode --max-pct 10
Remove-Item Env:OPENCODE_API_KEY; Remove-Item Env:STORYFORGE_CONNECTOR
```
- **Confirmation:** it shows the plan and asks you to type `opencode` before the first request.
- **Usage cap:** it stops if the estimated **5-hour Go limit** use reaches `--max-pct` (default 10%). A 40-turn run should use roughly **0.5–1%** of the 5-hour window. The estimate uses the app's default allowance setting in a fresh browser profile, so compare it with the Usage page in your OpenCode console afterwards.
- **Connector access:** if you changed `ALLOWED_ORIGIN` in your Worker from `*` to your Netlify address, the trial's local address (`http://127.0.0.1:8830`) will be blocked. Use `*` for the duration of the trial, or add that address.
- **What's sent:** only DeepSeek, through your connector, for the story turns, 2 regenerations, and the app's own background memory upkeep. The report lists requests by destination, so you can confirm none went to OpenRouter.
- **Keep in mind:** OpenCode describes Go as meant for coding agents. One 40-turn run is about one normal play session, but avoid running it many times in a row.
- **Privacy:** reports go to `tests\realmodel\reports\`. The key and the connector address are replaced with `[REDACTED]` and `[CONNECTOR]`. The report includes only the test story's text and META.
- **Your real app and saved stories are safe.** The trial runs in a separate temporary browser profile on its own local port.

Send me the `.md` and `.json` report from `tests\realmodel\reports\` and I'll analyze the results and recommend fixes.

## 5a. Running the trial on your iPhone (no computer needed)
The app folder now includes a trial page, `memtrial.html`. The app itself is unchanged (`index.html` is byte-identical to v36).

1. Deploy the `story-forge-pwa` folder to your Netlify site as usual. Include the new `memtrial.html`, `memtrial.js` and `trial/` folder.
2. In Safari, open `https://<your-site>/memtrial.html`. The page isn't linked from the app and is hidden from search engines.
3. Do the **dry run** first (ticked by default only if no key is found). It's free, sends nothing, and takes about a minute.
4. Untick Dry run and type `opencode` to confirm. Keep Safari open with the screen on for about 15–25 minutes. The page asks iOS to keep the screen awake.
5. If it's interrupted (you switch apps or the phone locks), reopen the page and tap **Continue the unfinished trial**.
6. When it finishes, tap **Share report**. It sends a `.md` and a `.json` file, which you can send to me.
7. Afterwards, tap **Delete trial data** to remove the test copy.

How it keeps your stories safe:
- It runs a separate copy of the app with renamed storage (`sf-trial-db` and the `sf-trial` database) and no service worker.
- It only reads your OpenCode key and connector address from your settings.
- At the end it confirms your real data is byte-for-byte unchanged and shows the result in the report.
- Memory is turned on only for the test story. The global setting stays off.
- It uses the same safeguards as the PC harness: OpenCode/DeepSeek only, a usage cap on this trial's estimated share of the 5-hour Go limit (default 10%), requests counted by destination, and the key and connector address redacted.
- **Connector:** the page runs from your Netlify address, so your Worker's `ALLOWED_ORIGIN` setting already permits it. There is no need to change it to `*`.

Tested here on an iPhone-sized Chromium screen (not a real iPhone, not real DeepSeek): `tests/phone_trial_check.py`, 27/27. That covers:
- the dry run;
- a full run against a stand-in connector, with only `deepseek-v4.1-flash` sent to the connector and none to OpenRouter;
- the confirmation gate;
- interrupting and resuming;
- deleting the trial data;
- checking that the real localStorage and IndexedDB were byte-identical.

## 6. Test results for this build (simulations and regression)
See `TEST-RESULTS-v36.md`.
