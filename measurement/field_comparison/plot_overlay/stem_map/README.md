# TLS stem map for picking anchor trees by eye (29 Oct 2026)

`make_stem_map.py` (read-only on inputs) writes:
- `stem_map_side_by_side.png`: TLS stems (left) beside the field site map (right). Both are north up and at the same metre scale, and the circles use the field map's own symbol scale (radius about 0.02 m per cm DBH), so sizes are comparable.
- `tls_stem_map.png`: the TLS panel alone, larger, for printing or zooming.
- `tls_stems_near_plot.csv`: the 113 TLS trees shown, with position relative to the GPS centre, DBH, height and point count.

How to read the TLS panel:
- The numbers are tree IDs (tree_NNN).
- Bold red = the 25 largest TLS trees by point count (a size measure that does not use DBH).
- Colours: green = DBH VALID, light green = DBH REVIEW, yellow dashed = ESTIMATED DBH only, white = no DBH (size unknown, drawn small).
- The dashed blue circle = 15 m around the GPS centre. The GPS may be several metres off, so the two panels need not line up exactly.

Next step: pick 2-3 field trees you can clearly identify in the TLS data (for example 1437 and 1439, the two largest), confirm them in CloudCompare if needed, and the rest can be matched from those.
