# Suggested report edits (v4 → v5)

These edits are ready to paste. Every number comes from `audit/recomputed/` or from the file named. The report itself was not changed.

## Front matter
- Replace `[To be completed: student ID]` with your WSU student ID. The folder name suggests 22083142; confirm it.

## Abstract
- No numeric change is needed. Optional: after "Spearman ρ = 0.91 for VALID pairs" add "(n = 23)".

## Sect. 1 (RQ3, O5, biomass)
- **RQ3.** Old: "...and how closely do they agree with field measurements?" New: "...and what field data would be needed to test their agreement with field measurements? (Agreement itself could not be tested; Sect. 6.3.)"
- **O5.** Old: "(O5) compare them with field records." New: "(O5) compare them with field records (blocked: no field data for WSL_ML2A)."
- **Biomass.** Delete the placeholder after you have confirmed with your supervisor. Otherwise use: "Biomass analysis was not attempted; deferring it was agreed with the supervisor on <date>."

## Sect. 3.1
- **CRS.** Old: "in EPSG:32756 as recorded in the processing metadata." New: "in EPSG:32756 (WGS 84 / UTM zone 56S, ellipsoidal heights), as stored in the LAS header."
- **Crops.** Old: "From WSL_ML2A I prepared two crops; only the crop named "55x55" was used." New: "From WSL_ML2A I prepared two crops (named 35x35 and 55x55). Both, and a 2 cm version of the 55x55 crop, were segmented automatically, but only the 3 cm 55x55 crop was refined and measured."
- **Crop shape.** Replace `[To be completed: confirm the crop shape ...]` with your answer to open question 1, or with: "Whether the crop boundary is exactly this rectangle is not recorded; edge flags assume it is."
- **Scanner and registration.** Replace `[To be completed: scanner model, scan positions and registration error]` with: "The raw file was exported by RIEGL rdbconvert 1.12.2 (LAS header); scanner model, scan positions and registration error were not supplied." Alternatively, supply the real values.

## Sect. 3.2
- After "it covers other plots and does not include WSL_ML2A" add: "It does contain 29 records for WSF_ML2A, a wet sclerophyll plot with a similar name that is not the scanned plot."
- Old: "One empty row is excluded". New: "One row without a site identifier is excluded".

## Table 2, Sect. 4.2
- **S1 tools.** Old: "CloudCompare 2.13.2 (per file header)". New: "RIEGL rdbconvert 1.12.2 (raw export); CloudCompare 2.13.2 (crop PLY headers)".
- **Downsampling placeholder.** Replace with: "The processing guide specifies RiSCAN PRO for cropping and downsampling [7], but which tool and filter produced these files was not recorded."

## Sect. 4.4
- Old: "A first round produced 199 exports and was superseded; a second round produced 163 tree clouds."
- New: "A first round produced 199 exports (28.71 M points, a redistribution of the automated trees) and was superseded. A second round produced 163 tree clouds (26.66 M points). After a script-assisted audit, four clouds (tree_051, 074, 079, 134) received script-proposed point recoveries, and I edited six more (tree_033, 067, 102, 103, 108, 114) on 21–23 October. The 163 measured clouds (26.60 M points) are this final set."

## Table 3 (rule column)
- **Height.** "REVIEW if: the ground under the foot is not locally supported; the foot is a fallback (lowest observation); the top is not a locally supported tip; the highest point lies > 0.5 m above the supported top; the stem axis meets the ground > 0.25 m from the foot; the tree was visually excluded; or the cloud was edited after QC."
- **DBH.** "N/A if no stem axis or no accepted fit (or withheld: tree_033). REVIEW if the value is a 1.1–1.5 m slice median, the foot is a fallback, ≥ 2 point clusters lie within 1 m of the axis at 1.3 m, the axis was refitted, or the axis–foot offset is > 0.25 m."
- **Crown base.** "Rule-based for 102 trees; chosen manually by me for 54 trees after visual review; N/A (7) where I judged there was no live crown."
- **Crown area.** Add: "or ITSMe crown classification unavailable (all points above the base used), or crown within 0.10 m of the crop edge."

## Sect. 4.7
- **Re-fit placeholder.** New text: "an independent re-implementation re-fitted 24 trees using the same stem foot, ground and axis. Heights agreed to within 5 × 10⁻¹³ m, which confirms the arithmetic but is not an independent height estimate. DBH could be compared for 14 trees: median absolute difference 0.26 cm, maximum 5.33 cm (tree_067, whose released value depends on an outline filter). For 5 of the 14, the re-fit failed the acceptance screen."
  - Source: `logs/independent_verification.csv`.
- **Checks sentence.** Add: "These checks did not detect that `summary.json` reports 16 all-VALID trees; the correct count is 14 (Sect. 6.2)."
- **Repository placeholder.** Fill in only after the measurement pipeline has been committed (audit F-003).

## Sect. 6.1
- **Label definitions.** Replace the placeholder with: "The labels come from a script-assisted screen of the round-2 set: AUTO_CANDIDATE = a proposed point recovery, MANUAL_REVIEW = an open uncertainty, UNCHANGED = no specific flag. They do not record whether a tree changed relative to the automated output."
- **"67 of 163" sentence (Sect. 5).** Old: "(67 of 163 differ in point count from the same-numbered automated file)". New: "(the round-2 file segmented_N differs in point count from automated tree N for 67 of 163 files; the measured tree_NNN corresponds to automated file NNN − 1)".

## Sect. 6.2
- **DBH failures.** Old: "28 trees had no stem axis and 55 had no acceptable slice." New: "28 trees had no stem axis, 54 had no acceptable slice, and one (tree_033) was withheld because of poor source data."
- **Top flags.** Old: "46 trees are flagged as possibly truncated at the top". New: "46 trees have a tree top that could not be confirmed (possible truncation or sparse sampling)".
- **Re-fit and sensitivity placeholder.** New text: "In the sensitivity test (8 trees), changing the DBH slice from 6 cm to 3, 5 or 10 cm changed the circle diameter by at most 1.94 cm (tree_084, 3 cm slice). Hull-based diameters differed from circle diameters by −12.0 to +5.9 cm. Maximum height exceeded the 99th-percentile height by 0.34–1.55 m. Single-envelope crown volumes were 1.39–2.42 times the sum of the 1 m slab envelopes."
  - Source: `results/sensitivity.csv`, computed in audit.

## Fig. 3
- Insert `ITSMe_all163_visualisations_20261023_202459/individual_trees/tree_069_3D_sideviews.png` and `tree_146_3D_sideviews.png` as (a), and `report_figures/dbh_vs_height.png` as (b). Check that (b) plots only the 23 VALID pairs, or change the caption to match what it plots.

## Sect. 7
- **"What the Evidence Supports", first conclusion.** Old: "more than a third of the points were unassigned, and only 25 of 163 refined trees are labelled unchanged by the audit, consistent with ..." New: "more than a third of the points (36.8%) were left unassigned, and refinement removed a further 2.0 M points from the automated trees, consistent with ..."
  - 28,708,304 − 26,663,898 = 2,044,406.
- **Low point counts.** Old: "several failed trees have fewer than ten points in the 6 cm slice". New: "12 of the 54 failed fits had fewer than ten points in the 6 cm slice; the rest failed on arc coverage or residual".
- **Selection bias.** Add: "VALID medians describe a non-random subset (DBH is VALID for 43 of 163 trees and fails more often on thin stems), so they should not be read as plot-level summaries."

## Sect. 8
- Old: "delivers a usable, auditable dataset". New: "delivers an auditable dataset that is usable once the pending human approvals are recorded".

## Use of AI (replace the whole bracket; adapt to University wording)
"I used generative AI coding assistants (OpenAI Codex and Anthropic Claude Code) as support tools. They wrote and ran the Python and R scripts for point-cloud auditing, ITSMe measurement, quality-control rules, statistics and figures. They proposed point recoveries for four trees and crown-base options, which I accepted or chose between. They compiled the result summaries from which the reported numbers were taken, and they helped edit and format this report. I performed the manual segmentation in CloudCompare, made the crown-base and trunk-cleaning decisions, and checked the reported numbers against the result files. All AI-generated code and logs are in the project repository."
- Keep the last sentence only if it becomes true (F-003).

## References
- [4], [5]: delete `[VERIFY]`. For [4], add doi:10.1109/ACCESS.2021.3084954.
- [2]: check volume and pages on the publisher's site.
- [7]: "Q-ForestLab: Steps processing pipeline (processing_pipeline.pdf), unpublished course notes". Author and date: confirm.
- [8], [9]: complete the custodian and version, or remove [9] if the file cannot be found.
