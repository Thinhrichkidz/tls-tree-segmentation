# v5c (28 Oct 2026): changes against v5b

All 15 validation checks pass. Height VALID 75 -> **79** (027, 035, 055, 114), REVIEW 88 -> 84. No tree got worse.
`ITSMe_all163_results_previous_*.xlsx` in this folder is the first post-processing pass, before code change 2; use `ITSMe_all163_results.xlsx`.

## Code changes
1. User height notes: `results/HEIGHT_USER_REVIEW_20261028/user_height_review.csv`. tree_090: top cut off by the dataset,
   height is a lower bound; stays REVIEW, no further cleaning.
2. Edited clouds: the reason "cloud edited after the inherited QC; ground at the stem foot not re-checked" is dropped when:
   - the top was re-checked on the current points, and
   - the stem axis, refitted on the edited points, meets the ground within 0.25 m of the foot.
   The foot ground test uses only the terrain mesh and classified ground, never the tree points, so an edit can only matter by
   moving the stem. Confirmed this way: 027, 035, 055, 082, 083, 094, 099, 114, 124.
   Not confirmable (reason kept): 045 (axis 0.36 m from the foot), 079, 137.

## Source clouds (baseline: session4_claude_20261028/state/, previous kept as CloudCompare_review_v2_v5b_baseline.csv)
| Tree | Edit | Result |
|---|---|---|
| 027 | Floating point removed | Height 19.367 -> 17.708 m. **VALID**. Crown volume 90.4 -> 63.2 m3 (REVIEW -> VALID). |
| 099 | Floating points removed | Height 19.991 -> 17.630 m. REVIEW (ground uncertain). Crown volume 248.8 -> 225.2 m3. |
| 083 | Floating point **still present** (716.44) | Height unchanged. The dense crown top fell from 713.13 to 712.24 m, so about 0.9 m of real top was removed. |
| 137 | Floating points **still present** (about 713.7) | Height unchanged. |
| 082 | Edited | Still 97.5 % one piece; height unchanged. |
| 100, 124, 078 | Not edited | Floating points / fragments still present. |

## Still open
- Floating points above the crown top (height too tall):
  - 100: 9.5 m;
  - 137: 8.8 m;
  - 124: 7.7 m;
  - 083: 4.2 m.
- Detached fragments: 078 (97.7 %), 082 (97.5 %).
