# Tree-by-tree matching, placement A (30 Oct 2026)

Inputs (read-only): site map digitisation (`../plot_overlay/map_digitised.csv`), TreeData.csv, v6 FINAL `tree_attributes.csv`, the full 3 cm crop, `CloudCompare_review_v2/`, and the trunk inspection in `C:\Users\hoang\Documents\Codex\2026-10-30\new-chat\outputs\Tree_inspection_2026-10-30` (AI-assisted; fitted base centres and widths for 074, 163, 103, 079 S/N).

**Placement A:** map 1439 = tree_074 and 1435 = tree_103, chosen because their TLS spacing (15.6 m, bearing 100 deg) matches the map. Map scale 1.13, rotation -6 deg. Placements B (1437 = 163) and C (1439 = 163) were tested and rejected (big field trees land on small stems).

## Scripts and outputs
- `search_missing_trunks.py`: predicted positions (`predicted_field_positions_A.csv`) and 1.2-1.4 m slices of the full crop around predicted 1437 and 1455 (`missing_trunk_search.png`).
- `ring_owner.py`, `view_tree081.py`, `ring_profile.py`: the unassigned ~1.1 m ring 4.4 m south of predicted 1437 is in none of the 163 trees; it is a thick leaning stem that ends 5-6 m above ground with no crown (`ring_side_views.png`), so not a live 107.5 cm tree. The tree_081 points near it are understorey foliage.
- `match_placement_A.py`: match table (`tree_matches_A.csv`), chance test, scatter (`dbh_matched_scatter.png`).

## Rules
Greedy one-to-one pairing by distance (max 4 m). Confirmed: <= 2 m and DBH within 25%. Probable: <= 2 m and DBH within 50% (or no DBH), or 2-4 m and DBH within 25%. Otherwise unmatched.
The 50% cap was added after the first run, which classed 1440 (14 cm) / tree_163 (85 cm) and 1437 (107.5 cm) / tree_085 (25 cm) as probable.

## Results (superseded: see Final below)
- 6 confirmed (1448/079S, 1435/103, 1449/102, 1444/089, 1436/091, 1451/106), 8 probable, 12 unmatched.
- Chance test (TLS DBH shuffled among stems, positions fixed, 2000 runs): 1.4 confirmed on average, 95th percentile 3, P(>= 6) = 0.0015. So the identification is better than chance.
- Confirmed, DBH used for the check (slice width for 103 and 079S, estimate for 106): n 6, bias -1.1 cm, RMSE 2.5 cm. Pipeline DBH only: n 4, bias -2.6 cm, RMSE 4.5 cm. **These are biased low by construction**: "confirmed" requires agreement within 25%.
- Confirmed + probable: n 13, bias -4.0 cm, RMSE 8.9 cm (20%). The two large disagreements are 1439/074 (-29%) and 1432/098 (-32%).
- 1437 (107.5 cm): no large live trunk at or near the predicted position; tree_163 (85 cm, leaning 63 deg) is 4-5 m away and sits where the map has 1440/1441. Unmatched.
- 1455 (74.5 cm): predicted 2-3 m inside the crop's east edge in dense clutter; no trunk of that size found. Unmatched.

## Final (30 Oct, after user decision) - USE THESE
User decision: tree_079 is two intertwined trees that cannot be segmented reliably, so tag 1448 is excluded from all counts.
Script `match_placement_A_final.py` -> `tree_matches_A_final.csv`, `dbh_matched_scatter_final.png` (the report's Fig. 3).
- 5 confirmed (1435/103, 1449/102, 1444/089, 1436/091, 1451/106), 8 probable, 12 unmatched, 1 excluded.
- Confirmed: n 5, bias -0.7 cm, RMSE 2.4 cm. Confirmed + probable: n 12, bias -4.1 cm, RMSE 9.2 cm (23%).
- Chance test: P(>= 5 confirmed) = 0.0065.
The user inspected and verified the anchor trees in CloudCompare; AI double-checked widths and spacing.
- `make_plot_location_map.py` -> `plot_location_map.png` (report Fig. 3a): TLS stems, GPS and map-fitted 15 m circles, posts, and lines from predicted tag positions to matched stems (final classes).
