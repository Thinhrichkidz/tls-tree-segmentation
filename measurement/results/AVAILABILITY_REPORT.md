# Availability report: INFO6003 per-tree attributes

This is the final step of `REPORT_DATA_REQUEST.md`. Written 25 October 2026 by Claude Code from files on the drive.

**What this report covers:**
- The measured dataset: `measurement_pipeline/results/ITSMe_all163_output_v3_FINAL_20261023_201144/` (called **FINAL**, run 23 Oct 2026).
- The figures: `measurement_pipeline/results/ITSMe_all163_visualisations_20261023_202459/` (called **VIS**).
- The 163 source clouds in `CloudCompare_review_v2/`. Their SHA-256 values were re-checked on 25 Oct 2026 against `session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv`: 163 of 163 match.

**What was and wasn't changed:**
- No source cloud, FINAL file or VIS file was modified, and nothing was recomputed.
- This report corrects four "not obtained" statements in FINAL (`methods.json`, `summary.json`, `FINAL_AUDIT_REPORT.md`) after a wider search of the drive. Those corrections are marked **[corrected 25 Oct]**.

**Paths:**
- Paths starting with `Codex_help/` are relative to `D:\22083142\outputs\WSL_ML2A\55x55\3cm\Codex_help`.
- Paths starting with `D:\22083142\` lie outside it.
- FINAL and VIS paths are relative to `Codex_help/measurement_pipeline/results/`.

---

## 1. Obtained

### Priority 1 (core outputs)

| # | Item | File | Notes |
|---|---|---|---|
| 1 | Per-tree attributes, one row per tree (163 rows, all 30 requested columns, plus status columns) | `FINAL/results/tree_attributes.csv` | `status` is `NA` for every tree (see §2). The workbook `FINAL/ITSMe_all163_results.xlsx` holds the same values plus QC reasons, colour coding and methods sheets |
| 2 | Methods record (software, units, definitions, parameters, script SHA-256 values) | `FINAL/results/methods.json` | Its "Not obtained" list is partly out of date; see §2 |
| 3 | Dataset counts | `FINAL/results/summary.json` | Two NA items can now be filled; see §2 rows C2 and C3 |

### Priority 2 (quality and robustness)

| # | Item | File | Notes |
|---|---|---|---|
| 4 | Outliers to check manually (99 flags) | `FINAL/results/outliers.csv` | 83 failed or missing DBH fits, 7 very large and 7 very small crowns, 1 very low stem completeness, 1 crown touching the ROI edge. No height/DBH-ratio flags were raised. Flags only; nothing was removed |
| 5 | Sensitivity tests on 8 trees | `FINAL/results/sensitivity.csv` | DBH with 3, 5, 6 and 10 cm slices; circle fit vs. convex hull; maximum vs. 99th-percentile height; crown envelope vs. 1 m slab hulls. Crown volume was not tested at two alpha/voxel settings, because the method is a convex envelope with no such parameter |
| 6 | Run time and machine | `FINAL/results/summary.json` (`run_time`), `FINAL/logs/run_timing.json`, `FINAL/logs/environment.json` | See below |

**Item 6 details:**
- **Run time:** preparation 64.3 s; measurement 51.8 s with 60 workers; per tree median 4.0 s, maximum 48.8 s.
- **Machine:** AMD Threadripper 7980X, 64 physical cores, 383 GB RAM, Windows 10.
- **Software:** R 4.5.2, ITSMe 2.0.0, Python 3.13.14.

### Figures

All figures are 300 dpi PNG, plus PDF for the report figures.

| Requested | Closest existing file | Notes |
|---|---|---|
| `height_vs_dbh.png` | `VIS/report_figures/dbh_vs_height.png` (+ `.pdf`) | Different file name. VALID pairs only (n = 23); the curve fit is descriptive |
| `distributions.png` | `VIS/report_figures/tree_height_distribution.png`, `dbh_distribution.png`, `crown_volume_distribution.png` (+ `crown_area_distribution.png`) | Separate files, not one combined panel |
| `example_trees.png` | `VIS/individual_trees/tree_069_3D_sideviews.png`, `tree_146_3D_sideviews.png` (recommended in `VIS/visualisation_summary.md`); 163 per-tree figures in total | Separate files, not one figure at a common scale |
| `tree_map.png` | not produced | See §2 |
| `before_after_example.png` | not produced | See §2 (D1) |
| (extra) | `VIS/comparisons/` (8 grids: tallest and shortest 8, largest and smallest DBH and crown area, segmentation-quality comparison, unusual structures); `VIS/report_figures/measurement_status_counts.png`, `dbh_vs_crown_area.png`, `height_vs_crown_area.png` | Validated (`VIS/logs`) |

---

## 2. Not obtained, or obtained only in part

### A. Data absent from the drive

| Item | Reason | Needs |
|---|---|---|
| `status` (accepted / uncertain / discarded) in `tree_attributes.csv` | No per-tree acceptance records exist for the current clouds; all human approvals are PENDING | Thomas's decision labels |
| Item 8: `refinement_log_summary.csv` | No refinement time or edit log was kept for the manual correction. Times must not be reconstructed | Not obtainable |
| Item 9: `field_matches.csv` | No field inventory spreadsheet is on the drive (searched 25 Oct). The report draft audits `TreeData.csv` (SHA-256 `fb308df06f97…`, 1,508 rows), but that file is not on the drive either. The draft also says the validation reference is a separate Excel inventory | The Excel inventory, its columns, and any tags or coordinates |
| Item 10: diameter-distribution comparison | Needs the inventory for plot WSL_ML2A | As above |
| Field accuracy and validation statistics | No reference data | As above |

### B. Parameters and settings never recorded

| Item | Reason |
|---|---|
| Rayextract parameters actually used (`gradient`, `height_min`, `max_diameter`, others) | Not in any file on the drive. `D:\22083142\tls-tree-segmentation\docs\WORKFLOW.md` shows only the pipeline document's example (`--gradient 2`, `--max_diameter 0.9 --height_min 10`) for a different plot (DSF_CP1B). That is **not** evidence for WSL_ML2A |
| Downsampling method and settings | The 3 cm resolution is known from the file names. How it was made is not recorded. The crop PLY headers say "Created by CloudCompare v2.13.2, 2026-09-25" |
| Step 3 `--distance_th` | Not recorded |

### C. Corrections to FINAL's "not obtained" statements [corrected 25 Oct]

| # | FINAL said | What the drive shows | Consequence |
|---|---|---|---|
| **C1 (D1)** | `methods.json` / `FINAL_AUDIT_REPORT.md` R7: "unedited Rayextract output not kept", so `before_after.csv` is not applicable | **The unedited RayCloudTools output exists.** It is in `D:\22083142\outputs\WSL_ML2A\55x55\3cm\` (details below) | **Item 7 (`before_after.csv`, with IoU) and `before_after_example.png` are possible.** They were not produced in this step (§3, A4) |
| **C2 (D2)** | `summary.json`: points before/after downsampling "NA (not recorded)" | The LAS headers record point counts at each resolution (table below) | The counts are available. The downsampling method is still unrecorded (§2 B) |
| **C3 (D1)** | `summary.json`: Rayextract segment count "NA" | `trees/clouds/` holds 162 per-tree files from `treesplit`, IDs 0–161. RayCloudTools wrote 28,708,304 of the 45,449,820 points to trees and 16,741,516 to `unassigned/…_segmented_-1.ply` (header counts) | **162 automated segments** (55x55 / 3 cm run). Whether all 162 are trees, not non-tree objects, was not checked |
| **C4 (D3)** | `HANDOVER/NEXT_STEPS.md` #1 asks whether a full-resolution scan exists; FINAL notes the limit of 3 cm spacing for DBH | It exists (same crop): `D:\22083142\data\cropped\WSL_ML2A\55x55\full\WSL_ML2A_crop_55x55_full.ply` / `.laz`, 234,060,453 points. The raw 1 cm scan is `D:\22083142\data\raw\WSL_ML2A\2025-05-12_WSL_ML2A_1cm_all.laz` (355,462,232 points) | Re-fitting thin-stem DBH at full resolution is possible, as a new and separately documented method version |
| **C5 (D4)** | `summary.json`: ROI = "WSL_ML2A_crop_55x55"; boundary assumed to be the axis-aligned XY bounding box of the 3 cm crop | That bounding box is **65.71 m × 67.84 m**, not 55 × 55 m. The 35x35 crop really is 35.00 × 35.00 m (LAS headers). The true shape of the "55x55" crop is unknown | `dist_to_roi_edge_m` and `flag_crown_touches_edge` (1 tree) are computed against that box. They are only correct if the crop is a box; treat them as **provisional** |

**C1 details: where the unedited output is** (all in `D:\22083142\outputs\WSL_ML2A\55x55\3cm\`, dated 25 Sep 2026):
- `trees/clouds/WSL_ML2A_crop_55x55_3cm_raycloud_segmented_0.ply` … `_161.ply`: 162 per-tree clouds, 28,708,304 points, header "generated by raycloudtools library".
- `segmentation/WSL_ML2A_crop_55x55_3cm_raycloud_segmented.ply`: the whole plot.
- `unassigned/…_segmented_-1.ply`, `metadata/…_raycloud_trees.txt` and `trees/metadata/`.

**C1 caveat on matching:** a refined file's number does **not** reliably identify its automated tree.
- 96 of the 163 V2 exports (`manual_seg_v2`) have the same point count as the same-numbered automated file; 67 differ.
- V2 has a `segmented_162` (there is no automated 162) and a `segmented_88 - Cloud.remaining.ply`.
- So pairs must be found by point or XYZ overlap.

**C2: point counts by resolution** (from the LAS headers):

| Cloud | Full | 2 cm | 3 cm |
|---|---|---|---|
| WSL_ML2A 55x55 crop (used) | 234,060,453 | 84,276,295 | 45,449,820 |
| WSL_ML2A 35x35 crop (not used) | 110,682,307 | 39,013,447 | 20,543,086 |
| WSL_ML2A raw scan, 1 cm, whole extent 450 × 754 m | 355,462,232 | – | – |

### D. Correction to a FINAL count (found while writing this report)

FINAL `summary.json` (`trees_all_core_valid`), `processing_summary.md`, `FINAL_AUDIT_REPORT.md` §B and the workbook's Summary sheet all say **16** trees have all four core metrics VALID. The per-tree statuses in the same folder give **14**.

**Where the two extra trees come from:**
- tree_069 and tree_146 are crown-size outliers, so their crown area and volume are REVIEW (per `tree_attributes.csv` and `logs/records.json`).
- `all163_postprocess.py` sets the `all_core_valid` flag (line 188) **before** the outlier rule demotes those crowns to REVIEW (about line 240). The flag is never recomputed.
- The same flag also colours the tree-status cell, so those two trees are likely coloured green in the workbook.

**What is not affected:** the per-metric statuses and values, and the totals of 76 SUCCESS and 87 PARTIAL. **Use 14 in the report.** FINAL was not edited; fixing it means a new rebuild into a new folder (§3, A5).

### E. Partly obtained

**`AVAILABILITY_REPORT.md` location:** the request asked for `results/`. FINAL is a validated folder and must not be edited, so this report is in its own folder instead.

**Prepared but blocked:**
- `before_after.csv` and `before_after_example.png`: blocked only by the matching decision (§4, Q4/Q5).
- `tree_map.png`: blocked by the unknown ROI boundary (C5) and by the missing quadrant grid.

---

## 3. Assumptions

These are assumptions made in FINAL (with their source) and in this report.

1. **Tree identity:** `tree_NNN` = V2 export number NNN−1, via `segmentation_v2_analysis/stable_tree_ids.json`. Never inferred from sorted file names.
2. **CRS:** EPSG:32756 (WGS 84 / UTM 56S, ellipsoidal heights), taken from project records and the source LAS WKT. Not re-surveyed.
3. **Height:** the highest point of the tree minus the terrain-mesh height at the stem foot. The foot is where the low-stem axis meets the mesh. When no axis exists, a fallback foot is used: the lowest observation, marked REVIEW.
   - Trees 103 and 108 use bases corrected by the user.
   - The 99th-percentile alternative is in `sensitivity.csv`.
4. **DBH:** measured 1.3 m **along the lean-corrected stem axis** from the foot ground, not vertically.
   - **Fit:** 6 cm slice; ITSMe `dbh_pc` circle fit.
   - **Screen:** 3–200 cm, arc ≥ 0.60, RMSE ≤ min(4 cm, max(1 cm, 10% of diameter)).
   - **Fallback:** the median of accepted 1.1–1.5 m slices, labelled REVIEW.
   - Failed fits are kept in a separate "unaccepted" column, not in `dbh_cm`.
   - **User decisions:** 067 uses an outline filter; 103 also gets an area-equivalent diameter (oval trunk); 033 is not released; 108 is provisional.
5. **Crown:**
   - **Crown base:** the user-agreed rule (first 0.25 m layer above 1 m wider than max(3 × trunk width, 0.3 × widest layer), with ≥ 70% crown layers above), or the user's choice for 61 trees. Seven trees have no live crown and are N/A.
   - **Area:** concave hull, concavity 3.
   - **Volume:** a 3D convex envelope, which **includes air gaps**. It is **not** wood volume or biomass.
6. **ROI:** one ROI, `WSL_ML2A_crop_55x55`, with its boundary assumed to be the crop's XY bounding box (questioned in C5).
7. **"Accepted trees" in §5:** there are no accepted / uncertain / discarded labels, so §5 uses the closest defensible subset: values whose status is **VALID**. It reports per-metric VALID values and the 14 trees with all four core metrics VALID. VALID is a documented numerical rule, not human acceptance or field validation.
8. **Not done:** no estimates, no tree age, no biomass (data-request rules 1, 5 and 6).
9. **Corrections C1–C5:** based on file headers, sizes and names only. No point payloads were compared, so the content of the automated clouds was not checked beyond their headers.

---

## 4. Questions for Thomas

1. **Rayextract settings:** which `rayimport` / `rayextract terrain` / `rayextract trees` parameters and which RayCloudTools version produced the 25 Sep 2026 outputs?
2. **Downsampling:** how was the 3 cm cloud made (tool, method), and what was filtered before cropping?
3. **ROI shape:** the "55x55" crop spans 65.7 × 67.8 m. What is its true boundary (a rotated square, a polygon)? Is there a boundary file or a quadrant grid?
4. **Before/after baseline:** which refined version should `before_after.csv` compare with the automated trees: round 1 (`trees/cloud_correct`, 199 files), V2 (`cloud_correct_v2`, 163), or the current `CloudCompare_review_v2`?
5. **V2 file names:** were the round-2 exports renamed to automated tree numbers? (67 do not match by point count.)
6. **Status labels:** do you want accepted / uncertain / discarded labels per tree? Otherwise `status` stays NA.
7. **Field data:** where are `TreeData.csv` and the Excel field inventory? Do they contain height and in-plot coordinates or tags for WSL_ML2A?
8. **The count of 16:** should FINAL be rebuilt (into a new folder) to fix the 16 → 14 all-VALID count and the tree-status colours of 069 and 146?

---

## 5. Quick numbers

**Trees processed:** 163 of 163.
- 76 SUCCESS: all four core metrics have a value.
- 87 PARTIAL SUCCESS.
- 0 FAILED.
- **Trees with all four core metrics VALID: 14** (not 16; see §2 D).

**Per-metric VALID values only** (from `FINAL/results/tree_attributes.csv`; matches `summary.json` statistics):

| Metric | n VALID / 163 | Median | Range |
|---|---|---|---|
| Height (m) | 53 | 15.40 | 10.31–27.18 |
| DBH (cm) | 43 | 26.79 | 10.44–66.61 |
| Crown envelope volume (m³) | 100 | 85.7 | 5.5–972.7 |

**Subset of the 14 trees with height, DBH, crown area and crown volume all VALID:**

| Metric | Median | Range |
|---|---|---|
| Height (m) | 16.52 | 10.54–27.05 |
| DBH (cm) | 19.87 | 13.38–66.61 |
| Crown envelope volume (m³) | 80.7 | 18.8–856.5 |

**Denominators to quote:**
- **Height:** 110 REVIEW.
- **DBH:** 37 REVIEW and 83 N/A. `dbh_fit_ok = FALSE` for 83 trees.
- **Crown volume:** 56 REVIEW and 7 N/A.
- **ESTIMATED:** none.

None of these values is field-validated, and all human approvals are PENDING.
