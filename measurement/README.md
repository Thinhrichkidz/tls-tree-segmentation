# Step 5: tree measurements (height, DBH, crown) for the 163 corrected trees

Tool: ITSMe (R) driven from Python/Jupyter. Input: the 163 manually corrected tree clouds of WSL_ML2A 55x55 / 3 cm (not in this repo, see the main README).

| Folder | Contents |
|---|---|
| `results/final_v6/` | **Current results (28 Oct 2026).** Workbook, `tree_attributes.csv`, `methods.json`, `summary.json`, `outliers.csv`, `sensitivity.csv`, `height_refine.csv`, `processing_summary.md` (read first), validation logs, executed notebook, and `history/` with the step-by-step change notes |
| `results/dbh_user_review/`, `results/height_user_review/` | The user's CloudCompare decisions used by v6 |
| `results/field_check_sheet/` | Printable field sheet for 13 trees (tape/hypsometer), CSV and plot map |
| `results/dbh_v4_experiment/`, `results/dbh_v4b_experiment/` | Tests behind the new DBH methods (hold-out and comparison with v3) |
| `results/final_v3/` | Previous final (23 Oct), kept unchanged. Audited results: `ITSMe_all163_results.xlsx`, `tree_attributes.csv`, `methods.json`, `summary.json`, `outliers.csv`, `sensitivity.csv`, `FINAL_AUDIT_REPORT.md`, `processing_summary.md`, executed notebook |
| `results/preliminary/` | Early height-only ranking of all exports and its method |
| `results/AVAILABILITY_REPORT.md` | Which requested data could and could not be produced |
| `notebooks/` | `ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb` (batch notebook for v6), `ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v3.ipynb` (used for v3) and `ITSMe_DBH_lean_correction.ipynb` |
| `scripts/` | Preparation, batch run, validation, workbook and figure scripts |
| `figures/` | `report_figures_v6/` + `visualisation_summary_v6.md` (current); `report_figures/` (v3); QC side views |
| `docs/` | Data request and results/limitations notes |

Status (from `FINAL_AUDIT_REPORT.md` / `processing_summary.md`): all human approvals are pending and nothing is field-validated. Many values are flagged REVIEW or N/A rather than estimated.

Scripts and notebooks contain absolute paths from the original workstation (`D:\` / `G:\`); set the project root to your own copy before running. They need the full tree clouds, which are not in the repo.

## Version 6 (28 Oct 2026)

`results/final_v6/` supersedes `final_v3/`. Main changes (details in `results/final_v6/processing_summary.md`):

| Metric | v6 | v3 |
|---|---|---|
| Height VALID | 73 | 53 |
| Any DBH (measured or ESTIMATED) | 126 | 80 |
| Gap-aware crown volume (1 m slab hulls) VALID | 122 | new |
| Crown projected area VALID | 123 | 131 |
| All four core values VALID | 16 | 14 (16 as reported) |

- **DBH:** new robust and fallback fits. Their values go only in an ESTIMATED column.
- **Height:**
  - top and connectivity re-checked on the current points;
  - truncation judged against the plot crop boundary;
  - feet moved under the trunk for 18 fallback trees.
- **Crown:** a new slab-hull volume.
- **Crop edge:** truncation and edge flags use the true tilted crop rectangle (`results/final_v6/manifests/roi.json`), not the bounding box.
- **Source clouds:** several clouds were re-cleaned by the user.

Known issues 1, 2 and 5 below are fixed in v6:
- the all-VALID count is recomputed after the outlier pass;
- a 16th validation check verifies it;
- the `status` column is filled in.

Issue 7 is resolved: tree_095's 36.7 cm DBH is correct. The 80.9 cm fit was pulled by understorey round the stem base (`results/tree095_dbh_check/`). Issue 3 is fixed in v6 (`methods.json` now says the unedited output is kept; RQ1 rerun in `results/rq1_before_after_20261028/`). Issues 4, 6 and 8 are not addressed.

## Known issues (in `results/final_v3/`)

The files in `results/final_v3/` are uploaded exactly as produced. An independent check of them (25 Oct 2026) found the following. The scripts were not changed to fix them.

| # | Where | Issue | Effect |
|---|---|---|---|
| 1 | `summary.json`, `processing_summary.md`, workbook | `all_core_valid` is set before the crown area/volume outlier pass (5th to 95th percentile) demotes values to REVIEW (`scripts/all163_postprocess.py`, `assess()` vs the later outlier loop) | They report 16 trees with all four core metrics VALID; the correct count is **14** (tree_069, tree_146). The report uses 14. |
| 2 | `scripts/all163_postprocess.py`, `validate()` | None of the 15 checks compares the all-VALID count with the per-metric statuses | "15/15 checks passed" does not cover issue 1. |
| 3 | `methods.json`, "Not obtained" | Says the unedited RayCloudTools output was not kept | Wrong: the 162 automated trees exist (`trees/clouds`, 8 of them sampled in `samples/automated_segmentation/`). |
| 4 | `results/final_v3/sensitivity.csv` | `scripts/sensitivity_all163.R` is not in the script hashes in `methods.json`, and was modified after `sensitivity.csv` was written | `sensitivity.csv` may not match the current script. |
| 5 | `tree_attributes.csv`, column `status` | Empty for all 163 trees | The tree status is only in the workbook. |
| 6 | scripts, manifests | Absolute `G:\22083142\...` paths; the worker asserts the file hash at that path | Not portable without editing the paths. |
| 7 | tree_095 | `dbh_pc` gives a DBH of 36.7 cm, but a plain least-squares circle fit on the same slice gives 80.9 cm (stem lean 17.3 degrees) | One of the 14 all-VALID trees may have a wrong DBH; not yet inspected. |
| 8 | Status rules (`assess()`) | Several REVIEW triggers (two or more clusters at 1.3 m, fallback foot, highest point more than 0.5 m above the supported top, cloud edited after QC) are not described in the report's Table 3 | Applying Table 3 as written gives 69 VALID heights and 66 VALID DBHs, not the reported 53 and 43. |
