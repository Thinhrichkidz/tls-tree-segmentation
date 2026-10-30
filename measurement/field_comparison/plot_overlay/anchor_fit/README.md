# Anchor fit (29 Oct 2026): not unique, matches NOT reliable

`anchor_fit_and_match.py` fits the site map to the TLS stems using only the large trees: the 9 field trees with DBH >= 50 cm against the 25 largest TLS trees within 26 m of the GPS centre, ranked by point count (TLS DBH is not used to fit or to pick pairs). Rotation searched +-45 deg, translation +-12 m.

## Result
- Best solution: rotation -45 deg (the edge of the search range), plot centre 9.1 m from the GPS centre.
- A very different solution scores almost the same: rotation 0 deg, centre 6.3 m south of the GPS centre (score 33.7 vs 33.5, and 6 anchors within 2 m vs 5).
- The answer jumps when the number of large TLS candidates changes (15, 20, 30, 40 give centres up to 19 m apart; `fit_summary.json`).
- So the map plus GPS do not pin down the plot automatically. `tree_matches.csv` and `dbh_tree_by_tree.csv` are written for the record but should not be used.

## Why
- The GPS posts do not agree with the pegs drawn on the map (the east post is 9 m from the centre by GPS but about 24 m on the map), so handheld GPS error is several metres.
- The map is approximate and not georeferenced.
- Many TLS trees of similar size stand a few metres apart, so several placements fit about equally well.

## What would fix it
A person picks two or three anchor trees by eye (e.g. 1437 and 1439 in the TLS cloud or on a TLS stem map), then the rest is matched from those.
