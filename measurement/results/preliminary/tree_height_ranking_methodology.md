# Preliminary tree-height ranking methodology

Prepared 21 October 2026. Scope: 163 current V2 review exports, observed geometry only. These are **preliminary comparisons, not validated complete-tree measurements**. All human approvals remain PENDING. No DBH, crown measurements, volume, biomass, new segmentation, point transfers or point removal were performed.

## Inputs and reproducibility

- Stable IDs, source names, current candidates and source hashes come from `segmentation_v2_correction/new_tree_quality_report.csv` and the current consolidated review folder. Historical 199-tree ownership was not used. The four latest automatic candidates are included among the 163 exports; none happens to enter the final screened ten.
- Read all current review XYZ observations, retaining original global coordinates. Existing segmentation/QC screens were reused for component fractions, sampled cross-tree contacts and terrain-boundary context. New operations were restricted to height, low-stem location, local ground support and selected-input preparation.
- The original terrain has 659,506 vertices and 1,318,980 triangles. Use its **actual triangles** via linear barycentric interpolation; never replace its topology with Delaunay triangulation, a bounding-box plane or a new ground surface. Use cached arrays already verified in prior work. No off-mesh extrapolation.
- Raw class-2 points provide a local consistency check, not independent surveyed truth: the terrain and classifications can share processing errors. Original notebook and review-file SHA-256 checks, per-tree checkpoints, selection mappings and coordinate transformations are saved under `validation/`, `checkpoints/`, `results/` and `terrain_reference/`.
- Existing isolated NumPy/SciPy/plyfile/matplotlib dependencies were reused from `verification_output/_deps`. Nothing was installed. No GPU claim is made.

## Height and observed top

`preliminary_height_m = highest_supported_z_m − estimated_local_ground_z_m`

The all-export CSV also retains raw min/max Z, raw Z range, the maximum-versus-supported-top difference and original zero-based point row of the supported tip. Metres throughout. A local-support filter requires **four other tree observations within 0.15 m and two other observations within 0.08 m** of the candidate tip. Search the upper 3 m plus, if needed, the highest 5,000 observations. This is a transparent screening threshold for the approximately 3 cm dataset, not a validated universal outlier detector. A supported tip still can belong to a neighbouring tree; prior ownership flags and visual review remain necessary.

The first pass had no supported point in the upper 3 m for four exports. Extending the search to the highest 5,000 observations recovered a lower supported top; no missing value was replaced with an invented height. **All 163 now have a finite geometric estimate**, including low-confidence fallback estimates. Large rejected-maximum differences: tree_004 0.354 m, tree_027 1.696 m, tree_083 3.313 m, tree_099 2.361 m, tree_100 8.592 m, tree_124 5.995 m, tree_136 1.234 m, tree_137 8.825 m. Sparse legitimate high observations may fail this rule, so these cases are explicitly excluded from screened ranking pending inspection. No original point is deleted, silently filtered from prepared inputs, or declared false solely by this test.

## Actual stem-foot estimate, leaning and missing bases

Do not use crown centroid as tree base. Start with observed low structure, initially points more than 0.30 m above their own terrain and within 4.5 m above the observed minimum. If too few remain, inspect the observed first 3.5 m above the minimum as an explicitly uncertain missing-base fallback.

At vertical stations spaced 0.25 m, use ±0.14 m horizontal bands. Connected XY groups link at 0.14 m. Check up to the three largest groups, exclude groups spanning over 2.2 m in XY, and fit supported circular-location aids with deterministic RANSAC (seed 6003 + tree index). Require at least 12 inliers, initial inlier fraction 0.55 and angular support at least 165 degrees. Location-aid radii are **not DBH measurements** and are not exported as diameters. Horizontal sections of leaning stems are elliptical; these fits estimate a centreline, not a stem-normal cross-section.

Fit a robust XY-versus-Z line through section centres, retain centres within 0.15 m, then require at least four stations spanning 0.75 m. Intersect the resulting low-stem axis iteratively with the actual sloping terrain. This supports leaning stems without straightening or rotating them. The CSV records axis fit error/span, lean, ambiguous sections and extrapolation from the lowest fitted section. Curvature, buttresses, partial arcs and branch junctions still can bias the axis.

If no usable axis is obtained, ground is sampled at the XY of the lowest observed point and **explicitly labelled LOWEST_OBSERVATION_XY_FALLBACK_UNCERTAIN**. It is a geometric hypothesis, not a verified stem foot; its height is LOW_OR_UNKNOWN and excluded from screened selection. If a base is missing, extrapolating an observed axis does not recreate any missing stem or establish biological completeness.

For screening, require axis RMSE ≤0.10 m, lowest fitted station ≤1.15 m above foot ground, minimum observed Z ≤0.60 m above that ground and no more than one ambiguous section. Negative minimum-minus-foot-ground values can arise on sloping ground at another XY and do not by themselves prove below-ground contamination. The full diagnostics retain them.

## Local ground support

Mesh elevation is the primary nominal ground. Cross-check with a robust least-squares plane through raw class-2 points within a **0.30–1.00 m annulus around the estimated foot**; soft-L1 scale 0.04 m, trim residuals beyond 0.10 m and refit. Do not average an arbitrary 5 m window on a slope. A locally supported ground reference requires:

- at least 40 retained class-2 points and coverage of at least five of eight angular sectors;
- plane RMSE ≤0.07 m and absolute plane-versus-mesh disagreement ≤0.15 m;
- the actual foot mesh triangle has longest XY edge ≤2 m.

95/163 references meet this local numerical screen. These criteria control local consistency, not absolute survey accuracy. Store plane elevation, mesh elevation, disagreement, count, angular coverage, RMSE and triangle size. The alternative `ground_plane_height_sensitivity_m` is the supported top minus that plane elevation; it is **a reference-choice scenario, not a statistical confidence interval**. No calibrated height confidence interval can be supplied without reference measurements and error validation.

## QC ranking and visual inspection

Initial automatic eligibility required locally supported ground, supported near-ground stem geometry, a supported observed tip with rejected-maximum difference ≤0.20 m, prior largest component fraction ≥0.98, at most two significant coarse voxel components, at most 50 sampled cross-tree contacts, minimum prior sampled boundary distance ≥0.75 m and supported-tip boundary distance ≥1 m. The contact threshold is a conservative project triage rule, not biological ownership proof; a small contact count can still matter. A mesh boundary is a proxy for plot-cut risk; no independent exact survey-boundary polygon was available for a new boundary proof. Prior sampling can miss a boundary contact. Retain these limitations.

Explicitly exclude tree_074, tree_079, tree_098 and tree_163 from screened ranking because their unresolved merged ownership, ground or contamination issues persist. Do not silently clear their earlier warnings. Tree_079's current candidate has a geometric height around 25.532 m, but its foot mesh versus annular-plane discrepancy is about 0.313 m and crown ownership is unresolved; it is not an approved height/DBH tree.

26 exports initially passed the numerical screen. Inspect both XZ and YZ views for the eight shortest and eight tallest numerical candidates. Exclude **tree_088** (bare upper stem, missing/dead/broken crown unresolved) and **tree_050** (bare leader/branches without a convincing complete upper crown). Do not classify them as short complete biological trees. No segmentation change was made. 24 exports remain eligible for provisional comparison, with the selected extremes visually checked in both side views. Automatic eligibility of middle-ranked, uninspected trees is not a human crown assessment.

For the final ten, the viewed geometry shows a plausible dominant basal stem and connected upper branching/crown, without an obvious isolated crown-fragment identity or conspicuous plot-cut top. This is enough for a **MEDIUM_PROVISIONAL observed-height comparison**, not a certification that all crown points are present or correctly owned. Understorey/branch ownership, fine missing tops and acquisition occlusion remain unresolved. Original MANUAL_REVIEW statuses and all human approvals remain intact.

## Two distinct rankings

All-export nominal extremes include failed/uncertain objects. They are saved separately in `top5_tallest_all_exports.csv`, `top5_shortest_all_exports.csv` and the complete `all_export_preliminary_ranking.csv`. Do not interpret these as the shortest/tallest complete biological trees in the plot.

### A. All-export provisional tallest

| Rank | Tree ID | Original V2 filename | Review PLY | Height (m) | Ground plane − mesh (m) | Confidence |
|---:|---|---|---|---:|---:|---|
| 1 | tree_103 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_102 - Cloud.ply` | `tree_103_MANUAL_REVIEW.ply` | 27.226 | -0.032 | MEDIUM_PROVISIONAL |
| 2 | tree_084 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_83 - Cloud.ply` | `tree_084_MANUAL_REVIEW.ply` | 27.178 | -0.133 | MEDIUM_PROVISIONAL |
| 3 | tree_041 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_40 - Cloud.ply` | `tree_041_MANUAL_REVIEW.ply` | 26.564 | -0.093 | LOW_OR_UNKNOWN |
| 4 | tree_069 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_68 - Cloud.ply` | `tree_069_MANUAL_REVIEW.ply` | 26.199 | -0.125 | MEDIUM_PROVISIONAL |
| 5 | tree_070 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_69 - Cloud.ply` | `tree_070_MANUAL_REVIEW.ply` | 26.001 | -0.135 | LOW_OR_UNKNOWN |

### A. All-export provisional shortest

| Rank | Tree ID | Original V2 filename | Review PLY | Height (m) | Ground plane − mesh (m) | Confidence |
|---:|---|---|---|---:|---:|---|
| 1 | tree_121 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_120 - Cloud.ply` | `tree_121_UNCHANGED.ply` | 9.387 | -0.139 | LOW_OR_UNKNOWN |
| 2 | tree_155 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_154 - Cloud.ply` | `tree_155_MANUAL_REVIEW.ply` | 9.612 | -0.193 | LOW_OR_UNKNOWN |
| 3 | tree_004 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_3 - Cloud.ply` | `tree_004_MANUAL_REVIEW.ply` | 9.880 | UNKNOWN | LOW_OR_UNKNOWN |
| 4 | tree_105 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_104 - Cloud.ply` | `tree_105_UNCHANGED.ply` | 9.970 | -0.181 | LOW_OR_UNKNOWN |
| 5 | tree_011 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_10 - Cloud.ply` | `tree_011_MANUAL_REVIEW.ply` | 10.148 | UNKNOWN | LOW_OR_UNKNOWN |

### B. QC-screened provisional tallest

| Rank | Tree ID | Original V2 filename | Review PLY | Height (m) | Ground plane − mesh (m) | Confidence |
|---:|---|---|---|---:|---:|---|
| 1 | tree_103 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_102 - Cloud.ply` | `tree_103_MANUAL_REVIEW.ply` | 27.226 | -0.032 | MEDIUM_PROVISIONAL |
| 2 | tree_084 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_83 - Cloud.ply` | `tree_084_MANUAL_REVIEW.ply` | 27.178 | -0.133 | MEDIUM_PROVISIONAL |
| 3 | tree_069 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_68 - Cloud.ply` | `tree_069_MANUAL_REVIEW.ply` | 26.199 | -0.125 | MEDIUM_PROVISIONAL |
| 4 | tree_026 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_25 - Cloud.ply` | `tree_026_MANUAL_REVIEW.ply` | 25.828 | -0.097 | MEDIUM_PROVISIONAL |
| 5 | tree_102 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_101 - Cloud.ply` | `tree_102_MANUAL_REVIEW.ply` | 24.480 | -0.095 | MEDIUM_PROVISIONAL |

### B. QC-screened provisional shortest

| Rank | Tree ID | Original V2 filename | Review PLY | Height (m) | Ground plane − mesh (m) | Confidence |
|---:|---|---|---|---:|---:|---|
| 1 | tree_108 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_107 - Cloud.ply` | `tree_108_MANUAL_REVIEW.ply` | 10.838 | +0.030 | MEDIUM_PROVISIONAL |
| 2 | tree_152 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_151 - Cloud.ply` | `tree_152_UNCHANGED.ply` | 11.027 | -0.146 | MEDIUM_PROVISIONAL |
| 3 | tree_056 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_55 - Cloud.ply` | `tree_056_MANUAL_REVIEW.ply` | 11.601 | +0.107 | MEDIUM_PROVISIONAL |
| 4 | tree_146 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_145 - Cloud.ply` | `tree_146_UNCHANGED.ply` | 12.067 | -0.065 | MEDIUM_PROVISIONAL |
| 5 | tree_151 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_150 - Cloud.ply` | `tree_151_UNCHANGED.ply` | 12.363 | -0.142 | MEDIUM_PROVISIONAL |

These are nominal orders among the eligible population, not a claim to have identified the true extremes among all biological trees. Heights of excluded exports and missing observations can alter the eventual ranking. Tree_103 and tree_084 differ by only **0.048 m** nominally: using the annular-plane reference reverses their order. Tree_108 and tree_152 are also close relative to ground/foot uncertainty. Report meaningful precision as approximately 0.01 m for reproducibility only; it is not centimetre accuracy.

## Preparation and validation

Copy ten primary review PLYs byte-identically under `input_trees/5_tallest` and `5_shortest`. Ten distinct IDs, no list overlap, no duplicated points introduced. The two groups retain exact review filenames and source V2 names in the manifest. Re-read all ten, compare counts/hashes/attributes, and validate explicit local-coordinate derivatives by inverse translation. Crop terrain by selecting original faces whose XY bounding boxes intersect each tree's XY bounding box +1 m; retain original topology and all required vertices, with no retriangulation.

Adapt both notebooks statically, retaining source originals. Parse all R and Python cells; inspect paths and manifest integrity. **No ITSMe smoke test was run** because required packages and kernels are absent. No full QSM, DBH, crown or volume computations were performed. Ray-cloud conversion is reproducibly specified but has not run; the tools are not available. Read `validation/` for the exact checks and environment evidence.

## Primary technical sources checked

- [ITSMe tree-height API](https://lmterryn.github.io/ITSMe/reference/tree_height_pc.html) and [implementation](https://github.com/lmterryn/ITSMe/blob/main/R/basic_metrics_pc.R): explicit XYZ ground data.frame support, extrema-based default, horizontal diameter routines and plotting behaviour.
- [ITSMe point-cloud reader](https://lmterryn.github.io/ITSMe/reference/read_tree_pc.html): TXT/PLY/LAS/LAZ support; [reader implementation](https://raw.githubusercontent.com/lmterryn/ITSMe/main/R/read_tree_pc.R) for PLY cleaning and TXT loading.
- [ITSMe DBH](https://lmterryn.github.io/ITSMe/reference/dbh_pc.html), [crown classification](https://lmterryn.github.io/ITSMe/reference/classify_crown_pc.html) and [package dependencies](https://github.com/lmterryn/ITSMe/blob/main/DESCRIPTION).
- [RayCloudTools format and Windows container instructions](https://github.com/csiro-robotics/raycloudtools), [importer](https://raw.githubusercontent.com/csiro-robotics/raycloudtools/main/raycloudtools/rayimport/rayimport.cpp), [model command](https://raw.githubusercontent.com/csiro-robotics/raycloudtools/main/raycloudtools/rayextract/rayextract.cpp) and [official container build](https://raw.githubusercontent.com/csiro-robotics/raycloudtools/main/docker/Dockerfile).
- [TreeTools](https://github.com/csiro-robotics/treetools) for model-format and later volume-summary capabilities. These online sources establish current interfaces; actual installed versions must still be recorded before execution.
