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

Running total toward the 45% stop: **about 4.6%** monthly (4% dashboard + 0.58% estimate since). Next dashboard reading will replace the estimate.
