# v4c (28 Oct 2026): changes against v4b

Run: this folder. All 15 validation checks pass; independent recalculation of 24 trees unchanged (height diff <= 5e-13 m).
Source baseline: `session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv` (previous session-3 snapshot kept unchanged;
see `session4_claude_20261028/state/BASELINE_CHANGE.json`). Only tree_045 and tree_139 changed; the other 161 hashes are identical.

## User decisions (results/DBH_USER_REVIEW_20261028/user_dbh_review.csv)
- tree_105: v4b RANSAC fit (9.2 cm) REJECTED - looks like two trees sharing one trunk.
- tree_136: v4b RANSAC fit (15.8 cm) REJECTED - ring sits inside dense foliage, not the trunk.
- tree_045, tree_139: clouds re-cleaned in CloudCompare and rerun.

## Re-cleaned trees
| Tree | Points | DBH before | DBH now | New-method check on cleaned cloud |
|---|---|---|---|---|
| 045 | 29,820 -> 26,558 | N/A (estimate 20.4 cm RANSAC) | **18.9 cm, REVIEW** (median of 1.1-1.5 m slices) | RANSAC 18.6 cm |
| 139 | 145,352 -> 120,909 | N/A (estimate 45.0 cm RANSAC) | **45.9 cm, REVIEW** (v3 rule) | v4 44.9, RANSAC 44.6 cm |

Both now have a measured DBH in the DBH column, so their estimates were removed. REVIEW reasons: stem axis refitted on the
cleaned points and meeting the ground 0.36 m (045) / 0.42 m (139) from the inherited stem foot; inherited ground/QC flags not
re-checked after the edit.

Other changes for these two trees:
- tree_045 height: VALID -> REVIEW (value identical, 14.873 m) because the cloud changed after the inherited height QC.
- tree_045 crown: area 4.22 -> 2.32 m2, envelope 14.6 -> 2.4 m3 (cleaning removed crown points above the 9.75 m base).
- tree_139 height and crown values: identical.

## Totals
DBH column: 43 VALID, 39 REVIEW, 81 N/A (v4b: 43 / 37 / 83). Estimated DBH: 39 trees (26 v4, 9 v4b RANSAC, 4 v4b floor).
Measured or estimated DBH: 121 of 163 (v3: 80).
