# Trunk slices: independent DBH for trees in and near the field plot (29 Oct 2026)

Goal: get a DBH for the large trees the pipeline could not measure (leaning, oval, two trunks), and check the pipeline DBH independently. Read-only on `CloudCompare_review_v2/` and the v6 FINAL results; everything is written in this folder.

## Files
- `measure_trunks.py`: 10 cm slices at 1.2 / 1.3 / 1.4 m above each tree's pipeline ground, for the 51 TLS trees within 16 m of either plot centre (GPS centre or the north-up fit centre). It writes `trunk_slice_dbh.csv` and, for every result that is not a clean circle or differs from the pipeline by > 20%, an image in `slice_images/` (top view of the slice plus two side views).
- `ellipse_key_trees.py` -> `ellipse_key_trees.csv`: ellipse fits for the large trunks whose slice is a clean ring.
- `eye_check_verdicts.csv`: Claude's verdict on 19 of the 27 slice images. **Use this, not the automatic `slice_dbh_cm` column, for any flagged tree.**

## Results
1. **Method check.** On 17 clean, round, VALID trunks the slice DBH agrees with the pipeline: mean +0.6 cm, RMSE 0.9 cm, worst 2.5 cm. For clean round trunks the pipeline measures what is in the scan reliably. This is a check of the measurement, not of field accuracy.
2. **New DBH for large trees the pipeline missed or underestimated:**

| Tree | Shape at 1.3 m | Slice DBH | Pipeline |
|---|---|---|---|
| tree_163 | one trunk, leaning strongly | **about 85 cm** (ellipse short axis) | N/A |
| tree_079 | two separate trunks (user: twisted together) | **about 64 + 63 cm** (combined about 90 cm) | N/A |
| tree_103 | oval trunk, 96 x 64 cm | **about 78 cm** (area-equivalent) | 66.6 (circle, too low for an oval) |
| tree_074 | leaning about 30 deg, somewhat oval | 58-68 cm | 63.6 (consistent) |

   So the scan does contain trees of the size of the largest field trees (field: 107.5, 90, 83, 75.5 and 74.5 cm). Earlier comparisons lacked them because the pipeline gave these trees no DBH, or a circle DBH for an oval trunk.
3. **The automatic slice is not trustworthy where there is clutter.** Understorey, branches and shrubs around the stem inflate it badly (tree_095 104 cm vs about 35 cm; tree_133 97 cm with no trunk at all). In those cases the pipeline value is usually right. That is why every flagged tree was checked by eye.

## Not done / limits
- 8 flagged images (tree_080, 085, 086, 092, 106, 108, 117, 121; all small trees, under about 25 cm) were not checked by eye.
- The ground height is a fallback for tree_163 and some others, so "1.3 m" may be off by a few tens of centimetres. The slices from 1.2 to 1.4 m barely differ for the key trees.
- A leaning trunk's diameter is taken as the short axis of the horizontal slice. For a round trunk that is exact; for a leaning oval trunk (074) the true value lies between the short axis and the area-equivalent, hence the range.
- The field measured DBH 1.3 m along the stem; on a strongly leaning tree (163) that is lower in vertical height than our slice. The width hardly changes with height here, so the effect is small.
- None of these trees is matched to a field tag yet. That is step 2 (matching by small groups).
