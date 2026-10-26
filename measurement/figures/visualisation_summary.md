# All-163 TLS visualisations: summary

Generated 23 October 2026, 20:25 (Australia/Sydney), by Claude.

**Numbers source:** `ITSMe_all163_output_v3_FINAL_20261023_201144/ITSMe_all163_results.xlsx` (final audited workbook; read only, hash unchanged before and after).

**Point source:** the 163 original clouds in `CloudCompare_review_v2` (read only; each hash checked against the numerical run).

**Script:** `measurement_pipeline/scripts/render_all163_figures.py`. **Validation:** `validate_all163_visualisations.py`.

## Result

| Output | Count | Status |
|---|---|---|
| Individual 3-panel figures (3D, XZ, YZ), 300 dpi, 4800 × 1920 px | **163 of 163** | all opened and validated; 0 failures |
| Comparison grids (4 × 4, XZ and YZ per tree), 300 dpi | 8 | shortest 8, tallest 8, largest / smallest DBH, largest / smallest crown area, quality comparison, unusual structures |
| Report figures (PNG 300 dpi + PDF) | 8 | 4 distributions, 3 scatter plots, status counts |

**Timing:** a fresh full run took **10.9 s** for the 163 individual figures and **22.5 s** in total, using 32 parallel processes (`logs/render_log_fresh_full_run.json`). Later reruns reuse unchanged figures; each figure's sidecar JSON holds the source hash, style version and title.

## Style: follows the reference figures

The reference figures in `measurement_pipeline/qc_figures/` were all available and inspected (10 individual figures and 2 screens). Their original code was found (`prepare_selected_inputs.py`, `height_qc_figures.py`) and its settings are reused:
- viridis by height, point size 0.25 (0.35 in the grids)
- terrain-mesh vertices within ±2.5 m of the foot in sienna
- a red stem-centre marker, default 3D camera, 15 × 6-inch panels
- red fitted stem-section centres and a red "+" at the foot in the grids

**Deliberate differences from the references:**
- **300 dpi** instead of 150.
- **True proportions in 3D:** the 3D box uses equal metre scaling; the references compressed height.
- **No overlapping labels:** the references' 3D Z label overlapped the XZ panel's label.
- **Colour bar added:** each tree is coloured from 0 m to its own top, so colours compare position within a tree, not across trees.
- **Titles and statuses come from the final workbook**, not the old preliminary heights. For example, tree_103 is now 27.046 m, not 27.226 m. REVIEW heights say REVIEW, and approval shows as PENDING.
- **The red stem centre is drawn only where a fitted stem axis exists.** 28 trees have none, so their figures show no marker and say so.
- **The figure note states** the display sample and that the brown points are terrain-mesh vertices, not observed ground returns.

**Display sampling (display only; measurements used every point):**
- Trees with more than 70,000 points show a random 70,000, drawn with numpy `default_rng(6003)`.
- Grids use 65,000, the same seed as the reference grids.
- No points were removed for appearance.

## Rankings use VALID values only

| Grid | Trees |
|---|---|
| Shortest 8 (VALID height) | 092, 149, 156, 143, 108, 052, 152, 154 |
| Tallest 8 (VALID height) | 084, 103, 041, 069, 026, 060, 093, 074 |
| Largest VALID DBH | 103, 074, 087, 070, 025, 134, 118, 069 |
| Smallest VALID DBH | 151, 146, 154, 149, 037, 018, 152, 088 |
| Largest VALID crown area | 070, 102, 097, 061, 078, 103, 104, 020 |
| Smallest VALID crown area | 068, 143, 024, 096, 045, 013, 053, 162 |
| Quality comparison | All four core metrics VALID: 053, 065, 067, 074. Most N/A or REVIEW: 032, 106, 111, 050 |
| Unusual structures | 079 (two merged trunks), 087 (leaning snag), 125 (bent stem), 118 (second leaning stem), 050 (dead snag), 152 (forked crown), 026 (understorey at the base), 001 (no stem axis) |

The validation script recomputes each ranking from the workbook and checks it matches.

## Report figures (descriptive)

**Distributions:**
- height: 53 VALID and 110 REVIEW, stacked, 0 N/A
- DBH: 43 VALID and 37 REVIEW; 83 N/A not shown
- crown area: 131 VALID and 25 REVIEW; 7 N/A
- crown volume: 100 VALID and 56 REVIEW; 7 N/A

**Scatter plots.** Blue circles are pairs where both values are VALID; orange open triangles have at least one REVIEW value. The power-law (log-log) line is fitted to VALID pairs only:

| Plot | VALID pairs | Fit | R² | Spearman ρ |
|---|---|---|---|---|
| height vs DBH | 23 | H = 4.32·DBH^0.42 | 0.80 | 0.91 |
| crown area vs DBH | 35 | — | 0.66 | 0.78 |
| crown area vs height | 46 | — | 0.56 | 0.69 |

These are descriptive fits to a small, non-random subset of trees. They are not validated allometric models, and the low numbers of VALID pairs should be stated in the report.

**Status counts** use the workbook's colours. No ESTIMATED or UNKNOWN core values exist.

## Validation (`logs/visualisation_validation.json`): all 9 checks pass

1. All 163 trees appear in the index exactly once.
2. There are 163 individual PNGs.
3. Every image opens at 300 dpi.
4. Every title equals the workbook height and status. Each figure was rendered from its own source cloud (hash and point count checked). Stem markers appear only where an axis exists. No approval is claimed. Subtitle statuses match the workbook, and no N/A is shown with a value.
5. All individual figures have one uniform size.
6. The comparison rankings use VALID values only.
7. The comparison figures open.
8. Every report figure exists as both PNG and PDF.
9. The validated workbook is unchanged, and there were no render failures.

**Visual inspection:**
- individual figures: 069, 146, 001, 079, 033
- grids: tallest, shortest, quality, unusual
- charts: height vs DBH, status counts

These found two problems, now fixed and re-rendered: a 3D axis label clipped by the zoom, and grid titles cut off at the figure edges.

## Problem trees made visible (not hidden)

- **tree_079:** two separate trunks from the ground up, merged into one cloud. This explains its 228.7 m² crown, which is REVIEW in the workbook.
- **tree_001:** the terrain falls up to 4 m below the fallback stem foot; the ground reference is uncertain and there is no stem axis.
- **tree_026:** understorey vegetation at the base.
- **tree_033:** the stem base is missing below 0.45 m (poor source data).
- **tree_125 and tree_087:** bent or leaning stems.
- **tree_118:** a second stem leaning alongside the trunk.

## Recommended figures for the INFO6003 report

1. `comparisons/tallest_8_trees.png` and `comparisons/shortest_8_trees.png`: the range of structures, all with VALID heights.
2. `individual_trees/tree_069_3D_sideviews.png` (tall, clear stem and crown) and `tree_146_3D_sideviews.png` (small tree with a layered crown) as example trees.
3. `report_figures/dbh_vs_height.png` and `measurement_status_counts.png`: the main numbers and honest denominators.
4. `comparisons/unusual_structures.png` and `segmentation_quality_comparison.png` for the limitations section.
5. `report_figures/tree_height_distribution.png`, `dbh_distribution.png` and `crown_area_distribution.png`.

## Files

- **Figures:**
  - `individual_trees/tree_NNN_3D_sideviews.png` (each with a `.json` sidecar)
  - `comparisons/`
  - `report_figures/`
- **Index:** `visualisation_index.csv`, one row per tree: figure path and hash, source file and hash, points, display points, stem marker, per-metric status, approval, title, and the comparison figures that include the tree.
- **Logs:** `logs/` (`render_log.json`, `render_log_fresh_full_run.json`, `visualisation_validation.json`).
- **Superseded:** two test runs of these scripts are in `results/_superseded_visualisation_test_runs/`.
