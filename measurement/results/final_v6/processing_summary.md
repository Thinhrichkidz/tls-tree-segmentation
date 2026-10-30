# All-163 ITSMe processing summary: version 6 (final, 28 Oct 2026)

**This folder is the current deliverable.** It supersedes v3 FINAL (`ITSMe_all163_output_v3_FINAL_20261023_201144/`, kept unchanged).
- The intermediate runs of 28 Oct (v4-v5d) are in `results/_superseded_20261028_v4_v5_runs/`.
- Their change notes and method notes are copied into `history/` here.

All human approvals remain PENDING. Nothing is field-validated: every accuracy figure below compares methods with each other.

## Results (163 trees)

| Metric | VALID | REVIEW | N/A | VALID median (range) | v3 VALID |
|---|---|---|---|---|---|
| Height (m) | **73** | 90 | 0 | 15.57 (9.39-27.18) | 53 |
| DBH (cm) | 42 | 44 | 77 | 26.82 (10.44-66.61) | 43 |
| DBH, ESTIMATED column only | | | | 40 trees | 0 |
| Crown base height (m) | 156 | 0 | 7 | 6.75 (1.00-19.00) | 156 |
| Crown projected area (m2) | 123 | 33 | 7 | 14.41 (3.37-90.11) | 131 |
| Crown envelope volume (m3) | 95 | 61 | 7 | 77.8 (5.5-1025.5) | 100 |
| **Crown volume, 1 m slab hulls (m3)** (new) | **122** | 34 | 7 | 47.0 (4.4-713.2) | - |

- Tree status: 82 SUCCESS, 81 PARTIAL SUCCESS, 0 FAILED (v3: 76 / 87 / 0). All four core values VALID: **16** trees (v3 reported 16; the correct v3 value is 14, see below).
- Any DBH (measured or ESTIMATED): **126 of 163** (v3: 80).
- DBH VALID went 43 -> 42 because edited clouds get a refitted stem axis, which is REVIEW by rule.

## What changed since v3 (details: `history/CHANGES_*.md`, sheet "Changes vs previous version")

### DBH
1. **v4 fit** (`scripts/dbh_v4.R`): points from 1.1-1.5 m pooled in the lean-corrected frame, robust (Huber) circle fit with outlier trimming.
2. **v4b fallbacks**, only for trees you marked NORMAL:
   - a small-stem RMSE floor of 2 cm;
   - a RANSAC trunk circle that must be hollow (<= 10 % of points inside).

Their values go only in "Estimated DBH (cm)" (ESTIMATED) and never enter the DBH column or the statistics.

Checks against the v3 values:

| Method | Comparison | Median | 90th percentile |
|---|---|---|---|
| v4 | hold-out, half the stem hidden | 3.8 % | 11.6 % |
| v4b floor | against v3 | 1.2 % | 3.8 % |
| v4b RANSAC | against v3 | 2.3 % | 7.7 % |

### Height (`scripts/height_refine_all163.py`)
1. **Top check:**
   - It is run on the current points.
   - Truncation is judged against the true crop footprint, a 57.33 x 55.00 m rectangle tilted 12.6 degrees (`manifests/roi.json`, `crop_rectangle`). The terrain-mesh edge also runs round holes inside the plot, which cannot cut a tree; the axis-aligned bounding box (used until the last update) misses clipped crowns.
   - Connectivity is recomputed with the original method.
2. **Trunk-centre foot:** 18 trees whose foot was the lowest observation have it moved under the trunk, using the stem axis or the released DBH circle. The ground-reliability rule is re-run at the new foot.
3. **Edited clouds:** the "cloud edited" reason is dropped when the refitted stem axis confirms the foot. The foot ground test never uses the tree points.

### Crown
1. **New gap-aware crown volume:** the sum of convex hulls of 1 m slabs.
   - It is stable: the 0.5 m slab sum differs by a median of 10 %, at most 25 %.
   - The single envelope is a median 1.6x (up to 3.8x) larger, because it fills the air between crown parts.
   - 27 trees whose envelope was REVIEW only for bridging gaps have a VALID slab volume.
2. **Envelope volume kept** for comparison with v3; its rules are unchanged.

### Known v3 issues fixed (from the repo README, independent check of 25 Oct)
- **Issue 1:** "all four core values VALID" was counted before the crown-size and height/DBH outlier pass, so it was too high. It is now recomputed after that pass.
- **Issue 2:** no check caught issue 1. A 16th validation check now does.
- **Issue 5:** the `status` column of `tree_attributes.csv` was empty. It now holds the tree status.
- **Issue 7, resolved:** tree_095. Its 36.7 cm DBH is correct, so its VALID status stands.
  - The 1.3 m slice shows a clean, hollow trunk ring of about 36 cm. The ITSMe fit and the hollow-trunk RANSAC (35.8 cm) sit on it with the same centre.
  - The 67-89 cm fits were pulled by dense understorey round the stem base (0.3-2.2 m).
  - Above 2.5 m, clear of the understorey, the stem is about 35-40 cm wide.
  - Evidence: `results/TREE095_DBH_CHECK_20261028/tree_095_dbh_check.png`.

### Source clouds (`CloudCompare_review_v2`)
- **Your edits (28 Oct):**
  - Re-cleaned: 045, 139, 023, 035 (twice), 039, 055, 094, 120, 121, 136, 137, 147.
  - Crown tops and fragments: 027, 082, 083, 099, 100, 124, 137.
- **Claude's edit, at your request:** 9 isolated floating points above the crown top were deleted (100: 3, 124: 1, 137: 4, 083: 1).
  - Backups and log: `session4_claude_20261028/backup_before_floating_point_removal_20261028/`.
  - Heights fell 4.0-9.5 m on those trees.
- **Baseline:** current hashes are in `session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv`.
  - Every earlier baseline is kept beside it.
  - All changes are logged in `BASELINE_CHANGE.json`.

### Your decisions
- DBH tree review: `results/DBH_USER_REVIEW_20261028/user_dbh_review.csv`.
- Height notes: `results/HEIGHT_USER_REVIEW_20261028/user_height_review.csv` (tree_090: top cut by the dataset).

### Update after the fragment decisions (28 Oct 2026, same folder)
- **078:** the detached upper-crown piece is confirmed as its own crown (`HEIGHT_USER_REVIEW_20261028/user_height_review.csv`, decision FRAGMENTS_OWN_CROWN). The cloud was not edited. Height REVIEW -> VALID.
- **082:** Claude deleted the low detached piece at your request. It was understorey or ground: 2,631 points, -0.4 to 3.1 m above ground, 1.7 m beside the trunk. Backup and log: `session4_claude_20261028/backup_before_fragment_removal_082_20261028/`.
  - Height REVIEW -> VALID.
  - Crown values are identical. But ITSMe's crown classification now returns nothing: before, the shrub had triggered its "first widening" rule at 0.25 m above the ground. The pipeline therefore uses its fallback (all points above the 10.75 m base), which by rule is REVIEW. It is the same 95,561 points as before.
- **Workbook before these changes:** `history/ITSMe_all163_results_before_078_082.xlsx`.

### Crown fallback rule (28 Oct 2026, same folder)
Where ITSMe's crown classification fails (13 trees), the crown is all tree points above the agreed crown base. This is no longer a REVIEW reason, only a labelled note.
- For 123 of the 143 trees where ITSMe did find a crown, its crown points above the agreed base are exactly all tree points above the base.
- The other 20 differ only where ITSMe starts its crown above the agreed base (e.g. tree_045: 13.5 m against 9.75 m).

Result:
- Crown area VALID 129 -> 141; slab volume 129 -> 140; envelope 102 -> 109.
- All four core values VALID 17 -> 18 (tree_037).
- No value changed. Tree 004 stays REVIEW (very small crown).

### Field check sheet
`results/FIELD_CHECK_SHEET_20261028/` (`scripts/field_check_sheet.py`): a printable sheet (13 trees, blank columns for tape and hypsometer values), a CSV and a plot map, with UTM and latitude/longitude. The trees are chosen to test:
- the all-VALID values (5 trees);
- each ESTIMATED DBH method (3);
- the floating-point cleaning (100, 124);
- the understorey DBH case (095);
- ground-uncertain heights (136, 016).

### True tilted crop outline (28 Oct 2026, same folder)
Edge distances (height top check, crown-edge flag, stem distance) now use the true crop footprint, a 57.33 x 55.00 m rectangle tilted 12.6 degrees. It is the same rectangle as `results/EDGE_RECHECK_20261026`, now stored in `manifests/roi.json`. They previously used the axis-aligned bounding box, which over-cleared tops and left clipped crowns unflagged.
- No value changed.
- Height VALID 83 -> 73: tops of 085, 126, 128, 129, 130, 131, 132, 135, 138 and 161 reach the true edge near the tip.
- 21 crowns touch the true edge (crown area and volume REVIEW), matching the report's edge check.
- Crown area VALID 141 -> 123; slab volume 140 -> 122; envelope 109 -> 95; all four VALID 18 -> 16.
- Workbook before this change: `history/ITSMe_all163_results_before_tilted_crop.xlsx`.

## Checks
- **Validation:** all **16** automatic checks pass (`logs/validation.json`).
  - New check: tree status and the all-VALID count are recomputed from the exported per-metric statuses.
  - Against v3 FINAL, every value change has a recorded reason: a re-cleaned cloud, a moved foot or a user-reviewed crown.
  - 44 trees changed; 179 rows in the changes sheet.
- **Independent recalculation** of 24 trees (`logs/independent_verification.*`, no ITSMe):
  - Height agrees within 2e-10 m, including tree_112 at its moved foot.
  - DBH median difference 0.26 cm.
- **Excel:** the workbook opened read-only in Excel; 8 sheets, 163 rows, status colours correct (`logs/excel_open_check.json`).
- **Run:** 55 R workers. Preparation 65 s, measurement 54 s, whole notebook 219 s. 0 failures, 0 retries.

## Open items
- **083 (your decision, 28 Oct: left as is, check at home):** your earlier edit removed 306 dense crown points at 15-18 m above ground (5th-neighbour spacing ~5 cm, i.e. real crown, not noise); the dense crown top fell from 17.45 m (23 Oct) to 16.57 m, so the reported height 16.77 m is probably ~0.7 m short. The 23 Oct points are in `measurement_pipeline/results/ITSMe_all163_output_v3_FINAL_20261023_201144/per_tree/tree_083/tree_083_local_xyz.txt` (local frame; add the translation in its prep.json) if you want to restore them.
- **137:** the refitted stem axis meets the ground 1.09 m from the foot. **105:** a fork below 1.3 m (split, or leave DBH N/A).
- **Height:** 82 REVIEW, mostly real ground uncertainty at the stem foot (69 trees). Needs better ground data or visual review.
- **Crown fallbacks:** resolved, see above. Tree 004 stays REVIEW (very small crown).
- **Validation:** no field (tape/caliper) measurements exist.

## Files
| File | What it is |
|---|---|
| `ITSMe_all163_results.xlsx` | Main workbook. 8 sheets; "Changes vs previous version" compares with v3 FINAL. |
| `results/` | `tree_attributes.csv` (now with `dbh_estimated_cm`, `crown_volume_slab_m3`), `methods.json`, `summary.json`, `outliers.csv`, `sensitivity.csv`, `height_refine.csv` |
| `logs/` | `validation.json`, `independent_verification.*`, `excel_open_check.json`, timing, environment, worker logs |
| `history/` | Change notes v4c-v5d, DBH method notes, and earlier workbooks of this run (compared with v5d; before the status fix; before 078/082; before the crown fallback rule) |
| `ITSMe_all163_processing.ipynb` | Executed notebook (`notebooks/ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb`) |
