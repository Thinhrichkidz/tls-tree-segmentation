# Data request for the INFO6003 report

**For:** Claude Code, working in this project folder.
**From:** Thomas, for the INFO6003 report on semi-automated individual-tree segmentation of Blue Mountains TLS data.

## Purpose

I am extracting per-tree attributes (height, DBH, crown volume, etc.) from the refined individual-tree point clouds. The report needs these values plus enough metadata to explain how they were produced.

Please:
1. Inspect this folder.
2. Work out which items below can be produced from what is here.
3. Produce them.
4. Write `results/AVAILABILITY_REPORT.md` saying what was and was not obtained, and why.

## Ground rules (important)

1. **Never invent or estimate values.** If something cannot be computed from the data or code here, leave it blank or `NA`, and explain why in the availability report.
2. **Do not modify raw or refined point-cloud files.** Read them only. Write all outputs to `results/`.
3. **Keep every tree, including failed or odd ones.** Use flags, never delete rows. The report must show honest denominators.
4. **Record units for every numeric column** (metres for height and coordinates, centimetres for DBH, m² and m³ for crown values), unless the existing code uses something else. If so, state what it uses.
5. **Do not estimate tree age.** There is no validated method for these plots.
6. **Do not convert crown volume to biomass.** Crown volume is not woody volume.
7. **If an existing script already computes something, reuse it and say so.** Do not silently change its method. If you change a method, document the old and new versions.
8. **Ask before committing to git.** When asked, use clear commit messages, e.g. "Add per-tree attribute extraction and methods record".

---

## Priority 1: core outputs (needed for the report)

### 1. `results/tree_attributes.csv`: one row per refined tree

| Column | Meaning |
|---|---|
| `tree_id` | Unique ID |
| `roi_id` | Region of interest the tree belongs to |
| `source_file` | Point-cloud file name |
| `n_points` | Number of points in the tree cloud |
| `status` | `accepted` / `uncertain` / `discarded` (from my refinement records, if available; otherwise `NA`) |
| `stem_x`, `stem_y` | Stem centre at 1.3 m (or stem base if the 1.3 m fit fails); say which |
| `crs` | Coordinate system, or `local` if unknown |
| `ground_z` | Ground elevation at the stem base |
| `ground_source` | `terrain_mesh` / `lowest_points` / other |
| `height_m` | Tree height |
| `dbh_cm` | Diameter at 1.3 m above ground |
| `dbh_n_points` | Points in the DBH slice |
| `dbh_fit_residual` | Fit residual (e.g. RMSE of the circle fit, in cm) |
| `dbh_fit_ok` | `TRUE` / `FALSE` |
| `crown_volume_m3` | Crown volume (method in `methods.json`) |
| `crown_area_m2` | Crown projected area |
| `crown_base_height_m` | Height of the crown base, if a rule exists |
| `n_stems_at_1_3m` | Number of separate stems at 1.3 m (multi-stem trees) |
| `flag_fork_near_dbh` | Stem forks within about ±0.3 m of 1.3 m |
| `flag_lean` | Stem noticeably leaning |
| `flag_truncated_top` | Top appears cut off or occluded |
| `dist_to_roi_edge_m` | Distance from stem to nearest ROI boundary |
| `flag_crown_touches_edge` | Crown points reach the ROI boundary |
| `stem_completeness` | Fraction of 0.5 m stem slices from ground to crown base that contain points (0–1) |
| `point_density` | Points per m³ of crown hull (or another stated measure) |
| `notes` | Anything unusual |

### 2. `results/methods.json`: how every value was computed

Include:
- **Software:** Python version and library versions (numpy, open3d, laspy, scipy, etc.), plus the script names and their git commit hash if available.
- **Units:** for every column.
- **Height:** definition (maximum point vs. 99th percentile) and ground reference.
- **DBH:** slice height and thickness, the fitting method (least squares, RANSAC, convex hull, etc.), and the quality rule used to set `dbh_fit_ok`.
- **Crown volume:** method (convex hull, alpha shape, voxel) and its parameter (alpha or voxel size).
- **Crown base:** the rule used to separate crown from stem.
- **Multi-stem rule:** how separate stems at 1.3 m are detected.
- **Downsampling:** method and resolution, if known from configs or logs.
- **Rayextract:** the parameters actually used (`gradient`, `height_min`, `max_diameter`, others), if found in scripts, configs or logs.

### 3. `results/summary.json`: dataset-level counts

Include:
- ROI count, and for each ROI its extent or area and location.
- Points before and after downsampling, if recorded.
- Number of automated segments from Rayextract.
- Number of trees refined, accepted, uncertain and discarded.
- Number of trees with `dbh_fit_ok = FALSE`.
- Number of edge-affected trees.

---

## Priority 2: quality and robustness (strengthens the report)

### 4. `results/outliers.csv`

Trees to check manually. Include each tree's ID, the reason, and the relevant values.

Reasons to flag:
- implausible height-to-DBH ratio
- failed DBH fit
- very small or very large crown
- very low stem completeness
- crown touching the ROI edge

Flag only. Do not delete or "fix" anything.

### 5. `results/sensitivity.csv`

Pick 5–10 representative accepted trees, mixing simple trees and trees with overlapping crowns, and record:
- DBH with slice thickness 3, 5 and 10 cm;
- DBH by circle fit vs. convex hull (if both are feasible);
- height as the maximum point vs. the 99th percentile;
- crown volume at two alpha or voxel settings.

### 6. Run time

Record the total and per-tree run time of the extraction, and the machine it ran on (CPU and RAM). Put these in `summary.json`.

---

## Priority 3: only if the data exist

7. **Unedited automated output.** If the original Rayextract segments were kept, write `results/before_after.csv`. For each tree it should give point counts before and after refinement, and, if point IDs or coordinates allow, the IoU between the automated segment and the refined tree.
8. **Refinement log.** Use one only if it was recorded during the work (time per tree, edit types). Summarise it in `results/refinement_log_summary.csv`. **Do not reconstruct times.**
9. **Excel field inventory.** If the Excel file is in the folder:
   - list its columns;
   - say whether it includes tree height and stem coordinates;
   - if tags or locations allow, propose candidate matches in `results/field_matches.csv` with columns `tree_id`, `field_record_id`, `match_status` (`accepted` / `ambiguous` / `unmatched`), `match_basis`, `field_dbh`, `field_height`.
   Do not compute agreement statistics yet; Thomas will check the matches first.
10. **Diameter distribution comparison.** If the plot or quadrant can be identified, compare the TLS DBH distribution with the inventory DBH distribution for the same plot (summary table plus an overlaid histogram or ECDF). This is a distribution-level comparison, not tree-by-tree validation.

---

## Figures (`results/figures/`, PNG at 300 dpi; also PDF if easy)

- `height_vs_dbh.png`: scatter plot, with failed fits and edge trees shown with a different marker.
- `distributions.png`: histograms of height, DBH and crown volume.
- `tree_map.png`: stem positions in the ROI, coloured by status, with the ROI boundary (and the quadrant grid if known).
- `example_trees.png`: 2–3 accepted trees rendered side-on, at the same scale.
- If the unedited output exists, `before_after_example.png`: one tree before and after refinement, same view and scale.

Use clear axis labels with units.

---

## Final step: `results/AVAILABILITY_REPORT.md`

Write a short report with these sections:
1. **Obtained:** each item produced, with its file path.
2. **Not obtained:** each item missing and the reason (data absent, method unclear, needs Thomas's input).
3. **Assumptions made:** anything not taken directly from existing code or configs.
4. **Questions for Thomas:** anything needing his decision, e.g. the meaning of status labels or which ROI is the main one.
5. **Quick numbers:** number of trees processed and, for accepted trees with successful fits only, the median and range of height, DBH and crown volume.

Thomas will pass the `results/` folder (CSV, JSON, figures and this report) to Claude in the INFO6003 project, which will put the values into the report.