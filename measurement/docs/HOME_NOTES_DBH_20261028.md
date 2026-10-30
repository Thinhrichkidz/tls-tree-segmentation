# Work of 28 Oct 2026 (DBH, height, crown volume): notes for home

## Start here: the final package
- **Results:** `measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/`. Read `processing_summary.md` first.
  - Workbook: `ITSMe_all163_results.xlsx`. Its sheet "Changes vs previous version" lists every change since v3 FINAL.
  - All 16 checks pass. The independent recalculation of 24 trees agrees, and the workbook opens in Excel.
  - `history/` holds the step-by-step change notes (v4c-v5d) and the DBH method notes.
- **Figures:** `measurement_pipeline/results/ITSMe_all163_visualisations_v6_20261028/`. Read `visualisation_summary.md`.
  - 163 tree figures, 8 grids and 9 report charts, all validated.
- **Notebook:** `measurement_pipeline/notebooks/ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb`.
  - Run it with `scripts/run_all163_notebook.py --out <folder> --notebook ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb`.
- **Intermediate runs (v4-v5d):** archived in `measurement_pipeline/results/_superseded_20261028_v4_v5_runs/`.
- **v3 FINAL:** kept unchanged as the last audited version before this work.

## Results (v6 FINAL) against v3
Edge checks use the true tilted crop outline (57.33 x 55.00 m, tilted 12.6 degrees) since the last update; that put 10 heights and 18 crowns back to REVIEW.

**Report:** `report_v8/` (v8 PDF, 12 pages, numbers checked against this run; read `revision_notes_v8.md`). v7 is unchanged.

| Metric | VALID | REVIEW | N/A | v3 VALID |
|---|---|---|---|---|
| Height | **73** | 90 | 0 | 53 |
| DBH | 42 | 44 | 77 (40 of these have an ESTIMATED value) | 43 |
| Crown area | 123 | 33 | 7 | 131 |
| Crown envelope volume | 95 | 61 | 7 | 100 |
| **Crown volume, 1 m slab hulls** (new) | **122** | 34 | 7 | - |

- Any DBH (measured or ESTIMATED): **126 of 163** (v3: 80).
- Tree status: 82 SUCCESS / 81 PARTIAL (v3: 76 / 87). All four core values VALID: **16** (v3: 14 after correcting its counting bug).

## What was improved (methods in `processing_summary.md`)
- **DBH:**
  - pooled robust fit (v4);
  - small-stem RMSE floor and hollow-trunk RANSAC (v4b), only for trees you marked NORMAL.
  - Results go only in the "Estimated DBH (cm)" column.
- **Height:**
  - The top check runs on the current points, against the plot crop boundary, not terrain-mesh holes.
  - 18 fallback feet were moved under the trunk.
  - Edited clouds are not flagged when the refitted stem axis confirms the foot.
  - Floating points above the crown were removed.
- **Crown:** a new gap-aware volume, the sum of 1 m slab convex hulls. The single envelope is kept for comparison.

## Source clouds changed on 28 Oct (`CloudCompare_review_v2`)
- **Your edits:**
  - 045, 139, 023, 035 (twice), 039, 055, 094, 120, 121, 136, 137, 147;
  - crown tops and fragments: 027, 082, 083, 099, 100, 124, 137.
- **Claude's edit, at your request:** 9 floating points above the crown top deleted on 100 (3), 124 (1), 137 (4) and 083 (1).
  - Byte-identical backups and a log: `session4_claude_20261028/backup_before_floating_point_removal_20261028/`.
- **Baseline:** current hashes are in `session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv`.
  - Every earlier baseline is kept beside it; all changes are logged in `BASELINE_CHANGE.json`.
- **tree_121_UNCHANGED.ply was edited.** Its filename still says UNCHANGED.
- **Crown changes from the edits:**
  - tree_120 crown 249 -> 69 m3: intentional, the removed points were not this tree.
  - tree_045 crown 14.6 -> 2.4 m3.
  - tree_035 crown 100 -> 80 m3: points above its 3.0 m crown base were removed.

## Your decision files
- DBH: `measurement_pipeline/results/DBH_USER_REVIEW_20261028/user_dbh_review.csv`.
  - 19 POOR_DATA, 4 SPECIAL, 20 NORMAL; v4b fits for 105 and 136 rejected.
- Height: `measurement_pipeline/results/HEIGHT_USER_REVIEW_20261028/user_height_review.csv`.
  - tree_090: top cut by the dataset; height is a lower bound.

## Open items
- **078 / 082 fragments: done.** 078 confirmed as its own crown; 082 low piece deleted by Claude (backup in `session4_claude_20261028/backup_before_fragment_removal_082_20261028/`). Both heights VALID. 082 crown is now REVIEW only because ITSMe no longer classifies a crown (fallback gives identical values).
- **083 (your decision, 28 Oct: left as is, check at home):** your earlier edit removed 306 dense crown points at 15-18 m above ground (5th-neighbour spacing ~5 cm, i.e. real crown, not noise); the dense crown top fell from 17.45 m (23 Oct) to 16.57 m, so the reported height 16.77 m is probably ~0.7 m short. The 23 Oct points are in `measurement_pipeline/results/ITSMe_all163_output_v3_FINAL_20261023_201144/per_tree/tree_083/tree_083_local_xyz.txt` (local frame; add the translation in its prep.json) if you want to restore them.
- **137:** the refitted stem axis meets the ground 1.09 m from the foot. Check the stem base.
- **105:** a fork below 1.3 m. Split it into two clouds, or leave the DBH N/A.
- **Height:** 80 REVIEW, mostly real ground uncertainty at the stem foot (69). Needs better ground data or visual review.
- **095: resolved.** 36.7 cm is correct; understorey round the base inflated the other fits (`results/TREE095_DBH_CHECK_20261028/`).
- **Crown fallbacks: resolved.** ITSMe failing is no longer a REVIEW reason, because its crown above the agreed base is exactly all points above it on 123 of 143 trees.
- **Field day:** print `measurement_pipeline/results/FIELD_CHECK_SHEET_20261028/FIELD_CHECK_SHEET.xlsx` (13 trees, map included).
- **No field measurements:** every accuracy figure compares methods with each other. Tape or caliper measurements of 10-15 trees would show real accuracy.

## The 37 trees with no DBH

### Bad dataset: your decision (19 trees)
001, 005, 011, 013, 023, 030, 035, 044, 046, 055, 101, 111, 122, 133, 137, 141, 143, 147, 158

- 023, 035, 055, 137, 147: cleaned but still failing; you decided not to clean further.
  - **035:** fits say about 18-19 cm, but the 1.4 m slice is 5 cm wider than the rest.
  - **055:** about 7 cm stem, too thin for 3 cm point spacing.
  - **137:** under 60 % of the stem was scanned.
- 030, 133: too poor to clean.

### Special cases: your decision (4 trees)
| Tree | Reason |
|---|---|
| 026, 097 | Missing roots / middle section of the stem. |
| 163 | Stem not straight, leans to one side. Would need a tilted-axis fit. |
| 105 | Fork below 1.3 m: two stems on one trunk. Splitting it into two clouds would let each stem be measured. |

### Earlier decisions, 23 Oct (2 trees)
| Tree | Reason |
|---|---|
| 033 | Not released: poor source data, stem base missing. |
| 108 | About 9 cm stem, too thin for 3 cm spacing. Provisional only. |

### Not reviewed in CloudCompare (12 trees)
These fail on the data. You have not looked at them.

| Trees | Reason |
|---|---|
| 003, 006, 019, 031, 032, 077, 090 | Less than 40 % of the stem visible at 1.1-1.5 m (occluded or one-sided scan). |
| 004, 012 | Almost no points on the stem at 1.3 m. |
| 079 | No stem axis; fitted radius disagrees with the radial profile. Also the very large crown (228.7 m2) flagged in v3. |
| 129 | Stem size differs too much between heights. |
| 130 | Fit gives 6.05 cm on a 10.4 m tree: height/DBH ratio 171 is implausible, so the value is withheld. |
