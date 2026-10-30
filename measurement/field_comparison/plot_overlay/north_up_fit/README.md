# North-up anchor fit (29 Oct 2026): best-supported placement, a PROPOSAL

> **Update (29 Oct, after trunk checks): two anchor pairs are probably wrong, and the "large trees about 30% low" result below is RETRACTED.** See "Trunk checks" at the end.

`north_up_fit_and_match.py` (read-only on inputs) is the anchor fit from `../anchor_fit/` with two constraints:
- rotation limited to +-15 deg, because the site map has a north arrow;
- tree_085 removed from the large-tree candidates, because the user checked it in CloudCompare (a thin stem with understorey).

Matching runs in two passes, following the professor's advice. First the 9 anchor trees (field DBH >= 50 cm) are matched among the 20 largest TLS trees, ranked by point count. Then the other field trees are matched among the stems that are left. Pairs are chosen by position only. DBH is recorded as a check, never used to choose a pair.

## Placement
- Map rotation -1.6 deg; plot centre 6.6 m south of the GPS centre (UTM 261365.71, 6264469.80).
- Stable: 15, 20 and 25 large-tree candidates give the same placement (within 0.25 m). With 30-40 candidates a placement to the north wins instead (`fit_summary.json`); that one puts tree_074 and tree_163 outside the plot.
- Agrees with the user's checks: tree_074 (a large single trunk) = 1439 (90 cm).

## Matches (`tree_matches.csv`)
- 6 confirmed, 8 probable, 12 unmatched.
- Anchor pairs:

| Field | Field DBH (cm) | TLS | TLS DBH (cm) | Diff | Class |
|---|---|---|---|---|---|
| 1439 | 90.0 | tree_074 | 63.6 | -29% | confirmed |
| 1448 | 83.0 | tree_069 | 51.7 | -38% | confirmed |
| 1447 | 51.3 | tree_060 | 56.3 | +10% | confirmed |
| 1432 | 51.4 | tree_098 | 34.8 | -32% | confirmed |
| 1435 | 75.5 | tree_103 | 66.6 | -12% | probable |
| 1455 | 74.5 | tree_132 | 32.0 | -57% | probable |

- Unmatched large trees: 1437 (107.5 cm), 1449 and 1450.

## Known contradictions (do not hide these)
- 1440 (14 cm Corymbia) is matched to tree_163, which the user says is a large leaning tree. That match is probably wrong. tree_163 may be 1437 (the largest field tree, unmatched, about 6 m from where the map puts it).
- 1446 (16 cm) is "probable" to tree_079, which the user says is two large trunks twisted together. Also probably wrong.
- So large TLS trees left over by the anchor pass can still be taken by small field trees. Treat any small-field-tree / large-TLS-tree pair as unmatched.

## DBH results
- RETRACTED (see Trunk checks): tree by tree (`dbh_tree_by_tree.csv`), confirmed matches with a measured TLS DBH: n = 5, bias -12.7 cm, RMSE 20.1 cm, median -29%. Two of the five pairs are probably wrong, so these numbers do not show a TLS underestimate.
- Distribution inside the fitted circle (`dbh_in_plot_distribution.csv`): 30 TLS trees, 20 with a measured DBH >= 10 cm; TLS median 28.0 cm against 32.5 cm in the field; upper quartile -32%; not statistically different (p = 0.48).
- Sample sizes are very small (5-11 trees), so these are indications, not accuracy figures.

## To make it firmer
The user confirms in CloudCompare: is tree_163 about 1 m thick at breast height (then it is 1437)? Are 069, 060, 098 and 103 large single trunks?

## Trunk checks (29 Oct)
User checks in CloudCompare (screenshots in chat): tree_079 is two trunks twisted together (cannot be separated); tree_163 is one large leaning trunk; tree_074 is one large trunk; tree_085 is a thin stem, not a large tree.

Claude then measured the trunks from the review clouds (`CloudCompare_review_v2/`, read-only), using 10 cm slices at 1.2-1.9 m above each tree's ground. Script: `measure_trunk.py`, kept in the session scratchpad, not on the drive.

| TLS tree | Slice at 1.3 m | Pipeline DBH | Matched to (field DBH) | Verdict |
|---|---|---|---|---|
| tree_163 | 0.84 m narrow width (leaning, oval slice; 0.82-0.96 m over 1.2-1.6 m) | N/A | 1440 (14 cm) | wrong pair; size fits 1439 (90 cm) or 1437 (107.5 cm) |
| tree_069 | 0.51 m circle (rms 1.5 cm) | 51.7 | 1448 (83 cm) | probably wrong; size fits 1447 (51.3 cm) |
| tree_060 | 0.56 m circle (rms 2.4 cm) | 56.3 | 1447 (51.3 cm) | plausible (+10%) |
| tree_098 | 0.36 m circle (rms 2.1 cm) | 34.8 | 1432 (51.4 cm) | probably wrong; size fits 1431 (36.1 cm), its map neighbour |
| tree_103 | oval 0.69 x 0.97 m; circle 0.78 m | 66.6 | 1435 (75.5 cm) | good; the circle DBH is low because the trunk is oval (area-equivalent about 78 cm, as in the 23 Oct diagnosis) |

What this means:
- The slices agree with the pipeline DBH on the clean round trunks, so the large differences in the 1448-069 and 1432-098 pairs come from wrong pairing, not TLS error.
- The tree-by-tree numbers above (bias -12.7 cm, RMSE 20.1 cm, median -29%) are therefore not valid and must not go in the report.
- The map seems right about which trees are neighbours but not about exact distances, so position-only matching picks the wrong neighbour.
- The size-based alternatives in the table are leads for checking, not matches. The professor asked that DBH not be used to force a match.

