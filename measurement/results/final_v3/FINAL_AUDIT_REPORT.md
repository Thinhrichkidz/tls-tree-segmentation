# Final audit report: INFO6003 ITSMe 163-tree analysis

Audited 23 October 2026 by Claude, acting as HPC engineer, TLS scientist and data-quality analyst.

**Audited deliverable:** `measurement_pipeline/results/ITSMe_all163_output_v3_FINAL_20261023_201144/` (called FINAL below).

**Evidence base:**
- source code in `measurement_pipeline/scripts/`
- per-tree inputs and results (`per_tree/`)
- logs, the executed notebook, and the workbook opened in Excel
- an independent recalculation from the original PLY files
- comparison with `ITSMe_top10_results.xlsx` and the 20-tree results

Earlier summaries were not taken as evidence. Every claim below cites a file or check.

## A. Requirement compliance

Sources: the all-163 task (T), `REPORT_DATA_REQUEST.md` (R) and this audit request (U).

| # | Requirement | How verified | Evidence | Status | Action |
|---|---|---|---|---|---|
| T1 | Read the data request, notebooks, reference workbook, inputs and docs | Re-read in this audit | Column list from R item 1 implemented; reference styles parsed from `ITSMe_top10_results.xlsx` (`xl/styles.xml`) | VERIFIED | – |
| T2 | Process all 163 trees | ID check against the folder, snapshot and workbook | `validation.json`: `163_ids_once`, `id_mapping_consistent`; 163 `result.json` files; worker failures 0 | VERIFIED | Mapping check added (see D3) |
| T3 | Height, DBH and crown projected area | Independent recalculation on 24 trees | Height difference ≤ 5e-13 m; DBH median absolute difference 0.26 cm; area 0.68–0.92 × convex outline (as expected for a concave outline) | VERIFIED | – |
| T4 | Every extra numeric metric in R | Column-by-column against R item 1 | `results/tree_attributes.csv` has all 30 R columns | VERIFIED, with caveats | `status`, `roi_id`/`crs` provenance: see R1 and E |
| T5 | Method, units, assumptions and limits per metric | Inspected `methods.json` and the Methodology sheet | Sections for height, DBH, crown, indicators, status rules, parallel processing and sensitivity | VERIFIED | Script hashes added (D6) |
| T6 | VALID / REVIEW / N/A / UNKNOWN rules; no fabrication | Status–value consistency check on all cells | `status_matches_value_presence`, `unaccepted_fits_not_in_dbh_column`, `estimated_column_empty` | VERIFIED | Two missing REVIEW rules added (D1, D2) |
| T7 | ESTIMATED only when defensible and kept separate | R rule 1 forbids estimates | Estimated DBH column empty; 0 ESTIMATED of any metric | VERIFIED (deliberately none) | – |
| T8 | Partial results kept | Count of trees with some but not all metrics | 87 PARTIAL SUCCESS trees keep their valid metrics | VERIFIED | – |
| T9 | Exact colour hex codes, per cell, with a legend | Automatic check of every status and value cell in five metric pairs; Excel COM colour samples | `colour_coding_consistent` (now covers value cells too); legend on Summary and Methodology sheets | VERIFIED | Value cells added to the check (D3) |
| T10 | Statistics on VALID values only; counts of valid / estimated / missing / review | Statistics recomputed from the exported sheet | `summary_statistics_recomputed_from_sheet`; Summary sheet has separate VALID-only and VALID+REVIEW blocks | VERIFIED | Recompute check added (D3) |
| T11 | Use the 64 cores efficiently, with RAM-aware workers | Timing and memory logs | 60 workers (cores capped by 70% of free RAM ÷ 4 GB); peak R memory ≤ 843 MB per tree; wall time is set by the largest tree (48 s) | VERIFIED | Peak memory logged (D7); no change needed |
| T12 | Error handling, per-tree logs, checkpoints, retry without rerunning successes | Resume test and failure-injection test | Rerun on a copy: 163/163 preparations and 163/163 measurements reused (8 s). A missing tree gave status `failed` while the other 163 continued | VERIFIED | – |
| T13 | Record duration, workers and status | `logs/run_timing.json`, Run details sheet | Preparation 64 s, measurement 52 s, notebook 142 s, 60 workers | VERIFIED | – |
| T14 | `ITSMe_all163_results.xlsx` with the four required sheets, styled like the reference | Excel COM open; sheet list; header style | 8 sheets (4 required + 4 supporting); bold blue header with border and wrap; frozen first row and column, as in the reference | VERIFIED | Filters added (D4) |
| T15 | No figures in the workbook or this stage | File listing | No image files in FINAL; no embedded drawings | VERIFIED | – |
| T16 | Validation list (units, ranges, N/A ≠ 0, estimates separate, opens, consistent with earlier) | `validation.json` (15 checks) and `excel_open_check.json` | All 15 checks True; Excel opened, 163 rows | VERIFIED | – |
| T17 | Compare with field inventory where available | Searched the project and drive | No inventory spreadsheet found | NOT APPLICABLE (no data) | Recorded in `methods.json` |
| T18 | Updated executable notebook | Executed end to end three times from scratch | `ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v3.ipynb`; executed copy in FINAL, no cell errors | VERIFIED | Independent-check and sensitivity cells added |
| T19 | `processing_summary.md`, logs and checkpoints | Files present | FINAL/`processing_summary.md`, `logs/`, `checkpoints/progress.csv`, `per_tree/` | VERIFIED | – |
| R1 | `tree_attributes.csv` | Columns and contents | Present. `status` is NA for all trees, because no accepted / uncertain / discarded records exist for the current clouds | VERIFIED, with `status` = NA (data absent) | – |
| R2 | `methods.json` | Content review | Present. Software, units, definitions and parameters; git = NA (not a repository); Rayextract parameters not found | VERIFIED | – |
| R3 | `summary.json` | Content review | ROI count and extent, status counts, failed fits (83), edge trees (1), run time. Points before/after downsampling and Rayextract segment count are NA (not recorded) | VERIFIED with NA items | – |
| R4 | `outliers.csv` | Content review | 99 flags: failed DBH, crown-size extremes, low stem completeness, edge contact; height/DBH ratio rule found none | VERIFIED | Size outliers now also set REVIEW (D2) |
| R5 | `sensitivity.csv` (5–10 trees) | Produced in this audit | 8 trees: DBH at 3/5/6/10 cm, circle vs hull, height max vs 99th percentile, crown envelope vs slab sums | VERIFIED | **Added** (D5) |
| R6 | Run time and machine | `summary.json`, `environment.json` | Present | VERIFIED | – |
| R7 | `before_after.csv` (unedited Rayextract output) | Searched the project docs and folders | `manual_seg_v2` is documented as a manually cleaned baseline; no unedited Rayextract output was kept | NOT APPLICABLE (data absent) | Recorded |
| R8 | Refinement log | Searched | No timing or edit log for the current clouds | NOT APPLICABLE | – |
| R9–R10 | Field matches and diameter-distribution comparison | Searched | No inventory found | NOT APPLICABLE | – |
| R-fig | Figures and `AVAILABILITY_REPORT.md` | – | Figures excluded by the task; availability report not written | INCOMPLETE (deferred) | The availability content is covered by `methods.json` "Not obtained" and section E |
| U1 | Independent recalculation of a representative sample | Own Python fits on 24 trees | `logs/independent_verification.csv` | VERIFIED | **Added** (D5) |
| U2 | Comparison with the 10-tree and 20-tree results | Value-by-value comparison | 20 trees identical (≤ 1.4e-14). All 10-tree differences explained (section C) | VERIFIED | – |
| U3 | Reproducibility | Three independent fresh runs | v2, v3-audit and v3-final runs: 0 value differences for all 163 trees | VERIFIED | – |

## B. Dataset verification (FINAL)

| Item | Count |
|---|---|
| Expected trees (snapshot, folder and stable-ID mapping) | 163 |
| Accounted for in the workbook (once each, same order and hash) | 163 |
| SUCCESS (all 4 core metrics have a value) | 76, of which 16 have all four VALID |
| PARTIAL SUCCESS | 87 |
| FAILED | 0 |

| Metric | VALID | ESTIMATED | N/A | REVIEW | UNKNOWN |
|---|---|---|---|---|---|
| Height | 53 | 0 | 0 | 110 | 0 |
| DBH | 43 | 0 | 83 | 37 | 0 |
| Crown base height | 156 | 0 | 7 | 0 | 0 |
| Crown projected area | 131 | 0 | 7 | 25 | 0 |
| Crown envelope volume | 100 | 0 | 7 | 56 | 0 |
| Crown length / crown ratio | 53 | 0 | 7 | 103 | 0 |
| Equivalent crown diameter | 131 | 0 | 7 | 25 | 0 |
| Crown point density | 100 | 0 | 7 | 56 | 0 |

UNKNOWN is used in the indicator columns (stem completeness, lean flag, crown-edge flag) when no stem axis exists.

## C. Issues identified

**Code and validation**
1. **The source-hash check was too weak.** It only checked that each file name was in the snapshot, not that its hash matched. The data happened to be correct, because the preparation step asserts hashes, but the check itself proved nothing.
2. **The colour check covered only status cells**, not the value cells beside them.
3. **There was no check that the exported statistics match the exported cells**, and no contradiction check (crown base ≥ height, crown ratio outside 0–1).
4. **There were no filters on the tables** (an explicit requirement).
5. **The version-comparison check was written only for v2.** Applied to v3 it reported genuine status-only changes as failures.
6. **Script versions were not recorded**, and per-tree memory was not measured, so the RAM-per-worker assumption had no evidence behind it.

**Scientific**
1. **tree_102** was VALID for height and DBH although its stem axis meets the ground 0.38 m from its ground-reference foot. That pattern caused the wrong bases on 103 and 108, and the handover had listed 102 as still needing review. No other tree has an offset above 0.06 m.
2. **Crown-size outliers were listed in `outliers.csv` but kept VALID.** The most important case is tree_079: 228.7 m², 2.5 times the next-largest crown, from a 1.28 M-point cloud. It probably includes neighbouring crowns.
3. **Borderline DBH cases**, compared with the independent fit (values agree, screen outcomes differ):
   - tree_103 (oval trunk): ITSMe's DBH routine gives 66.6 cm, a direct slice fit 69.1 cm, and the independent fit 68.0 cm. The area-equivalent diameter is 78.1 cm. Circle DBH is inherently ambiguous on this trunk, which is why both values are reported.
   - tree_067: 26.8 cm depends on the user-agreed outline filter; without it the independent fit gives 21.5 cm.
   - tree_125 (VALID, 29.6 cm) and tree_049 (REVIEW, 42.7 cm) pass ITSMe's screen but not my independent one. The values agree within 1.2 cm; only the pass/fail outcome at the threshold differs.
4. **Comparison with `ITSMe_top10_results.xlsx`.** Every difference has a documented cause:
   - 103: height −0.18 m (corrected base); DBH now passes after cleaning.
   - 108: 38.1 cm → N/A; the old axis followed a side branch.
   - 056: 9.93 cm → N/A; arc coverage 0.45.
   - 102: −0.13 cm; different axis version.
   - Crown areas change only through the crown base.
   - All other heights and DBHs are identical.
5. **Inherited height QC.** 110 heights are REVIEW mostly because of inherited flags (uncertain ground for 68, top for 46, fallback foot for 27). This batch did not re-derive those flags.
6. **The stem-cluster indicator at 1.3 m is a heuristic.** It puts 27 DBHs on REVIEW when there are other point clusters within 1 m of the stem. It cannot tell a second stem from a branch or a leftover shrub.

**Performance (no defect)**
- Measurement wall time (52 s) is set by the largest tree (48 s), with largest-first scheduling.
- Preparation (64 s) is mostly writing text inputs.
- More workers would not reduce either.
- Peak memory: R heap 225 MB median, 843 MB maximum per tree. The 4 GB allowance is conservative; R heap excludes some native allocations.

## D. Improvements implemented (v3)

| # | What changed | Why | How validated | Measurements changed? |
|---|---|---|---|---|
| D1 | New rule: axis/foot offset above 0.25 m → height and DBH REVIEW | Scientific issue 1 | tree_102 is now REVIEW with the reason stated; no other tree affected | Status only (102 height, DBH, crown length, crown ratio) |
| D2 | Crown-size outliers (outside the 5th–95th percentile of crown area) → area and volume REVIEW; derived crown metrics follow | Scientific issue 2 | 11 trees changed status, listed in "Changes vs previous version" | Status only |
| D3 | Validation rebuilt to 15 checks: true per-file hash, results computed on the current source, ID mapping and order, value-cell colours, statistics recomputed from the sheet, contradictions, generic version comparison | Code issues 1, 2, 3 and 5 | All 15 pass on FINAL | No |
| D4 | Filters on All Tree Results, Quality Control and Changes sheets | Code issue 4 | Excel COM: `AutoFilterMode = True` on all three | No |
| D5 | Independent recalculation (`verify_all163_independent.py`) and `sensitivity.csv` (`sensitivity_all163.R`), both run by the notebook | Requirements U1 and R5 | Outputs in `logs/` and `results/` | No |
| D6 | Script SHA-256 hashes in `methods.json` | Reproducibility | Present | No |
| D7 | Peak R memory per tree recorded | Evidence for worker sizing | Run details sheet; maximum 843 MB | No |

Regression evidence: the FINAL measured values for all 163 trees equal v2 and the v3-audit run exactly (0 differences). The 20 earlier test trees are still reproduced to within 1.4e-14.

## E. Remaining limitations (need data, inspection or supervisor input)

1. **Height:** 110 heights are REVIEW from inherited ground and top flags. Re-checking ground and tops (especially the 27 fallback-foot trees) would resolve many.
2. **DBH:** 83 are N/A.
   - 28 have no stem axis from the existing helper.
   - The rest have incomplete or noisy rings at 3 cm point spacing.
   - No relaxation was applied.
   - Provisional raw fits are kept separately.
3. **Crown ownership is not verified for any tree.** 140 trees carry the inherited proximity-contact flag. tree_079's crown needs a visual ownership check.
4. **Crown volume is a convex envelope including air gaps.** 38 envelopes have a 1 m slab ratio above 2. It is not wood volume or biomass.
5. **Definitions to state in the report:**
   - DBH is measured 1.3 m along the lean-corrected stem axis from the foot ground, not vertically.
   - Height is the highest point above the foot ground (the 99th-percentile alternative is in `sensitivity.csv`).
   - The CRS (EPSG:32756) comes from project records and is not re-verified.
6. **Not obtainable from the data here:**
   - segmentation status labels
   - unedited Rayextract output and its parameters
   - downsampling counts
   - a field inventory, and so accuracy or validation statistics
7. **Not done in this stage:** figures and `AVAILABILITY_REPORT.md`.

## F. Final verification evidence

- **Notebook:** `ITSMe_all163_processing.ipynb` executed in 142.3 s with no errors.
  - preparation 64.3 s, 48 processes
  - measurement 51.8 s, 60 workers
  - statuses: 120 ok, 43 partial, 0 failed
- **`logs/validation.json`:** 15 of 15 checks True:
  - `163_ids_once`, `every_tree_has_status`, `source_hashes_match_snapshot`, `results_computed_on_current_source`, `id_mapping_consistent`
  - `values_in_plausible_ranges_no_zero_for_missing`, `estimated_column_empty`, `unaccepted_fits_not_in_dbh_column`, `status_matches_value_presence`
  - `colour_coding_consistent`, `summary_uses_valid_only`, `20_tree_results_reproduced`, `summary_statistics_recomputed_from_sheet`, `no_contradictory_values`, `values_changed_only_for_user_reviewed_crowns`
- **`logs/independent_verification.json`:**
  - 24 trees; maximum height difference 4.8e-13 m; maximum ground difference 2.4e-10 m
  - DBH compared on 14 trees: median absolute difference 0.26 cm, maximum 5.33 cm (067, explained in C)
  - workbook volume / convex hull of all points above the base: 0.99–1.00
- **`logs/excel_open_check.json`:** opened in Excel; 8 sheets; 163 tree rows; colour samples match the status hex codes. Excel also confirmed the filters, the frozen panes (row 1, column 1) and numbers stored as numbers.
- **Resume test (on a copy):** 163/163 preparations and 163/163 measurements reused in 8 s. **Failure injection:** a missing tree was recorded as `failed` without stopping the others.
- **Reproducibility:** three fresh full runs give identical measured values for all 163 trees.
- **Source protection:** all 163 `CloudCompare_review_v2` hashes equal the Session 3 snapshot before and after the run.

**What is not claimed:**
- that every one of the 163 trees has reliable measurements (see the REVIEW and N/A counts)
- field accuracy
- that branch ownership is correct
