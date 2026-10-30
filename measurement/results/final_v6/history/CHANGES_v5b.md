# v5b (28 Oct 2026): changes against v5

All 15 validation checks pass. Height VALID 71 -> **75**, REVIEW 92 -> 88. No tree got worse.

## Code changes (scripts/height_refine_all163.py, all163_postprocess.py)
1. **Top check uses the plot crop boundary (ROI box), not the terrain-mesh edge.** The mesh edge also runs round holes in the
   terrain inside the plot (unscanned ground), and a hole cannot cut a tree. On 062, 128, 132 and 135 the "edge" was a mesh
   hole 1-10 m from the stem, while the crop boundary was 2-7.5 m away. All four are now VALID.
2. **Connectivity ("cloud in pieces") recomputed on the current points** with the original method
   (`segmentation_v2_analysis/scripts/checkpoint1_audit.py`). It reproduces the inherited values exactly, so the flag was not
   stale. Clouds in pieces: 001 87.1%, 012 94.5%, 090 94.1%, 002 96.6%, 082 97.5%, 078 97.7% (rule: >= 98%).

## Source clouds (baseline in session4_claude_20261028/state/, previous kept as CloudCompare_review_v2_v5_baseline.csv)
Changed: 100, 124, 136, 137.
- **136:** the floating point is gone. Height 17.511 -> 15.733 m (ITSMe 17.096 -> 15.318, ground -0.415 m under the trunk).
  Crown volume 164.2 -> 105.2 m3 and area 24.6 -> 23.9 m2: more than the floating point was removed. Still REVIEW (ground).
- **100, 124, 137: the floating points are still there.** Every point at the listed coordinates is present and the heights are
  unchanged. The edits saved at 18:18-18:26 removed other points; they took place before the coordinate list was made.
  - 124: DBH VALID -> REVIEW, because the stem axis was refitted on the edited points.
    Crown volume VALID -> REVIEW, because the 1 m slab ratio went 2.03 > 2.
- **083, 099, 027:** not edited; floating points still there.

## Still to clean (height tops)
| Tree | Floating points | Above the crown top | Would become |
|---|---|---|---|
| 100 | 3 | 9.5 m | REVIEW (correct height) |
| 124 | 1 | 7.7 m | REVIEW (ground; correct height) |
| 137 | 4 | 8.8 m | REVIEW (ground; correct height) |
| 083 | 1 | 3.3 m | VALID |
| 027 | 1 | 1.7 m | VALID |
| 099 | 3 | 2.3 m | REVIEW (ground; correct height) |
100 keeps REVIEW only if something else blocks it; its only current reasons are the floating points.

Clouds in pieces whose only height issue is the detached fragments: 078, 082, 090. Removing the detached fragments
(or confirming they belong to the tree) would make them VALID.
