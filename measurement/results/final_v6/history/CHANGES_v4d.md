# v4d (28 Oct 2026): changes against v4c

All 15 validation checks pass; only the 10 re-cleaned trees changed. Source baseline updated in
`session4_claude_20261028/state/` (v4c baseline kept as CloudCompare_review_v2_v4c_baseline.csv; log in BASELINE_CHANGE.json).

## User decisions
- Re-cleaned at 1.0-1.6 m in CloudCompare: 023, 035, 039, 055, 094, 120, 121, 136, 137, 147.
- 030 and 133: dataset too poor to clean -> POOR_DATA.
- 105: fork below 1.3 m, not split -> DBH stays N/A.
- Note: tree_121_UNCHANGED.ply was edited; the filename was not changed.

## Re-cleaned trees
| Tree | Points | DBH now | Why no DBH (if none) | Crown change |
|---|---|---|---|---|
| 039 | 40,867 -> 36,511 | 12.0 cm, REVIEW (measured) | | volume 38.3 -> 35.2 m3 |
| 094 | 288,139 -> 250,394 | 28.1 cm, REVIEW (measured) | | none |
| 120 | 216,531 -> 135,674 | 40.4 cm, REVIEW (measured) | | **area 19.3 -> 14.3 m2, volume 248.6 -> 69.3 m3** |
| 136 | 358,193 -> 323,107 | 38.8 cm, REVIEW (measured) | | none |
| 121 | 85,979 -> 81,387 | 10.1 cm, ESTIMATED (v4) | | volume 38.1 -> 31.7 m3 |
| 035 | 74,937 -> 73,251 | none | slice radii inconsistent (all methods ~18.4 cm) | none |
| 055 | 52,584 -> 50,500 | none | slice radii inconsistent (~6.6 cm stem, too thin for 3 cm spacing) | none |
| 147 | 85,944 -> 77,886 | none | slice radii inconsistent / RMSE | volume 47.9 -> 41.0 m3 |
| 137 | 108,496 -> 70,756 | none | less than 60 % of the stem visible | none |
| 023 | 155,594 -> 151,295 | none | RMSE above limit; RANSAC arc too low | volume 305.2 -> 308.0 m3 |

tree_120 crown reduction confirmed intentional by the user (28 Oct 2026): removed points were not this tree's crown.

Height values are identical for all 10; 035 and 055 height status VALID -> REVIEW (cloud edited after the inherited QC).

## Totals
DBH column: 43 VALID, 43 REVIEW, 77 N/A. Estimated: 40 (27 v4, 9 v4b RANSAC, 4 v4b floor). Any DBH: 126 of 163 (v3: 80).
