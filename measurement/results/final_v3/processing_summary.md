# All-163 ITSMe processing summary: version 3 (final, audited)

Run 23 October 2026, 20:11 (Australia/Sydney), by Claude. **This folder is the final deliverable.** Earlier versions are kept unchanged:
- `ITSMe_all163_output_20261023_194253` (v1, automatic crown bases)
- `ITSMe_all163_output_v2_20261023_195000` (v2, your crown-base choices for 55 trees)
- `_superseded_all163_audit_intermediate_runs/` (two intermediate audit runs with numbers identical to this one)

The audit findings are in `FINAL_AUDIT_REPORT.md`.

`CloudCompare_review_v2` was only read. No estimates were made (`REPORT_DATA_REQUEST.md` rule 1). All human approvals are PENDING, and nothing is field-validated.

## What v3 changed relative to v2

**Measured values: none.** All 163 trees reproduce v2 exactly.

**Status changes only (12 trees, all listed in the sheet "Changes vs previous version"):**
1. **tree_102: height and DBH VALID → REVIEW.** Its stem axis meets the ground 0.38 m from the foot used for its ground height. This was an open issue from the handover that v2 did not show.
2. **Crowns outside the 5th–95th percentile of crown areas: VALID → REVIEW.**
   - very large: 026, 041, 069, 079, 084, 110, 132
   - very small: 044, 146, 151, 158
   - tree_079 (228.7 m²) is the main concern, because it is far larger than any other.

**Added:**
- `results/sensitivity.csv`
- independent recalculation of 24 trees (`logs/independent_verification.*`)
- filters on the main tables
- script SHA-256 hashes in `methods.json`
- peak memory per tree
- 15 automatic validation checks (previously 10)

## Execution

| Item | Value |
|---|---|
| Machine | AMD Threadripper 7980X, 64 cores / 128 threads, 383 GB RAM, Windows 10; R 4.5.2, ITSMe 2.0.0, Python 3.13.14 |
| Notebook | `measurement_pipeline/notebooks/ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v3.ipynb`; executed copy `ITSMe_all163_processing.ipynb` |
| Preparation | 48 processes, 64 s |
| Measurement | 60 R workers, 52 s; per tree median 3.9 s, max 48 s (tree_079) |
| Whole notebook | 142 s |
| Peak R memory per tree | median 225 MB, max 843 MB (tree_079); allowance 4 GB per worker |
| Worker failures / retries | 0 / 0 |

## Results (163 trees)

- **SUCCESS: 76.** Height, DBH, crown area and crown volume all have values; 16 of these have all four VALID.
- **PARTIAL SUCCESS: 87.**
- **FAILED: 0.**

| Metric | VALID | REVIEW | N/A | ESTIMATED | VALID median (range) |
|---|---|---|---|---|---|
| Height (m) | 53 | 110 | 0 | 0 | 15.40 (10.31–27.18) |
| DBH (cm) | 43 | 37 | 83 | 0 | 26.79 (10.44–66.61) |
| Crown base height (m) | 156 | 0 | 7 | 0 | 6.75 (1.00–19.00) |
| Crown projected area (m²) | 131 | 25 | 7 | 0 | 14.55 (3.39–90.11) |
| Crown envelope volume (m³) | 100 | 56 | 7 | 0 | 85.7 (5.5–972.7) |

The reasons for every REVIEW and N/A are in the workbook ("Quality Control" sheet, 431 rows) and in `results/outliers.csv`. In summary:
- **Height REVIEW:** inherited ground and top QC flags (68 ground, 46 top, 27 fallback foot) and tree_102.
- **DBH N/A:**
  - 42 trees have arc coverage below 60%.
  - 28 have no stem axis.
  - 17 have RMSE above the limit, and 8 have no fit.
  - 033 is not released, and 108 is provisional.
- **Crown REVIEW:**
  - 38 envelopes bridge large gaps (1 m slab ratio above 2).
  - 12 use the fallback crown (ITSMe found no crown).
  - 11 are size outliers.
  - One crown reaches the ROI edge, and tree_033 has poor source data.
- **Crown N/A (7):** you judged there is no live crown.

## Files

| File | What it is |
|---|---|
| `ITSMe_all163_results.xlsx` | 8 sheets: All Tree Results, Summary Statistics, Quality Control, Methodology & Metadata, Check vs 20-tree results, DBH lean-corrected slices, Run details, Changes vs previous version |
| `results/` | `tree_attributes.csv`, `methods.json`, `summary.json`, `outliers.csv`, `sensitivity.csv` (data-request items 1–6) |
| `logs/` | `validation.json`, `independent_verification.csv/.json`, `excel_open_check.json`, run timing, environment, worker logs |
| `checkpoints/`, `per_tree/`, `manifests/` | Per-tree checkpoints and provenance |
| `FINAL_AUDIT_REPORT.md` | Audit findings |

## Remaining limitations

These are detailed in `FINAL_AUDIT_REPORT.md`, section E:
- inherited height QC flags (110 trees on REVIEW)
- the DBH limit at 3 cm point spacing, and 28 trees without a stem axis
- unverified branch ownership between trees
- no field data, so no accuracy assessment
- no unedited Rayextract output and no Rayextract parameters
- figures not made (a separate task)
