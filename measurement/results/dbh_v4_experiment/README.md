# DBH v4 experiment (28 Oct 2026)

Side-by-side test of a new DBH method on the saved v3 inputs. **v3 is untouched**; nothing here is merged into the v3 workbook.

Scripts: `scripts/dbh_v4.R` (method), `scripts/run_dbh_v4.R` (all 163 trees vs v3), `scripts/holdout_dbh_v4.R` (accuracy test).

## Method
Instead of one 6 cm slice at 1.3 m, pool the lean-corrected points from 1.1-1.5 m, crop to the radial-histogram stem radius (+0.10 m),
fit a circle with a Huber loss and a weak centre prior, trim points more than 2.5 robust SD from the surface and refit.
Gate: pooled arc >= 0.40 (v3: 0.60 on one slice), >= 25 inliers, 5-160 cm, RMSE <= v3 limit, per-slice radii within 15 %,
radius within max(3 cm, 25 %) of the radial histogram. Trees with no stem axis assume a vertical axis through the stem foot.
Result tier would be ESTIMATED (never VALID).

## Results on 163 trees
- v3 has a DBH for 80 trees. v4 passes its gate on 96: 68 of those 80 plus 28 trees v3 left empty. Total coverage 80 -> 108 if v3 values are kept where v4 does not pass.
- Where both exist (gate ok, n = 68): median difference 1.35 %, 90th percentile about 5 %, largest 19.8 % (tree_081).
- 55 trees still have no value. Largest cause: RMSE above limit (44 trees; clutter, forks or non-circular stems), then arc below 0.40 (7).
- Ones to look at first: tree_057 and tree_142 (no axis, vertical assumed), tree_081 (20 % off v3).

## Hold-out accuracy (66 trees with a clean full-arc v3 value, part of the stem hidden)
| Visible arc | Gate pass | v4 median abs error (passed) | v4 90th pct (passed) | plain circle median / 90th |
|---|---|---|---|---|
| 270 deg | 84 % | 1.7 % | 5.3 % | 2.4 % / 10.3 % |
| 180 deg | 62 % | 3.8 % | 11.6 % | 6.5 % / 26.7 % |
| 120 deg | 6 % | 14.3 % | 19.4 % | 26.3 % / 55.4 % |

So a v4 value from about half a circle is typically within 4 % but can be 12 % off; below about a third of the circle the gate correctly rejects.
This is a test against v3 itself, not field data. Tape/caliper measurements are still the only real accuracy check.
