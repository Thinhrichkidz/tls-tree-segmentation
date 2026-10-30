# Field check sheet (12 trees)

Built from `ITSMe_all163_output_v6_FINAL_20261028` with `measurement_pipeline/scripts/field_check_sheet.py` (read-only on the results).

- `FIELD_CHECK_SHEET.xlsx`: print the "Field sheet" tab and fill in the FIELD columns. The "Instructions" tab says how to measure.
- `field_check_trees.csv`: the same table.
- `field_check_map.png`: plot layout, with the sample trees numbered.
- Plot SW corner: E 261323.4, N 6264444.9 (EPSG:32756), about -33.73320, 150.42382 (WGS 84).

## Selection
1. Five trees with all four core values VALID, spread over DBH (smallest, quartiles, median, largest): tests the core results.
2. Three trees with an ESTIMATED DBH, one per method (v4 pooled fit, v4b small-stem floor, v4b RANSAC), the median-DBH tree of each: tests the estimates.
3. tree_100 and tree_124: heights fell 9.5 m and 7.7 m after floating points above the crown were removed: tests that cleaning.
4. tree_095: DBH 36.7 cm with dense understorey round the stem base (repo README issue 7, resolved by slice plots): tests the clutter case (counted once if already chosen in group 1).
5. Two trees with a measured DBH whose height is REVIEW for ground uncertainty, with the largest difference between the two ground references: tests the height uncertainty.

## Trees
1. **tree_149**: all four core values VALID (DBH 13.4 cm, smallest of those trees)
2. **tree_065**: all four core values VALID (DBH 18.0 cm, 25th percentile of those trees)
3. **tree_144**: all four core values VALID (DBH 21.2 cm, 50th percentile of those trees)
4. **tree_095**: all four core values VALID (DBH 36.7 cm, 75th percentile of those trees)
5. **tree_103**: all four core values VALID (DBH 66.6 cm, largest of those trees)
6. **tree_014**: ESTIMATED DBH 18.4 cm (v4 pooled fit); DBH column N/A
7. **tree_096**: ESTIMATED DBH 11.9 cm (v4b small-stem RMSE floor); DBH column N/A
8. **tree_112**: ESTIMATED DBH 19.3 cm (v4b hollow-trunk RANSAC); DBH column N/A
9. **tree_100**: height fell 9.5 m after floating points above the crown were removed (now 17.28 m)
10. **tree_124**: height fell 7.7 m after floating points above the crown were removed (now 13.41 m)
11. **tree_136**: height REVIEW: ground uncertain (the two ground references differ by 0.71 m)
12. **tree_016**: height REVIEW: ground uncertain (the two ground references differ by 0.55 m)
