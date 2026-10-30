# DBH v4b: fallbacks for the user-reviewed NORMAL trees (28 Oct 2026)

Input: your CloudCompare review of the 43 trees that failed on fit RMSE (`results/DBH_USER_REVIEW_20261028/user_dbh_review.csv`):
12 POOR_DATA, 3 SPECIAL (026, 097 missing sections; 163 leaning), 28 NORMAL. v4b values are released only for NORMAL trees.

Pipeline run: `results/ITSMe_all163_output_v4b_DBH_20261028/` (15/15 checks pass; v3 values unchanged).

## Two fallbacks (scripts/dbh_v4.R)
1. **Small-stem RMSE floor.** With ~3 cm point spacing, ~1.5 cm surface noise is normal, so "RMSE <= 10 % of diameter" is too strict
   for thin stems. With pooled arc >= 0.70 the limit becomes at least 2 cm. Against v3: n 58, median 1.2 %, 90th pct 3.8 %.
2. **RANSAC trunk circle.** Finds the circle most band points lie on, but only counts circles that are hollow (<= 10 % of
   points inside), because the scanner cannot see inside a trunk. Against v3: n 73, median 2.3 %, 90th pct 7.7 %.
   Largest misses are 067 (v3 used your outline filter) and 103 (oval trunk).
   Two earlier variants were rejected: plain RANSAC (tree_095 128 % too big) and an inside-point penalty (several 25-38 % too small).

## Result on the 28 NORMAL trees: 17 recovered
FLOOR: 052 11.5, 096 11.9, 106 14.1, 117 8.7 cm.
RANSAC: 042 29.2, 045 20.4, 062 14.2, 100 19.5, 104 19.4, 105 9.2, 109 19.2, 112 19.3, 136 15.8, 139 45.0, 140 13.6, 148 25.8, 153 17.3 cm.

Not recovered (11): 023, 030, 035, 039, 055, 094, 120, 121, 133, 137, 147 (too cluttered, too sparse, or slices disagree).

## Visual check (normal_trees_band_fits.png)
Top view of the 1.1-1.5 m band: grey = points, red dashed = v4 fit, blue = released v4b fit.
Doubtful from the picture: **105** (tiny ring next to a much larger point mass), **136** (ring inside dense foliage),
**139** and **045** (plausible ring but heavy clutter). The others sit on a clear hollow ring.
To reject a fit: put REJECT in the `v4b_decision` column of user_dbh_review.csv and rerun the post-processing; ACCEPT removes the
"visual check pending" note.
