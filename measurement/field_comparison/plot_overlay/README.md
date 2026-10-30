# Field plot overlay (29 Oct 2026)

The 30 m field plot (WSF_ML2A, centre and N/E/S/W posts from `Ecology_Hub_Plot_Data.xlsx`) placed in the TLS crop, plus attempts to match the tagged trees on the site map (`Bullaburra site layout amd1.jpeg`) to TLS stems.

- `map_digitised.csv`: tree, peg and circle positions read by eye from the map (displayed at 2000 px wide; about 0.03 m per px; reading error about +-0.3 m). Map labels 1433 and 1434 are assumed to be CSV tags 1473 and 1474 (same species and DBH); to be confirmed by the professor.
- `plot_posts_utm.csv`: posts in EPSG:32756. GDA94 was treated as WGS84 (offset about 1.5-1.8 m).

## First try: DO NOT USE the matches
`locate_plot_and_match.py` and its outputs in this folder (`tree_matches.csv`, `dbh_tree_by_tree.csv`, `fit_summary.json`, `plot_overlay.png`, `tls_trees_in_plot.csv`, and the "fitted map centre" rows of `dbh_in_plot_distribution.csv`).
The fit used position only. In this dense stand (about one stem per 20 m2) it locked onto small stems: e.g. field 1448 (83 cm) paired with a 10 cm TLS stem. Kept for the record only.

The "GPS centre" rows of `dbh_in_plot_distribution.csv` do not depend on the matching and are usable, with the caveat that the GPS centre may be several metres off.

## Second try: `anchor_fit/`
See `anchor_fit/README.md`. The large-tree fit is not unique either, so no tree-by-tree result is reliable yet.
