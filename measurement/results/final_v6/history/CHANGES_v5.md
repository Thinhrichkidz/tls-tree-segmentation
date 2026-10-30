# v5 (28 Oct 2026): height refinements, against v4e

Run: this folder (notebook `ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb`, new step 2b `scripts/height_refine_all163.py`).
All 15 validation checks pass. No source cloud changed. DBH and crown values unchanged.
`ITSMe_all163_results_previous_20261028_181143.xlsx` is the first post-processing pass. It was superseded after the change
check was extended to crown ratio, which follows the height. Use `ITSMe_all163_results.xlsx`.

## Result
Height: VALID 50 -> **71**, REVIEW 113 -> 92. No tree went from VALID to REVIEW.
REVIEW -> VALID (21): 047, 057, 071, 081, 085, 091, 104, 106, 112, 117, 120, 121, 125, 126, 129, 130, 131, 138, 147, 148, 161.

## Fix 1: top re-checked on the current points
The inherited top flag failed 38 trees only because a point was within 0.75 m of the terrain-mesh edge. That distance came
from screening before the manual cleaning; on the current points many of those trees have no point near the edge at all.
New rule, all on the current points:
- the tip is supported (unsupported points <= 0.2 m above it);
- the cloud is >= 98% one piece (inherited);
- the tip is >= 1 m from the edge;
- either no point is within 0.75 m of the edge, or all such points are >= max(2 m, 10% of height) below the tip.
Trees whose crown reaches the edge close to the tip stay REVIEW: 005, 062, 119, 128, 132, 135, 139, 159.

## Fix 2: stem foot under the trunk (18 trees)
For fallback-foot trees (foot = lowest observation), the foot is moved under the trunk. The source is the stem axis or the
DBH circle released for that tree. The inherited ground-reliability rule is then re-run at the new foot.
Height = ITSMe height - ground shift. The raw value is kept in the height note.

| Tree | Source | Ground shift | Height before -> after | Status |
|---|---|---|---|---|
| 023 | stem axis (1.40 m from old foot) | -0.170 | 20.158 -> 20.328 | REVIEW |
| 039 | stem axis | +0.202 | 11.580 -> 11.377 | REVIEW |
| 057 | v4 DBH circle | -0.021 | 12.828 -> 12.849 | VALID |
| 100 | v4b RANSAC circle | +0.080 | 26.883 -> 26.803 | REVIEW |
| 104 | v4b RANSAC circle | -0.147 | 24.733 -> 24.881 | VALID |
| 106 | v4 DBH circle | +0.084 | 11.066 -> 10.982 | VALID |
| 109 | v4b RANSAC circle | -0.034 | 15.571 -> 15.605 | REVIEW |
| 112 | v4b RANSAC circle | -0.016 | 16.479 -> 16.495 | VALID |
| 117 | v4 DBH circle | -0.050 | 10.302 -> 10.351 | VALID |
| 120 | stem axis (1.62 m from old foot) | -0.050 | 22.308 -> 22.359 | VALID |
| 121 | stem axis | -0.003 | 9.387 -> 9.390 | VALID |
| 136 | stem axis | -0.415 | 17.096 -> 17.511 | REVIEW |
| 139 | stem axis | +0.295 | 21.263 -> 20.968 | REVIEW |
| 140 | v4b RANSAC circle | +0.084 | 12.935 -> 12.851 | REVIEW |
| 142 | v4 DBH circle | -0.012 | 16.939 -> 16.952 | REVIEW |
| 147 | stem axis | -0.008 | 10.384 -> 10.392 | VALID |
| 148 | v4b RANSAC circle | +0.005 | 12.838 -> 12.833 | VALID |
| 153 | v4b RANSAC circle | -0.054 | 13.227 -> 13.281 | REVIEW |

Not moved (no stem axis and no released DBH fit): 001, 005, 030, 046, 097, 111, 133, 158, 163.
- 111 and 133: your bad-dataset decision.
- 163: leaning, so a vertical drop is wrong.
Effects of a moved foot on other values:
- Crown length is unchanged, because the crown base is still measured from the old ground; crown ratio follows the new height.
- Where the ground shifts by more than 10 cm (136, 139, 023, 039, 104), the DBH note states that the 1.3 m reference has moved.

## Remaining REVIEW reasons (92 trees; a tree can have several)
| Trees | Reason |
|---|---|
| 69 | Ground at the foot uncertain. Real: switching ground reference moves height by a median 0.22 m on these trees. |
| 22 | Tree top: crown reaches the edge near the tip, unsupported points above the tip, or the cloud is in pieces. |
| 9 | Fallback foot with no trunk position. |
| 7 | Highest point not supported. |
| 7 | Clouds edited today with a robust foot: top re-checked, ground at the foot not re-checked. |
| 3 | Stem axis meets the ground away from the foot. |
| 4 | Earlier visual or user notes. |
