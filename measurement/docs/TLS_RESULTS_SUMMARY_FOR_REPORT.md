# TLS tree-attribute results: summary for the INFO6003 report

Compiled 25 October 2026 by Claude Code from a read-only inspection of the drive. The statistics were computed in memory from the files cited. Apart from this summary, no file was created or changed.

**Path abbreviations:**
- **CH** = `D:\22083142\outputs\WSL_ML2A\55x55\3cm\Codex_help`
- **FINAL** = `CH\measurement_pipeline\results\ITSMe_all163_output_v3_FINAL_20261023_201144`
- **VIS** = `CH\measurement_pipeline\results\ITSMe_all163_visualisations_20261023_202459`
- **SCR** = `CH\measurement_pipeline\scripts`

---

## 1. Folder overview

**Main per-tree results table:** `FINAL\results\tree_attributes.csv` (82,875 bytes, 163 rows × 32 columns).

The same values are in `FINAL\ITSMe_all163_results.xlsx`, sheet "All Tree Results" (182,382 bytes, 163 rows × 59 columns). The four core value columns were checked against the CSV: the largest difference is 7.1e-15, and missing cells match exactly.

**Key small files:**

| Path | Type | Size (bytes) | Content |
|---|---|---|---|
| `FINAL\results\tree_attributes.csv` | CSV | 82,875 | per-tree results |
| `FINAL\results\summary.json` | JSON | 8,298 | dataset counts, statistics, run time |
| `FINAL\results\methods.json` | JSON | 8,275 | methods, parameters, software, script hashes |
| `FINAL\results\outliers.csv` | CSV | 9,579 | 99 outlier flags |
| `FINAL\results\sensitivity.csv` | CSV | 2,569 | 8-tree sensitivity tests |
| `FINAL\ITSMe_all163_results.xlsx` | XLSX | 182,382 | 8-sheet workbook |
| `FINAL\FINAL_AUDIT_REPORT.md` | MD | 16,505 | audit |
| `FINAL\processing_summary.md` | MD | 4,530 | run summary |
| `FINAL\logs\validation.json` | JSON | 998 | 15 checks, all true |
| `FINAL\logs\independent_verification.csv` | CSV | 7,705 | independent re-fit of 24 trees |
| `CH\measurement_pipeline\results\AVAILABILITY_REPORT_20261025_081504\AVAILABILITY_REPORT.md` | MD | 15,220 | availability report (25 Oct) |
| `VIS\visualisation_summary.md`, `VIS\visualisation_index.csv` | MD/CSV | 7,572 / 52,690 | figure index |

**Point-cloud folders** (counts and example names only):

| Folder | Count | Example |
|---|---|---|
| `CH\CloudCompare_review_v2\` (the source of FINAL) | 163 PLY | `tree_001_MANUAL_REVIEW.ply` |
| `CH\manual_seg_v2\` | 163 PLY | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_0 - Cloud.ply` |
| `CH\manual_seg\` (round 1, historical) | 199 PLY | `demo_0_2026-10-19_00h38_45_651.ply` |
| `D:\22083142\outputs\WSL_ML2A\55x55\3cm\trees\clouds\` (unedited automated) | 162 PLY + 3 `.bin` | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_0.ply` |
| `FINAL\per_tree\tree_NNN\` | 163 folders | `prep.json`, `result.json`, `*_local_xyz.txt` |
| `D:\22083142\data\cropped\WSL_ML2A\{35x35,55x55}\{full,2cm,3cm}\` | 12 LAS/LAZ/PLY | `WSL_ML2A_crop_55x55_3cm.las` |

---

## 2. Methods

**Sources:**
- `FINAL\results\methods.json`
- the per-tree worker `SCR\all163_tree_worker.R` (function `measure_tree()`)
- preparation code `SCR\prepare_all163.py` (`prepare()`) and `SCR\all163_common.py`
- status rules in `SCR\all163_postprocess.py`

All measurements use local XYZ text: global coordinates minus the stem-foot translation, with the ground at Z = 0.

### Height

- **Call:** `ITSMe::tree_height_pc(pc, dtm = ground_ref (0,0,0), r = ground_lookup_radius)`, in `all163_tree_worker.R` line 91.
- **Formula:** from the ITSMe 2.0.0 code (printed read-only), h = `max(pc$Z) − median(dtm Z under the 10 lowest points)`.
- **What that means:** the **maximum point**, not a percentile, minus the **terrain-mesh ground at the stem foot**. The foot is where the low-stem axis meets the mesh.
  - 27 trees use a fallback foot at the lowest observation.
  - 2 trees (103 and 108) use a corrected base agreed with the user.
- **Alternatives** (in the workbook columns and `sensitivity.csv`):
  - the 99th-percentile height;
  - the supported top (`supported_top()`, `all163_common.py` lines 52–58): the highest point whose 5th neighbour is ≤ 0.15 m away and 3rd neighbour ≤ 0.08 m.
- **VALID rule** (`methods.json`): ground LOCALLY_SUPPORTED, a robust foot, top LOCALLY_SUPPORTED_OBSERVED_TIP, highest point within 0.5 m of the supported top, and no visual exclusion.
- **REVIEW rule:** an axis/foot offset above 0.25 m (`all163_postprocess.py` line 30, `AXIS_FOOT_TOL_M = 0.25`).
- **Unit:** m.

### DBH

Code: `all163_tree_worker.R` lines 116–157.

- **Location:** 1.3 m **along the stem axis** above the foot ground, lean-corrected. The cloud is rotated so the axis is vertical (`rotation_to_vertical()`).
- **Crop:** radius = max(0.15 m, bark-radius mode + 0.10 m). The bark-radius mode is the peak of a 1 cm histogram of point distances from the axis between 1.0 and 1.6 m.
- **Fit:** `ITSMe::dbh_pc(slice_thickness = 0.06, thresholdR2 = 0.001, functional = TRUE, concavity = 4, r = 1.5)`.
  - **Slice:** 6 cm.
  - **Fitting method:** least-squares circle fit. `stats::optim(L-BFGS-B)` minimises Σ(Rᵢ − mean Rᵢ)² over the centre, and the radius is median(Rᵢ) (`ITSMe:::f`, `ITSMe:::get_radius`, `how = "median"`).
  - Before fitting, points whose nearest neighbour is more than 0.05 m away are removed.
  - `functional = TRUE` also returns a concave-hull diameter (fDBH, `concaveman`).
- **Acceptance** (`accept()`, lines 24–25): 0.03 m < d < 2 m, arc coverage ≥ 0.60, and RMSE = √R2 ≤ min(0.04 m, max(0.01 m, 0.1 × d)).
- **Fallback:** the median of the accepted 6 cm slices at 1.1, 1.2, 1.3, 1.4 and 1.5 m (`diameter_slice_pc`), labelled REVIEW.
- **Failure:** no stem axis, or no acceptable fit, gives N/A. Raw failed fits go in the workbook column "Unaccepted DBH fit (cm)" (46 values).
- **Ratio rule:** H/(D/100) outside 20–150 gives REVIEW (`all163_postprocess.py` lines 228–233). No tree triggered it.
- **Exceptions** (`methods.json` "DBH"):
  - 067 uses an outline filter;
  - 103 also reports an area-equivalent diameter;
  - 033 is not released;
  - 108 is provisional.
- **Units:** cm. `dbh_fit_residual` is the RMSE in cm.
- **Not RANSAC.** RANSAC (seed 6003) is used only to fit the stem axis (`refresh_axis()` / `circle()` from `preliminary_heights.py`).

### Crown base height

- **Code:** `crown_base_rule()`, `all163_common.py` lines 118–152. Constants: `DZ = 0.25`, `CROWN_FRACTION = 0.3`, `FACTOR = 3.0`, `CONTINUITY = 0.7` (line 29).
- **Layers:** 0.25 m thick. Each layer's r95 radius is smoothed over 3 layers.
- **Trunk reference:** the narrowest layer between 1 m and 60% of tree height.
- **Crown layer:** wider than max(3 × trunk r95, 0.3 × widest layer).
- **Base:** the lowest crown layer above 1 m from which at least 70% of the layers up to the top are crown.
- **User choices** override the rule. They are recorded in:
  - `CH\measurement_pipeline\results\CROWN_BASE_RERUN_20261023_191046\agreed_crown_bases.csv`
  - `...\CROWN_BASE_REVIEW_ALL163_20261023_194703\user_crown_choices.csv`
- **Unit:** m.

### Crown points, area and volume

- **Crown points** (worker lines 94–114): `ITSMe::classify_crown_pc(thresholdbranch = 1.5)`, keeping points with Z ≥ crown base.
  - If ITSMe finds no crown, all tree points above the base are used instead. These are labelled REVIEW (12 trees; workbook "Crown method").
- **Area:** `ITSMe::projected_area_pc(concavity = 3)`, a **concave hull**, m² (`envelope()`, line 50).
- **Volume:** a **3D convex hull**, `geometry::convhulln(options "Qt Tv")` (`crown_convex_hull()`, `SCR\crown_volume_metrics.R` line 14), m³. It includes air gaps and is not wood volume.
- **Gap screen:** envelope ÷ sum of 1 m slab hulls; a ratio above 2 gives REVIEW (`envelope()` lines 55–62).
- **Size outliers:** crown area outside the 5th–95th percentile gives REVIEW (`all163_postprocess.py` lines 236–245).

### Other attributes

From `stem_indicators()`, `all163_common.py` lines 164–184:
- **`n_stems_at_1_3m`:** point clusters within 1 m of the axis, in a 10 cm layer at 1.3 m (link distance 0.10 m, at least 8 points per cluster).
- **`flag_fork_near_dbh`:** more clusters at 1.6 m than at 1.0 m, and at least 2 at 1.6 m.
- **`stem_completeness`:** the fraction of 0.5 m slices, from the ground to the crown base, that have a point within 0.5 m of the axis.
- **`flag_lean`:** lean ≥ 10°.

Derived values (`methods.json` "Crown"):
- crown length = height − crown base
- crown ratio = crown length ÷ height
- equivalent crown diameter = 2√(area/π)
- point density = crown points ÷ envelope volume (points/m³)

### Software versions

**Used for FINAL** (`FINAL\results\methods.json`, "Software"):
- R 4.5.2 (ucrt), ITSMe 2.0.0, geometry 0.5.2
- Python 3.13.14, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2
- plyfile: "unknown"
- Windows 10 (10.0.19045), AMD64

**Inspection session** (used only to read and print):
- Python 3.12.7 (Anaconda), pandas 2.2.2, numpy 1.26.4, scipy 1.13.1, openpyxl 3.1.5
- R 4.4.3 with ITSMe 2.0.0 from `CH\measurement_pipeline\environment\home-R-library`; the ITSMe code was read from this library.

---

## 3. Processing parameters

**Downsampling method: NOT FOUND.**
- Searched: `methods.json` (which only says "3 cm raycloud product … no further resampling"), `D:\22083142\tls-tree-segmentation\docs\WORKFLOW.md` (a TODO) and the PLY headers.
- The crop PLY header says "Created by CloudCompare v2.13.2, 2026-09-25" (`D:\22083142\data\cropped\WSL_ML2A\55x55\3cm\WSL_ML2A_crop_55x55_3cm.ply`).
- The resolution is 3 cm, from the folder and file names.

**ROI:**
- **Count:** 1, `WSL_ML2A_crop_55x55` (`summary.json` "roi").
- **Extent:** the XY bounding box runs x 261323.43–261389.14 m and y 6264444.92–6264512.76 m, so it is **65.71 × 67.84 m**, not 55 × 55 m. Source: the LAS header of `D:\22083142\data\cropped\WSL_ML2A\55x55\3cm\WSL_ML2A_crop_55x55_3cm.las`.
- **CRS:** EPSG:32756 (`methods.json`, "not re-verified").
- **True boundary shape:** NOT FOUND.

**Point counts** (from the LAS headers; `summary.json` says "NA (not recorded)"):

| Stage | Points | Path |
|---|---|---|
| Raw 1 cm scan (whole scan, 450 × 754 m) | 355,462,232 | `D:\22083142\data\raw\WSL_ML2A\2025-05-12_WSL_ML2A_1cm_all.laz` |
| 55x55 crop, full resolution | 234,060,453 | `...\data\cropped\WSL_ML2A\55x55\full\WSL_ML2A_crop_55x55_full.laz` |
| 55x55 crop, 2 cm | 84,276,295 | `...\55x55\2cm\WSL_ML2A_crop_55x55_2cm.las` |
| 55x55 crop, 3 cm (used) | 45,449,820 | `...\55x55\3cm\WSL_ML2A_crop_55x55_3cm.las` |
| 35x35 crop, full / 2 cm / 3 cm (not used) | 110,682,307 / 39,013,447 / 20,543,086 | `...\35x35\...` |

**Rayextract / RayCloudTools parameters actually used: NOT FOUND.**
- Searched: `methods.json`, `WORKFLOW.md`, the PLY headers (which say only "generated by raycloudtools library"), and all handover notes.
- `WORKFLOW.md` gives only the pipeline document's example for a **different plot** (DSF_CP1B): `rayimport … ray 0,0,-0.1 --max_intensity 0`, `rayextract terrain … --gradient 2`, `rayextract trees … --max_diameter 0.9 --height_min 10`. This is not evidence for WSL_ML2A.

**Step 3 `--distance_th`:** the value used is NOT FOUND. The script is `D:\22083142\scripts\tree_extraction.py`, whose default is 0.01 m.

---

## 4. Per-tree results

Source: `FINAL\results\tree_attributes.csv`, 163 rows. **There are no duplicate tree IDs.**

### Columns, units and missing values

Units come from `methods.json` and the column names. In the CSV, `NA` marks a missing value.

| Column | Unit | Missing / NA |
|---|---|---|
| tree_id, roi_id, source_file | – | 0 |
| n_points | count | 0 |
| status (accepted/uncertain/discarded) | – | **163 (all NA)** |
| stem_x, stem_y | m, EPSG:32756 | 0 |
| stem_xy_source | – | 0 (135 "stem axis at 1.3 m", 28 "stem base (foot XY); no stem axis") |
| crs | – | 0 |
| ground_z | m | 0 |
| ground_source | – | 0 (134 stem foot, 27 fallback foot, 2 corrected base) |
| height_m | m | 0 (VALID 53, REVIEW 110) |
| height_status | – | 0 |
| dbh_cm | cm | **83** (VALID 43, REVIEW 37, N/A 83) |
| dbh_status | – | 0 |
| dbh_n_points | count | 28 |
| dbh_fit_residual | cm (RMSE) | 35 |
| dbh_fit_ok | TRUE/FALSE | 0 (TRUE 80, **FALSE 83**) |
| crown_volume_m3 | m³ | 7 (VALID 100, REVIEW 56, N/A 7) |
| crown_volume_status | – | 0 |
| crown_area_m2 | m² | 7 (VALID 131, REVIEW 25, N/A 7) |
| crown_area_status | – | 0 |
| crown_base_height_m | m | 7 |
| n_stems_at_1_3m | count | 0 |
| flag_fork_near_dbh | bool | 0 |
| flag_lean | bool | 28 |
| flag_truncated_top | bool | 0 |
| dist_to_roi_edge_m | m | 0 |
| flag_crown_touches_edge | bool | 7 |
| stem_completeness | 0–1 | 33 |
| point_density | points/m³ | 7 |
| notes | – | 14 empty |

**DBH method** (workbook "DBH method"):
- 66 direct fits at 1.3 m
- 14 fallbacks (median of 1–4 accepted slices)
- 55 with no acceptable slice
- 28 not attempted (no stem axis)

### Descriptive statistics

- **"All"** means every value present in the column (VALID + REVIEW).
- The `status` column is NA for every tree, so **there is no "accepted" subset**. "VALID" is the closest documented substitute.
- SD uses n − 1, and quartiles use linear interpolation.
- These values match `summary.json` → "statistics".

| Metric | Subset | n | Mean | SD | Median | Q1 | Q3 | Min | Max |
|---|---|---|---|---|---|---|---|---|---|
| Height (m) | All | 163 | 17.044 | 5.027 | 16.357 | 12.389 | 21.125 | 9.387 | 27.178 |
| Height (m) | VALID | 53 | 16.821 | 5.055 | 15.404 | 12.372 | 20.799 | 10.309 | 27.178 |
| DBH (cm) | All | 80 | 30.643 | 15.551 | 25.376 | 18.493 | 38.309 | 10.117 | 75.781 |
| DBH (cm) | VALID | 43 | 31.653 | 16.858 | 26.792 | 18.214 | 42.100 | 10.442 | 66.614 |
| Crown volume (m³) | All | 156 | 212.529 | 319.594 | 95.058 | 42.380 | 224.761 | 3.405 | 2426.610 |
| Crown volume (m³) | VALID | 100 | 174.472 | 221.735 | 85.662 | 43.219 | 207.175 | 5.492 | 972.652 |
| Crown area (m²) | All | 156 | 25.755 | 29.548 | 15.016 | 8.591 | 27.317 | 1.888 | 228.709 |
| Crown area (m²) | VALID | 131 | 21.773 | 19.386 | 14.553 | 9.006 | 26.038 | 3.392 | 90.107 |
| Crown base (m) | All (no status column) | 156 | 7.051 | 4.143 | 6.750 | 3.250 | 10.750 | 1.000 | 19.000 |

**Trees with all four core metrics VALID: 14.** FINAL says 16, but that count is out of date; see §9, item 2.

The 14 trees are:
- **Height (m):** median 16.52, range 10.54–27.05.
- **DBH (cm):** median 19.87, range 13.38–66.61.
- **Crown volume (m³):** median 80.7, range 18.8–856.5.

### Outliers (listed only; nothing was changed)

Tree IDs carry the `tree_` prefix. V = VALID, R = REVIEW.

| Metric | 5 smallest | 5 largest |
|---|---|---|
| Height (m) | 121 9.387 (R), 155 9.628 (R), 105 9.970 (R), 011 10.148 (R), 004 10.234 (R) | 084 27.178 (V), 103 27.046 (V), 100 26.883 (R), 041 26.602 (V), 069 26.199 (V) |
| DBH (cm) | 092 10.117 (R), 151 10.442 (V), 146 10.647 (V), 154 10.906 (V), 149 13.384 (V) | 084 75.781 (R), 103 66.614 (V), 074 63.649 (V), 087 62.880 (V), 070 62.801 (V) |
| Crown volume (m³) | 146 3.405 (R), 024 5.492 (V), 044 5.838 (R), 004 6.673 (R), 158 6.685 (R) | 079 2426.610 (R), 026 1336.141 (R), 084 1174.658 (R), 031 1025.506 (R), 110 998.977 (R) |
| Crown area (m²) | 146 1.888 (R), 158 2.685 (R), 004 3.009 (R), 033 3.054 (R), 151 3.078 (R) | 079 228.709 (R), 110 106.835 (R), 084 103.722 (R), 132 99.343 (R), 069 97.638 (R) |
| Crown base (m) | 101, 039, 052, 086, 147: all 1.00 | 126 19.00, 007 16.25, 163 16.25, 087 15.50, 025 15.25 |

**Height-to-DBH ratio** H/(D/100), over the 80 trees with both values:
- range 31.1–118.4, median 67.6;
- **no tree falls outside the code's 20–150 rule**, consistent with 0 ratio flags in `outliers.csv`;
- lowest: 087 31.1, 025 35.4, 084 35.9, 074 36.6, 134 37.7;
- highest: 151 118.4, 146 113.3, 075 104.5, 124 104.1, 154 103.5.

**Existing outlier flags** in `FINAL\results\outliers.csv` (99 in total):
- 83 failed or missing DBH fits
- 7 very large crowns
- 7 very small crowns
- 1 very low stem completeness
- 1 crown touching the ROI edge

### Spearman correlation, height vs DBH

Computed in memory:
- **all available pairs:** n = 80, ρ = 0.831, p = 1.45e-21;
- **VALID–VALID pairs:** n = 23, ρ = 0.906, p = 2.68e-09.

### First 10 rows of `tree_attributes.csv`

Display changes (the data are unchanged):
- numbers are rounded to 3 decimals, and `notes` is cut to 60 characters;
- three columns are left out because they have the same value in all 10 rows: `roi_id` = WSL_ML2A_crop_55x55, `status` = NA, `crs` = EPSG:32756;
- `source_file` is also left out: it is `tree_NNN_MANUAL_REVIEW.ply`, except tree_010, which is `tree_010_UNCHANGED.ply`;
- in `ground_source`, "stem foot" means "terrain_mesh at stem foot (actual triangle)" and "fallback foot" means "terrain_mesh at lowest-observation XY (fallback foot; uncertain)".

| tree_id | n_points | stem_x | stem_y | stem_xy_source | ground_z | ground_source | height_m | h_status | dbh_cm | dbh_status | dbh_n_points | dbh_fit_residual | dbh_fit_ok | crown_volume_m3 | vol_status | crown_area_m2 | area_status | crown_base | n_stems | fork | lean | trunc_top | dist_edge | crown_edge | stem_compl | point_density | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_001 | 43055 | 261324.603 | 6264498.254 | stem base (foot XY); no stem axis | 705.468 | fallback foot | 19.214 | REVIEW | NA | N/A | NA | NA | FALSE | 265.305 | REVIEW | 25.537 | REVIEW | 3.000 | 3 | FALSE | NA | TRUE | 1.174 | FALSE | NA | 151.916 | ground reference uncertain (inherited QC); stem foot is a fa |
| tree_002 | 42245 | 261327.606 | 6264494.458 | stem axis at 1.3 m | 703.283 | stem foot | 18.657 | REVIEW | 34.876 | VALID | 40 | 2.254 | TRUE | 208.772 | VALID | 36.091 | VALID | 11.500 | 1 | FALSE | FALSE | TRUE | 4.177 | FALSE | 1.000 | 178.994 | ground reference uncertain (inherited QC); tree top needs re |
| tree_003 | 17062 | 261329.472 | 6264499.332 | stem axis at 1.3 m | 702.280 | stem foot | 12.580 | REVIEW | NA | N/A | 9 | NA | FALSE | 42.177 | VALID | 9.994 | VALID | 3.500 | 2 | FALSE | FALSE | TRUE | 6.042 | FALSE | 0.857 | 352.823 | ground reference uncertain (inherited QC); tree top needs re |
| tree_004 | 3477 | 261329.532 | 6264497.058 | stem axis at 1.3 m | 702.236 | stem foot | 10.234 | REVIEW | NA | N/A | 3 | NA | FALSE | 6.673 | REVIEW | 3.009 | REVIEW | 6.250 | 0 | FALSE | FALSE | TRUE | 6.103 | FALSE | 1.000 | 447.315 | ground reference uncertain (inherited QC); tree top needs re |
| tree_005 | 50283 | 261330.573 | 6264478.532 | stem base (foot XY); no stem axis | 703.095 | fallback foot | 16.100 | REVIEW | NA | N/A | NA | NA | FALSE | 52.049 | VALID | 13.327 | VALID | 10.750 | 4 | TRUE | NA | TRUE | 7.144 | FALSE | NA | 690.060 | ground reference uncertain (inherited QC); stem foot is a fa |
| tree_006 | 64021 | 261330.806 | 6264482.299 | stem axis at 1.3 m | 702.596 | stem foot | 16.357 | REVIEW | NA | N/A | 23 | 1.299 | FALSE | 220.026 | REVIEW | 26.037 | REVIEW | 3.750 | 1 | FALSE | FALSE | TRUE | 7.377 | FALSE | 1.000 | 285.916 | ground reference uncertain (inherited QC); tree top needs re |
| tree_007 | 38021 | 261330.269 | 6264491.377 | stem axis at 1.3 m | 702.416 | stem foot | 21.999 | REVIEW | NA | N/A | 20 | 1.046 | FALSE | 75.918 | VALID | 24.014 | VALID | 16.250 | 1 | FALSE | FALSE | FALSE | 6.840 | FALSE | 1.000 | 443.059 | ground reference uncertain (inherited QC) / fit failed quali |
| tree_008 | 65871 | 261331.753 | 6264476.121 | stem axis at 1.3 m | 703.817 | stem foot | 19.301 | VALID | 28.148 | REVIEW | 33 | 1.925 | TRUE | 102.767 | VALID | 27.906 | VALID | 13.500 | 2 | FALSE | FALSE | FALSE | 8.324 | FALSE | 1.000 | 517.240 | 2 point clusters within 1 m of the stem at 1.3 m (second ste |
| tree_009 | 98274 | 261332.140 | 6264486.960 | stem axis at 1.3 m | 702.661 | stem foot | 15.648 | REVIEW | NA | N/A | 8 | 0.983 | FALSE | 180.396 | VALID | 21.930 | VALID | 1.250 | 1 | FALSE | FALSE | FALSE | 8.711 | FALSE | 1.000 | 542.473 | ground reference uncertain (inherited QC) / fit failed quali |
| tree_010 | 26371 | 261331.328 | 6264495.534 | stem axis at 1.3 m | 702.155 | stem foot | 11.945 | REVIEW | NA | N/A | 10 | 1.221 | FALSE | 50.324 | VALID | 9.319 | VALID | 3.000 | 1 | FALSE | FALSE | FALSE | 7.899 | FALSE | 1.000 | 515.280 | ground reference uncertain (inherited QC) / fit failed quali |

---

## 5. Segmentation and refinement records

### Automated (Rayextract) segments

- **Count:** **162** per-tree clouds, `D:\22083142\outputs\WSL_ML2A\55x55\3cm\trees\clouds\…_segmented_0.ply` to `_161.ply`.
- **Points:** 28,708,304 in total (summed from the PLY headers). A further 16,741,516 points were left unassigned, in `…\3cm\unassigned\WSL_ML2A_crop_55x55_3cm_raycloud_segmented_-1.ply`.
- `summary.json` gives "NA (not recorded in this batch)", which is now out of date.

### Refined, accepted, uncertain and discarded

- **Refined:** 163 (`summary.json` "trees_refined").
- **Accepted / uncertain / discarded:** NOT FOUND. `summary.json` says "NA (no accepted/uncertain/discarded records …)", and the workbook column "Human approval" is PENDING for all 163 trees.

Screening labels exist, but they are **not** acceptance decisions:

| Round | Labels | Source |
|---|---|---|
| V2 review | 134 MANUAL_REVIEW, 25 UNCHANGED, 4 AUTO_CANDIDATE | `CH\segmentation_v2_correction\new_correction_summary.md` |
| Round 1 (199 exports) | 0 ACCEPTED, 197 REVIEW REQUIRED, 2 EXCLUDED | `CH\segmentation_final\dataset_summary.md` |

### Unedited automated output

**Yes, it still exists**, under `D:\22083142\outputs\WSL_ML2A\55x55\3cm\`:
- `trees\clouds\`
- `segmentation\WSL_ML2A_crop_55x55_3cm_raycloud_segmented.ply` (the whole plot)
- `unassigned\`, `metadata\`, `trees\metadata\`, `trees\meshes\`
- `output_script\trees_propagated\` (162 Step 3 LAS files)

**Caveat:** V2 file numbers do not reliably equal the automated IDs. 96 of the 163 V2 files have the same point count as the same-numbered automated tree, and 67 do not (from the PLY headers).

### Refinement or timing log

**NOT FOUND.** All folders were searched; `FINAL_AUDIT_REPORT.md` item R8 also states that none exists. CloudCompare working files exist without any log: `…\3cm\segmentation\` `seg_v01–v11.ply`, `work_v01–v04.bin`, `clean_v01–v03.bin`.

### Per-tree flags

From `tree_attributes.csv`:

| Flag | Counts |
|---|---|
| `flag_crown_touches_edge` | TRUE 1, FALSE 155, NA 7 |
| `dist_to_roi_edge_m` < 2 m | 1 tree (tree_001, 1.174 m) |
| `flag_fork_near_dbh` | TRUE 41, FALSE 122 |
| `flag_lean` | TRUE 17, FALSE 118, NA 28 |
| `flag_truncated_top` | TRUE 46, FALSE 117 |

`n_stems_at_1_3m` (a cluster heuristic, not a verified stem count):

| Clusters at 1.3 m | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Trees | 3 | 97 | 40 | 12 | 5 | 4 | 2 |

---

## 6. Field inventory

**There is no field inventory (Excel or CSV) anywhere on `D:\22083142`.**
- **Files searched:** all 10 `.xlsx` and all 483 `.csv` files, excluding environment folders.
- **Header search:** species, tag, quadrant, site_id, field, inventory and plot_id. The only hits were false positives: `dbh13_*` columns, and the word "field" in `tree_146_provisional_metric_fields.csv`.
- **Agreement:** `FINAL_AUDIT_REPORT.md` item T17 reached the same conclusion.

**`TreeData.csv`:** NOT FOUND on the drive. It is known only from its audit output, `D:\22083142\tls-tree-segmentation\docs\INFO6003_report_v3\data\audit_output.json`:
- SHA-256 `fb308df06f97…`, 1,508 rows, 47 columns, 37 site IDs;
- quadrants SW 379 / SE 366 / NE 358 / NW 352 / missing 52;
- tag IDs, species, and DBH columns dbh1–dbh11;
- its "coordinate_or_height_columns" are only `canopy_live_dead`, `canopy_percent_alive` and `stump_height_m`. So it has **no tree height and no stem coordinates**.

The report draft (`INFO6003_Final_Report_v3.tex`) says the validation reference is a separate Excel inventory. That file is not on the drive.

**Matching between segmented trees and field records:** NOT FOUND. There is no `field_matches.csv` or equivalent.

---

## 7. Existing figures

All files are PNG unless noted.

### Final result figures (VIS)

| Path | Description |
|---|---|
| `VIS\report_figures\dbh_vs_height.png/.pdf` | DBH vs height for VALID pairs (n = 23, per `HANDOVER\SESSION_CHRONICLE.md`), with a descriptive fit |
| `VIS\report_figures\tree_height_distribution.png/.pdf` | Height histogram |
| `VIS\report_figures\dbh_distribution.png/.pdf` | DBH histogram |
| `VIS\report_figures\crown_volume_distribution.png/.pdf` | Crown volume histogram |
| `VIS\report_figures\crown_area_distribution.png/.pdf` | Crown area histogram |
| `VIS\report_figures\dbh_vs_crown_area.png/.pdf`, `height_vs_crown_area.png/.pdf` | Scatter plots |
| `VIS\report_figures\measurement_status_counts.png/.pdf` | VALID / REVIEW / N/A counts per metric |
| `VIS\comparisons\tallest_8_trees.png`, `shortest_8_trees.png` | 4 × 4 grids of XZ/YZ side views |
| `VIS\comparisons\largest_dbh_trees.png`, `smallest_dbh_trees.png`, `largest_crown_trees.png`, `smallest_crown_trees.png` | 4 × 4 comparison grids |
| `VIS\comparisons\segmentation_quality_comparison.png`, `unusual_structures.png` | Quality and unusual-structure grids |
| `VIS\individual_trees\tree_NNN_3D_sideviews.png` (163 files) | 3D + XZ + YZ view per tree. Recommended examples: `tree_069_…` and `tree_146_…` (`VIS\visualisation_summary.md`) |

### Other figures

| Path | Description |
|---|---|
| `CH\segmentation_final\qc_figures\demo_94_before_after.png` | Before/after of Codex's round-1 lower-stem pilot. This is an added-points proposal, not the manual refinement |
| `CH\CloudCompare_review_support\qc_figures\*_proposal_before_after.png` (7 files) | Before/after of round-1 correction proposals |
| `CH\measurement_pipeline\qc_figures\` (12 files) | Earlier reference 3D side views of 10 trees and the tallest/shortest screens. The heights shown are earlier values |
| `CH\session2_claude_20261023\outputs\step3\tree_NNN.png` (163 files) | Segmentation-review views (floating parts, leftovers), state as of 22 Oct |
| `D:\22083142\tls-tree-segmentation\docs\INFO6003_report_v3\figures\dbh_ecdf.pdf` | ECDF of TreeData.csv dbh1, by site prefix |

**Not found:**
- a tree map / stem-position map;
- a before/after comparison of the manual refinement against the automated output.

---

## 8. Files to use for the report (small files, no point clouds)

1. `FINAL\results\tree_attributes.csv` (82.9 KB), the main table.
2. `FINAL\results\summary.json` and `FINAL\results\methods.json`.
3. `FINAL\results\outliers.csv` and `FINAL\results\sensitivity.csv`.
4. `CH\measurement_pipeline\results\AVAILABILITY_REPORT_20261025_081504\AVAILABILITY_REPORT.md`. It corrects the "not obtained" items and the all-VALID count (16 → 14).
5. `FINAL\FINAL_AUDIT_REPORT.md` (definitions in §E) and `FINAL\processing_summary.md`.
6. Figures:
   - from `VIS\report_figures\`: `dbh_vs_height.png`, `measurement_status_counts.png`, `tree_height_distribution.png`, `dbh_distribution.png`, `crown_volume_distribution.png` and `crown_area_distribution.png` (about 0.1 MB each);
   - `VIS\individual_trees\tree_069_3D_sideviews.png` (1.3 MB) and `tree_146_3D_sideviews.png` (0.9 MB);
   - optionally `VIS\comparisons\tallest_8_trees.png` (3.6 MB).
7. Optionally `FINAL\ITSMe_all163_results.xlsx` (182 KB), which holds the QC reasons.

---

## 9. Gaps and questions

1. **"Accepted" is undefined.** `status` is NA for all 163 trees, so "accepted tree" statistics are replaced by VALID values.
2. **The all-VALID count conflicts.** FINAL `summary.json` (`trees_all_core_valid`), the workbook Summary sheet ("of which all four VALID") and `processing_summary.md` all say **16**. The per-tree statuses give **14**, because tree_069 and tree_146 have crown area and volume at REVIEW.
   - **Cause:** `all_core_valid` is set at `all163_postprocess.py` line 188, before the crown-size outlier rule runs (about lines 236–245).
   - **Quote 14.**
3. **`height_m` includes REVIEW values.** It has a value for all 163 trees, but 110 of those are REVIEW. `dbh_cm` likewise includes 37 REVIEW values.
4. **`dbh_fit_residual` includes failed fits.** It has 128 values, including failed fits (maximum 18.06 cm), so it is not limited to accepted fits.
5. **The edge flags assume a box.** They treat the ROI as its 65.71 × 67.84 m bounding box; the true boundary of the "55x55" crop is NOT FOUND.
6. **Settings not recorded:** the downsampling method, the Rayextract parameters and the Step 3 threshold are all NOT FOUND (§3).
7. **No reference data.** There is no field inventory and no TreeData.csv on the drive (§6), so validation is not possible.
8. **Crown volume sensitivity is partial.** Volume "at two alpha/voxel settings" was not computed, because the method is a convex hull with no such parameter. A comparison of the envelope against the slab sum is given instead.
9. **The workbook has no Visualisation Index sheet** and no hyperlinks; the figure index is a separate CSV.
10. **Versions differ.** The inspection session used different Python and R versions from FINAL. ITSMe is 2.0.0 in both.
11. **The report draft is out of date.** `INFO6003_Final_Report_v3.tex` still says no numerical values exist.

---

## 10. Excel and CSV files

### 10.1 The ten `.xlsx` files

All ten are in CH; there are no `.xls` files and none elsewhere on the drive.

**What they all are:** type **(b), TLS-derived results**. Every sheet concerns height, DBH or crown values, or their QC, keyed by `tree_NNN`. None is a field inventory or a matching table.

**How they were read:** with openpyxl, never saved.

**Structure:**
- no merged cells, hidden sheets or hyperlinks;
- formulas appear only in the two 20-tree review workbooks (1 + 80 cells each);
- several sheets have a title row before the header, so read them with a header offset.

| # | Path (under `CH\measurement_pipeline\results\`) | Sheets (rows × cols) | Notes |
|---|---|---|---|
| 1 | `ITSMe_all163_output_v3_FINAL_20261023_201144\ITSMe_all163_results.xlsx` | All Tree Results 164×59; Summary Statistics 40×14; Quality Control 434×6; Methodology & Metadata 88×2; Check vs 20-tree results 23×14; DBH lean-corrected slices 676×8; Run details 164×9; Changes vs previous version 49×8 | **Final.** The header is row 1 in All Tree Results, DBH slices and Run details; the other sheets have a title row first |
| 2 | `ITSMe_all163_output_v2_20261023_195000\ITSMe_all163_results.xlsx` | Same layout; QC 411×6; Changes 317×7 | Superseded (v2) |
| 3 | `ITSMe_all163_output_20261023_194253\ITSMe_all163_results.xlsx` | Same layout without the Changes sheet; QC 534×6 | Superseded (v1) |
| 4–5 | `_superseded_all163_audit_intermediate_runs\…_v3_audit_20261023_200244\…xlsx`, `…_v3_final_20261023_200555\…xlsx` | Same as FINAL | Superseded intermediate runs |
| 6 | `ITSMe_top10_batch_20261023\ITSMe_top10_results.xlsx` | Results 12×33; Original vs adapted 11×19; DBH lean-corrected slices 56×8; Other diameters 34×6; DBH sensitivity 12×19; Run details 12×4; Notes 26×1 | 11-tree test (historical) |
| 7 | `CROWN_VOLUME_TOP20_20261023_164430\outputs\top20_crown_review\Crown_volume_20_tree_review.xlsx` | Measurements 32×15 (1 formula); Diagnostics 32×15 (80 formulas) | 20-tree test; row 1 is blank and the header comes lower |
| 8 | `DBH_remaining_band_review_20261023_172945\outputs\dbh_band_review\Tree_measurements_with_DBH_review.xlsx` | Measurements 32×15 (1 formula); Diagnostics 32×15 (80 formulas); DBH band review 96×8 | Historical DBH band tests |
| 9 | `CORRECTED_FOUR_TREE_RERUN_20261023_190059\outputs\Tree_measurements_CORRECTED_FOUR_TREE_RERUN_20261023_190059.xlsx` | Measurements 23×17; Four trees old vs new 7×13; DBH detail (4 trees) 50×10; Read me 19×1 | Historical; title row first |
| 10 | `CROWN_BASE_RERUN_20261023_191046\outputs\Tree_measurements_CROWN_BASE_RERUN_20261023_191046.xlsx` | Measurements 23×21; Crown base change 23×13; Four trees old vs new 7×13; DBH detail 50×10; Read me 24×1 | Historical; title row first |

**The 59 columns of FINAL "All Tree Results"** (units as given in the headers):

| Group | Columns |
|---|---|
| Identity and status | Tree; Tree processing status; Original V2 file; Review file; ROI; Points; Segmentation status (all "NA"); Inherited QC status; Human approval (all "PENDING") |
| Height | Height ITSMe (m); Height status; Height note; Height supported top (m); Height 99th percentile (m) |
| DBH | DBH (cm); DBH status; Estimated DBH (cm) (0 values); Unaccepted DBH fit (cm) (46 values); DBH note; DBH method; Points in 6 cm DBH slice; DBH circle fit RMSE (cm); DBH arc coverage; DBH fit OK; Stem lean (deg); Area-equivalent DBH (cm) (1 value) |
| Crown | Crown base height (m); Crown base status; Crown base source; Crown projected area (m2); Crown area status; Crown envelope volume (m3); Crown volume status; Crown note; Crown length (m); Crown ratio; Equivalent crown diameter (m); Envelope / 1 m slab ratio; Crown point density (points/m3); Crown method |
| Position and indicators | Stem X (m); Stem Y (m); Stem position source; CRS; Ground Z (m); Ground source; Distance to ROI edge (m); Stem completeness (0-1); Stem clusters at 1.3 m; Fork near DBH; Leaning stem (>=10 deg); Truncated top; Crown touches ROI edge; Neighbour contact (inherited); Stem axis source |
| Reference and provenance | Reference: automatic ITSMe crown area (m2); Reference: automatic ITSMe crown envelope (m3); Reference: automatic crown start (m); Source SHA-256 |

**First 10 rows:** the core values equal those in `tree_attributes.csv` (verified in memory); see the table in §4.

**Summary Statistics sheet:** it has the same VALID and VALID+REVIEW statistics as §4, plus these (VALID only):

| Metric | n | Mean | Median |
|---|---|---|---|
| Crown length (m) | 53 | 9.741 | 9.754 |
| Crown ratio | 53 | 0.594 | 0.586 |
| Equivalent crown diameter (m) | 131 | 4.870 | 4.305 |
| Crown point density (points/m³) | 100 | 1152.6 | 1069.1 |

It also shows "of which all four VALID: 16"; see §9, item 2.

**Workbooks 2–10** are earlier or subset versions of the same TLS results. Workbook 1 supersedes their values, so no separate statistics are given.

### 10.2 The 483 `.csv` files

All are in CH; there are none elsewhere on the drive. Judging by their headers, every one is type **(b), TLS results**, or **(d), other** (manifests, hashes, provenance, package lists). **None is (a) a field inventory or (c) a matching table.**

| Group | Files | Header or location | Type |
|---|---|---|---|
| ITSMe per-tree run outputs | 222 + 50 | `results\ITSMe_*tree_*\` | (b) |
| Batch-quality diagnostics | 29 | `stable_tree_id, crown_min_z_m, …` | (b) |
| Lean-corrected DBH tables | 47 + 42 | `tree, height_m, diameter_m, …` and `tree, axis_source, …, dbh13_m` | (b) |
| Selection and manifest files | 96 | `selection_group, rank, …` | (d) |
| Hash lists | 31 | `path, sha256` | (d) |
| FINAL, v1, v2 and intermediate results and manifests | 5 + 5 | `tree_attributes.csv`, `outliers.csv` | (b) |
| Source snapshots | 1 each | `session3_codex_20261023\state\CloudCompare_review_v2_CURRENT.csv` and the Session 2 state file | (d) |
| Ownership mapping and inventories | several | `segmentation_v2_analysis\*.csv`, `segmentation_v2_correction\*.csv` | (d) |
| R package versions | 2 | `environment\*.csv` | (d) |
| File manifest | 1 | `HANDOVER\FILE_MANIFEST.csv` | (d) |

**Field-inventory questions** (height, DBH, species, tag, plot/quadrant, coordinates; same as TreeData.csv?; linking to segmented trees): **not applicable**, because no field inventory exists on the drive (§6).

**Possible link to field records:** only through stem coordinates. `tree_attributes.csv` has `stem_x` and `stem_y` (EPSG:32756). TreeData.csv, according to its audit output, has no coordinates, only site, quadrant and tag. So no direct link exists from the data on the drive.
