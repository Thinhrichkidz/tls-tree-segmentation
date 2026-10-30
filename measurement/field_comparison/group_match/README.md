# Step 2: matching field tags to TLS trees (29 Oct 2026): NOT POSSIBLE from the map

`pair_hypothesis_match.py` (read-only on inputs) tests about 40,000 pair hypotheses. Each pairs two large field trees (DBH >= 50 cm) with two large TLS trees. That fixes rotation (within +-20 deg), scale (0.8-1.4, since the map is approximate) and shift. The score is how many of the 26 field trees then have their own TLS stem within 1.5 m. Pairs are chosen by position only.

A chance baseline repeats the whole search 20 times with the TLS stems moved to random positions in the same area (same number of stems).

## Result (`pair_hypothesis_summary.json`)
| | Field trees matched |
|---|---|
| Best placement on the real data | 16 |
| A completely different placement (centre 13 m away) | 16 |
| Best placement on random stems, 20 runs | 13-16 (mean 14.5) |

- The real data does no better than random stem positions. Two unrelated placements tie.
- The DBH check on the "best" placement is nonsense (e.g. 1445: 11 cm in the field, 76 cm in TLS; 1452: 12.5 vs 54 cm).
- So `pair_hypothesis_matches.csv` is **not** a valid match list. It is kept only to document the test.

## Why
The stand is dense: about 0.06 stems per m2, so any point has a TLS stem within 1.5 m about a third of the time. The site map is approximate (the professor said so; the GPS posts and the drawn pegs disagree by several metres). Map positions cannot single out the right stems.

This confirms the earlier attempts (`../plot_overlay/`, `anchor_fit/`, `north_up_fit/`) on a principled footing: the map plus GPS cannot identify individual trees in the scan.

## What can still be done
- **Distribution-level DBH comparison** inside the plot (already done; it can be refreshed with the better slice DBH from `../trunk_slices/`).
- **Tree-level validation needs identifications from people who were at the plot.** For example the professor confirms which TLS tree is 1437, 1439, 1448 and 1435 from screenshots. Positions measured in the field (bearing and distance from the centre post) for a few large trees would also work.
