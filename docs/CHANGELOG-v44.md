# v44: a code check that only allows people the reply actually names

## Why
The v43 replay ran 11 repair requests with `"effort"`. All 11 came back usable in 2.3–3.5 s, using about 720–815 input / 160–300 output tokens. Claude reviewed every entry of all 11 against the story text, checking key terms and reading passages where it mattered:
- **Fully supported:** 27, 41, 51, 55, 57, 69, 71, 79. That includes 55, where the stranger is now recorded as unknown instead of the earlier "Vey Calder" guess.
- **53:** the location "manor hall" isn't stated, but the reply continues straight on from the hall scene in 51. That's acceptable continuity.
- **45:** Brother Aled is listed as a witness and as present, but he doesn't appear in this reply. That came from the "scene before" hint. Unsupported.
- **63:** "the sexton-coated man" is named as Vey Calder. Nowhere in the story is that man linked to Vey. Unsupported.

So 2 of 11 replies still had unsupported entries, and the prompt rules alone didn't reach the target of none.

## Change
- **New `repairFilter()`.** It runs on every repair before anything is recorded, and on replays too.
  - A proper name (Vey Calder, Lady Orla) is kept only if its first name appears in that reply's own text. Titles like Brother and Lady are skipped, and a surname alone ("Calder crates") isn't enough.
  - A lower-case description ("the fire boy") needs any one of its words to appear.
  - The player character is always allowed.
  - Words are matched on their own, so line breaks and hyphens don't hide a name.
  - Labels such as "unknown man", "an unnamed …" or "someone" are dropped.
  - What was dropped is recorded in `rp.dropped`.
- VER is now 44 and the cache is now `sf-v44`.

## Checked on the real replies (no new requests)
- Running the filter over the 11 stored v43 blocks dropped exactly the unsupported people: Brother Aled from 45 and Vey Calder from 63.
- It also dropped the labels "unknown man" (55) and "an unnamed man coiling rope" (69).
- It removed nothing that was supported. The first version did wrongly drop names that came right after a line break; that's fixed, and the regression test covers it.
- **Result:** 0 of 11 replies have unsupported people.
- **Still a weak spot:** the 53 location is carried over through continuity rather than stated.

## Tests
- `tests/repair_v41.py` now has 22 checks, including three name-check tests. One is ChatGPT's "Calder crates" case: a surname alone must not let Vey Calder through.
- The full `run_all.py` suite passes.

## Next (needs Anna's approval)
- A 40-turn run with repair on and `ocLite: "effort"`.
- Report native and repaired metadata separately, with what was dropped.
