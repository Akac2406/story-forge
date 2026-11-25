# OpenCode Go usage ledger (memory overhaul testing)

Budget (Anna, 2026-11-24): testing may take total monthly usage up to 45% (hard limit 50%). The 4% already used counts.
No Extra Usage, no purchases. Respect the 5-hour and weekly windows. If usage cannot be measured reliably, pause real-model testing.

Sources: **Dashboard** = Anna's OpenCode usage page (authoritative). **Estimate** = the trial page's `ocPct()` estimate.

| Date (MT) | Who | What | 5-hour | Weekly | Monthly | Source |
|---|---|---|---|---|---|---|
| 2026-11-24 | Claude | Phase 2 A/B (4 runs), earlier today | ~4.5% total | — | — | Estimate |
| 2026-11-24 | Claude | Separate-step A/B (4 runs + 1 stopped run) | ~5% total | ~2% | ~1% | Estimate |
| 2026-11-24 21:12 | Anna | Reading at authorization | 5% | 5% | **4%** | Dashboard (reported by Anna) |
| 2026-11-24 21:35 | Claude | Hybrid A/B: Cedar Ridge, hybrid on (30 turns, live v91 trial page) | 1.09% | 0.44% | 0.22% | Estimate |
| 2026-11-24 22:20 | Claude | Hybrid A/B: Glass Orchard, hybrid on (40 turns, live v91 trial page) | 1.80% | 0.72% | 0.36% | Estimate |
| 2026-11-25 02:20 | Claude | Hybrid + recall: Glass Orchard (40 turns, live v92/v93 trial page; resumed once at turn 31) | 1.94% | 0.78% | 0.39% | Estimate |
| 2026-11-25 03:30 | Claude | Hybrid + recall rerun on v94: Glass Orchard (40 turns; provider slow, ~2 min replies) | 1.60% | 0.64% | 0.32% | Estimate |
| 2026-11-25 04:10 | Claude | Hybrid + recall on v94: Cedar Ridge (30 turns) | 1.09% | 0.43% | 0.22% | Estimate |

Running total toward the 45% stop: **about 5.5%** monthly (4% dashboard + 1.51% estimate since). Next dashboard reading will replace the estimate.

## Results: Glass Orchard, hybrid + recall (2026-11-25)

| Check | Hybrid only (11-24) | Hybrid + recall (11-25) |
|---|---|---|
| Scene location | 24/25 | 25/25 |
| Characters present | 17/17 | 17/17 |
| Events recorded | 10/15 | 12/15 |
| Knowledge (exact / paraphrase) | 3/6 | 3/6 / 4/6 |
| No knowledge leaks | | 6/6 |
| Narrator kept secrets | | 30/30 |
| Narrator wrote [[META]] | | 28/40 (missed 17, 25-28, 33-36, 38-40) |
| Missing blocks repaired | | 38/40 |
| Regenerate / branch / cancel ops | | all ok; memory integrity ok; real stories unchanged |

Findings: (1) when the narrator skips its notes the hybrid step recovers events and scene but usually records LEARNED as none, which is where the knowledge misses come from; (2) misses snowballed because the history only showed narrator-written blocks, so recent turns had none: fixed in 94 (repaired blocks shown as examples); (3) a connector request hung for 20+ minutes (fixed in 94 with the stall watchdog) and once the trial wedged before turn 31 with no network activity (cause not found; resumed from saved progress).

## Results: Glass Orchard, hybrid + recall, v93 vs v94 (notes-history fix)

| Check | v93 | v94 |
|---|---|---|
| Narrator wrote [[META]] | 28/40 (misses in runs: 25-28, 33-36, 38-40) | 31/40 (misses scattered: 12, 18, 21, 26, 31, 32, 35, 36, 39; no run longer than 2) |
| Missing blocks repaired | 38/40 | 35/40 (memory steps hit the 90 s limit while the provider was slow) |
| Scene location | 25/25 | 23/25 (turn 21 "Lady Orla's room", turn 34 "the quay": wording, not wrong scenes) |
| Characters present | 17/17 | 17/17 |
| Events recorded | 12/15 | 14/15 |
| Knowledge (exact / paraphrase) | 3/6 / 4/6 | 5/6 / 5/6 |
| No knowledge leaks (memory) | 6/6 | 6/6 |
| Narrator kept secrets (text check) | 30/30 | 29/30 (turn 35: a character guesses "in Corwin's own desk, I'd wager"; speculation, flagged by the keyword check) |
| Regenerate / branch / cancel, integrity, real stories untouched | ok | ok |

Conclusion: the fix stops the snowballing (no long streaks of missing notes) and the knowledge score improved from 3/6 to 5/6. One run each, so treat the size of the gain as indicative.

## Results: Cedar Ridge, hybrid only (v91) vs hybrid + recall (v94)

| Check | Hybrid only | Hybrid + recall, v94 |
|---|---|---|
| Scene location | 27/30 | 27/30 |
| Characters present | 23/24 | 24/24 |
| Events recorded | 16/19 | 18/19 |
| Knowledge (exact / paraphrase) | 1/4 | 2/4 / 3/4 |
| No knowledge leaks | | 4/4 |
| Narrator kept secrets | | 25/25 |
| Narrator wrote [[META]] | | 25/30 (misses 12, 13, 23, 25, 29) |
| Missing blocks repaired | | 30/30 |
| Regenerate / branch / cancel, integrity, real stories untouched | | ok |

Both stories improve with recall on v94; knowledge capture is still the weakest area (exact keyword checks are strict). Recommendation: make recall + the notes-history fix the default for hybrid stories after one more confirming run, and look at LEARNED extraction in the hybrid step (it records "none" too often when the narrator skips its notes).
