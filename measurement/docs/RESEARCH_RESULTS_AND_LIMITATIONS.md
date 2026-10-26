# Research results and limitations

Verified from saved results on 21 October 2026 (Australia/Sydney). Detailed methods remain in `measurement_pipeline/results/tree_height_ranking_methodology.md` and `measurement_pipeline/ITSMe_RUNTIME_TEST_REPORT.md`.

## Segmentation and rankings

The 163-file V2 dataset is the current manually reviewed baseline, not verified scientific ground truth. Four proposed automatic corrections have provenance; no candidate status means human acceptance. Historical exclusions and the 2,056,490-point quarantine remain in place; do not restore excluded observations automatically. Special ownership/ground warnings for tree_074/079/098/163 remain unresolved.

All 163 current review exports have preliminary terrain-referenced geometric height estimates. Ground uses the actual terrain mesh at an estimated stem foot; the supported-top method and fallback/missing-base flags are documented. Existing QC evidence and limited visual screening produced 24 provisional eligible candidates. Ten nominal extremes were copied without changing primary PLY coordinates or attributes. Separate all-export rankings include questionable objects and must not be confused with complete-tree comparisons.

Nominal tallest IDs/heights (m): **103 27.226; 084 27.178; 069 26.199; 026 25.828; 102 24.480**. Nominal shortest: **108 10.838; 152 11.027; 056 11.601; 146 12.067; 151 12.363**. Exact stable IDs have the `tree_` prefix. The two leading tall estimates differ by only 0.048 m; the alternative ground reference reverses their order. Excluded objects/unsampled crowns can change final biological rankings. No tree is recorded as human-approved.

## Actual notebook measurements: export 145 / tree_146

The successful real R-kernel ITSMe test loaded all 25,948 observations from the documented local TXT. Height **12.067056599187 m** agrees with the earlier prepared top-minus-ground calculation (difference about −2.7e-14 m). This verifies implementation consistency under the **same** ground/top assumptions, not independent accuracy.

Default max-Z minus retained min-Z gave **11.909729003906 m**, about 0.157 m shorter. Circle DBH **10.6592312595371 cm**, functional DBH **11.374784009743 cm**, 0.06 m band at 1.3 m vertically above estimated foot ground, **17 observations / 70% angular coverage**. Circle results across six parameter/ground cases range about **10.13–10.66 cm**; functional results about **10.71–12.72 cm**. These are alternative assumptions, not replicates or a confidence interval. Package `R2` is mean squared radial residual, not a coefficient of determination or percentage accuracy.

Exploratory projected crown area **2.783742185 m²** follows the notebook's automatic first-widening crown rule. It includes lower leafy material and bare stem above that boundary; it does not independently identify the live biological crown or settle neighbouring-tree foliage ownership. The value must remain provisional.

## Precision and scientific uncertainties

On the tested tree, direct global-PLY loading via ITSMe/Rvcg retained point count but reduced distinct Y values from 6,588 to five, with maximum nearest-XYZ discrepancy **0.24804 m**. The source PLY was not altered. The translated local PLY preserved the 6,588 Y values with discrepancy below about 1e-7 m. The actual measurements used the separate local TXT and consistent foot-ground reference. This supports the local-input route on this software stack; it does not prove every possible package version behaves identically.

Terrain/classified-ground disagreement, stem-foot extrapolation, partial DBH arcs, original scan sampling, leaning trunks, missing tops/bases, crown ownership and plot-boundary truncation remain relevant. Horizontal slices through leaning stems are not stem-normal DBH sections; the notebook's 15-degree trigger is a review rule, not a validated universal threshold.

Independent tape/caliper or otherwise defensible reference measurements, documented ground convention and human completeness/ownership decisions are needed before claiming accuracy. No final complete-tree ranking, full ten-tree ITSMe batch, QSM model, woody volume or biomass has been completed. QSM setup and modelling remain a separate future stage.

At home, reproduce the existing one-tree results first and record software differences. Preserve original inputs, source IDs/hashes and all uncertainty flags. Do not rerun scientific processing merely to replace a drive letter.
