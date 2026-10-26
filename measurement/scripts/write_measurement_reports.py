from preliminary_heights import *
from collections import Counter

def table(rows,extra=False):
    lines=['| Rank | Tree ID | Original V2 filename | Review PLY | Height (m) | Ground plane − mesh (m) | Confidence |','|---:|---|---|---|---:|---:|---|']
    for r in rows:
        d=r['plane_minus_mesh_m'];ds=f'{float(d):+.3f}' if d else 'UNKNOWN'
        lines.append(f"| {r['rank']} | {r['stable_tree_id']} | `{r['original_v2_filename']}` | `{r['review_ply_filename']}` | {float(r['preliminary_height_m']):.3f} | {ds} | {r['overall_height_confidence']} |")
    return '\n'.join(lines)

def main():
    rows=csvread(W/'results/all_tree_preliminary_heights.csv');manifest=csvread(W/'results/top10_selection_manifest.csv')
    # Ground-reference alternatives are sensitivity scenarios, not confidence intervals.
    for filename in ['all_tree_preliminary_heights.csv','top5_tallest.csv','top5_shortest.csv','top10_selection_manifest.csv','top5_tallest_all_exports.csv','top5_shortest_all_exports.csv']:
        rr=csvread(W/'results'/filename)
        for r in rr:
            plane=r['ground_plane_z_m'];top=r['highest_supported_z_m'];h=r['preliminary_height_m']
            r['ground_plane_height_sensitivity_m']=float(top)-float(plane) if plane and top else ''
            r['ground_reference_scenario_height_difference_m']=abs(float(r['plane_minus_mesh_m'])) if r['plane_minus_mesh_m'] else ''
            r['ranking_uncertainty_note']='Ordinal position is nominal; ground-reference/top/ownership uncertainties may change order. Scenario difference is not a confidence interval.'
        csvwrite(W/'results'/filename,rr)
    rows=csvread(W/'results/all_tree_preliminary_heights.csv');manifest=csvread(W/'results/top10_selection_manifest.csv')
    ranked=sorted(rows,key=lambda r:float(r['preliminary_height_m']),reverse=True)
    csvwrite(W/'results/all_export_preliminary_ranking.csv',[dict(nominal_descending_rank=i+1,**r) for i,r in enumerate(ranked)])
    tall=csvread(W/'results/top5_tallest.csv');short=csvread(W/'results/top5_shortest.csv');at=csvread(W/'results/top5_tallest_all_exports.csv');ass=csvread(W/'results/top5_shortest_all_exports.csv')
    qc=csvread(ROOT/'segmentation_v2_correction/new_cloudcompare_review_manifest.csv')
    counts=Counter(r['current_qc_status'] for r in rows);eligible=sum(r['qc_screen_eligible']=='True' for r in rows);ng=sum(r['ground_reference_reliability']=='LOCALLY_SUPPORTED' for r in rows)
    method=f'''# Preliminary tree-height ranking methodology

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

{ng}/163 references meet this local numerical screen. These criteria control local consistency, not absolute survey accuracy. Store plane elevation, mesh elevation, disagreement, count, angular coverage, RMSE and triangle size. The alternative `ground_plane_height_sensitivity_m` is the supported top minus that plane elevation; it is **a reference-choice scenario, not a statistical confidence interval**. No calibrated height confidence interval can be supplied without reference measurements and error validation.

## QC ranking and visual inspection

Initial automatic eligibility required locally supported ground, supported near-ground stem geometry, a supported observed tip with rejected-maximum difference ≤0.20 m, prior largest component fraction ≥0.98, at most two significant coarse voxel components, at most 50 sampled cross-tree contacts, minimum prior sampled boundary distance ≥0.75 m and supported-tip boundary distance ≥1 m. The contact threshold is a conservative project triage rule, not biological ownership proof; a small contact count can still matter. A mesh boundary is a proxy for plot-cut risk; no independent exact survey-boundary polygon was available for a new boundary proof. Prior sampling can miss a boundary contact. Retain these limitations.

Explicitly exclude tree_074, tree_079, tree_098 and tree_163 from screened ranking because their unresolved merged ownership, ground or contamination issues persist. Do not silently clear their earlier warnings. Tree_079's current candidate has a geometric height around 25.532 m, but its foot mesh versus annular-plane discrepancy is about 0.313 m and crown ownership is unresolved; it is not an approved height/DBH tree.

26 exports initially passed the numerical screen. Inspect both XZ and YZ views for the eight shortest and eight tallest numerical candidates. Exclude **tree_088** (bare upper stem, missing/dead/broken crown unresolved) and **tree_050** (bare leader/branches without a convincing complete upper crown). Do not classify them as short complete biological trees. No segmentation change was made. {eligible} exports remain eligible for provisional comparison, with the selected extremes visually checked in both side views. Automatic eligibility of middle-ranked, uninspected trees is not a human crown assessment.

For the final ten, the viewed geometry shows a plausible dominant basal stem and connected upper branching/crown, without an obvious isolated crown-fragment identity or conspicuous plot-cut top. This is enough for a **MEDIUM_PROVISIONAL observed-height comparison**, not a certification that all crown points are present or correctly owned. Understorey/branch ownership, fine missing tops and acquisition occlusion remain unresolved. Original MANUAL_REVIEW statuses and all human approvals remain intact.

## Two distinct rankings

All-export nominal extremes include failed/uncertain objects. They are saved separately in `top5_tallest_all_exports.csv`, `top5_shortest_all_exports.csv` and the complete `all_export_preliminary_ranking.csv`. Do not interpret these as the shortest/tallest complete biological trees in the plot.

### A. All-export provisional tallest

{table(at)}

### A. All-export provisional shortest

{table(ass)}

### B. QC-screened provisional tallest

{table(tall)}

### B. QC-screened provisional shortest

{table(short)}

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
'''
    (W/'results/tree_height_ranking_methodology.md').write_text(method,encoding='utf-8')
    readiness=f'''# Measurement pipeline: prepared inputs and remaining setup

**Status: inputs and working notebooks prepared; execution blocked by missing software.** All heights and rankings are provisional. All 163 segmentation approvals remain PENDING. None is certified as a complete biological tree. No packages were installed, original PLYs/notebooks changed, DBH/crown metrics calculated or QSM models constructed.

Workspace: `{W}`.

## Start here

1. Inspect `results/top5_tallest.csv`, `top5_shortest.csv` and the exact `top10_selection_manifest.csv`; use the corresponding primary PLY in `input_trees/5_tallest/` or `5_shortest/` in CloudCompare. Ten selected trees: {', '.join(r['stable_tree_id'] for r in manifest)}. Every selected source hash matches the unchanged current review file.
2. Review each tree's full base, connected stem, own upper crown/tip, nearby-tree contacts and ground, using `qc_figures/*_selected_3D_sideviews.png`. In CloudCompare retain a common Global Shift for absolute data; do not combine local derivatives with absolute data without the recorded inverse translation.
3. Record your decision separately in `results/human_review_template.csv`: stable ID, exact review SHA-256, decision, date and reviewer. An old decision must not apply to a later changed file. Do not replace the correction manifest or equate AUTO_CANDIDATE / UNCHANGED with accepted completeness.
4. After environment setup, open `notebooks/ITSMe_V2_10_selected_trees.ipynb` using the R kernel, set `TREE_ID="tree_146"`, keep DBH/crown/sensitivity switches FALSE and run one tree through the height cell. Confirm point count, `h1$lp=0`, height agreement with the prepared supported-top height (allow the documented raw-maximum difference), and inspect diagnostic plots and warnings.
5. Only then enable one-tree provisional DBH. Check slice location 1.3 m vertically above the chosen foot ground, angular coverage, neighbour contamination, circular/functional fit and point-density sensitivity. Do not accept a numerical result just because the function completes.
6. Keep QSM disabled until reviewed modelling is requested. Configure Docker or existing native executables in `notebooks/QSM_V2_10_selected_trees.ipynb`, run preflight, then explicitly enable one-tree conversion and validate it. Do not start all ten models.

## Selected candidate limitations

- **tree_103 / tree_084:** nominal heights 27.226 / 27.178 m are not distinguishable as a definitive first/second ranking; the ground-plane alternative reverses their order. tree_103 has estimated low-stem lean 16.8 degrees and two prior coarse components (dominant component 99.735%); inspect minor vegetation. tree_084 has a −0.133 m ground-plane discrepancy and prior ownership contacts.
- **tree_069 / tree_026 / tree_102:** local ground-plane discrepancies approximately −0.125 / −0.097 / −0.095 m; prior sampled contacts require crown/stem ownership review. tree_026 has substantial mid-stem leafy material: verify it is its own branching, especially before crown/QSM work. tree_102 retains all points, but its ranking height uses a supported tip 0.018 m below its raw maximum.
- **tree_108:** lean approximately 25.9 degrees; lowest fitted section about 0.93 m above the estimated foot and observed minimum about 0.22 m above foot-ground Z. Inspect foot extrapolation and lower-stem curvature. It passes the specified provisional height screen, but horizontal-slice DBH is not a validated stem-normal diameter. Notebook diameter stages stop at a 15-degree lean trigger unless explicitly overridden for a labelled provisional diagnostic.
- **tree_152:** ground-plane discrepancy −0.146 m, close to the 0.15 m screening limit; lowest retained observation about 0.35 m above foot ground. Confirm ground/foot and crown membership rather than treating the screen as approval.
- **tree_056:** prior contacts and visible lower/middle foliage require review. **tree_146 and tree_151:** simpler low-lean observed structures; good initial height-test candidates, still pending approval. tree_146 is the default smoke-test ID.
- All ten still need biological identity, crown/top completeness and contamination inspection. Selected trees are 7 MANUAL_REVIEW and 3 UNCHANGED outputs; no selected automatic candidate was silently accepted.
- **Excluded notable cases:** tree_088 and tree_050 have bare/unresolved upper crowns; tree_079 remains excluded with ground/ownership warnings; tree_074/098/163 retain manual-merge/contamination warnings. The eight exports with >0.20 m unsupported-top drops are listed in the methodology and remain outside the screened ranking.

## What is prepared

- `results/all_tree_preliminary_heights.csv`: 163 numeric geometric height estimates plus missing-base, top, terrain, ownership and confidence diagnostics. {ng} locally supported ground references, {eligible} provisionally eligible observed trees after the visual exclusions.
- `results/top5_tallest.csv` / `top5_shortest.csv`: screened provisional comparison. `top5_*_all_exports.csv`: all-export extremes including problematic objects. `all_export_preliminary_ranking.csv`: all 163 in nominal descending order. `top5_*_screened_initial.csv` are **audit-only intermediate tables**, superseded by the final screened CSVs.
- `results/top10_selection_manifest.csv`: exact stable-ID/original-name/review-name/copied-file mapping, hashes, QC, translations, auxiliary paths and ground sensitivity. No overlap between the two selected groups.
- Primary selected PLYs preserve original global coordinates and **all source attributes**. No rows removed or added in preparation.
- `terrain_reference/tree_NNN/`: all-point local XYZ TXT for ITSMe, local XYZRGB PLY for format conversion, original-terrain face subset PLY and vertices TXT, fixed foot-ground XYZ and a reversible `coordinate_transform.json`. The local derivatives intentionally project the schema to XYZ or XYZRGB; scanner-normal/ray/scalar attributes are not invented. The absolute primary PLY retains them.
- The translation is constant: local = absolute − (estimated foot X, foot Y, mesh ground Z). Units metres, no rotation, rescaling, upright correction or pointwise slope flattening. Matching translated terrain keeps true slope. The local mesh is not a new terrain reconstruction.
- `qc_figures/`: 3D and side views per selected tree, plus side-view screening sheets. Subsampling affects **display only**.
- `validation/`: original-notebook full-cell audit, source hashes, environment evidence, syntax/manifest/point-count checks and input round-trip evidence. `checkpoints/`: per-tree height diagnostics, section centres and selected-tip identity.

## Notebook audit and expected measurements

Both originals were read completely: ITSMe has 29 cells, QSM has 11. Full original cell contents and metadata are preserved in `validation/original_notebook_static_audit.json`; original SHA-256 values are unchanged.

### Original ITSMe: R analysis with a mixed Colab setup cell

The notebook first contains Python `google.colab` drive mounting despite R metadata, then R library setup and `devtools::install_github`, `read_tree_pc(.ply)`, `tree_height_pc`, `dbh_pc(functional=TRUE)` and DBH sensitivity examples (R2 0.002, 0.2 m slice, concavity 3). It computes diameters at 1.0/1.5/1.9 m, `classify_crown_pc(thresholdbranch=1.5)`, then `projected_area_pc(concavity=3)`, saving PNGs. It suppresses warnings and does not pass a DTM. Its default height is max Z − min Z, and its default DBH reference can be wrong when the base is absent.

The working copy retains these functions, adds an explicit one-point XYZ foot-ground reference, records the actual package signatures/versions, preserves warnings and source mapping, and writes unique per-tree run directories under `results/ITSMe_tree_NNN_TIMESTAMP_PID/`. It reads prepared TXT through the original ITSMe reader rather than taking a precision/cleaning risk through Rvcg's PLY path. No points are sampled out. Height uses the source algorithm's raw maximum and is recorded **separately** from the supported-top ranking estimate. Optional DBH/sensitivity/crown stages are off initially.

ITSMe directly supports PLY, TXT, LAS and LAZ. DTM input must be an XYZ **data.frame**, not a bare numeric ground value. A constant local translation alone does not fix the algorithm's min-Z default; the explicit DTM reference is essential. The prepared one-point ground reference avoids the default 5 m median terrain window on a slope. Source plotting can zero relative to cloud minimum; the adapted extra figure labels true foot-ground zero.

Horizontal-slice circular and functional DBH remain biased for leaning stems. Narrowing a band reduces smear but does not turn a horizontal ellipse into a stem-normal circle. This workflow reports vertical height; stem length along a curved trunk is a different quantity. The source notebook does not calculate a full suite of crown diameters/3D crown volume, so those need a separately documented extension after testing.

### Original QSM: Python wrapper, C++ tools, Linux/Colab builds

Python mounts Drive and invokes apt/git/CMake/sudo to build Eigen, libnabo, Qhull, RayCloudTools and TreeTools, including a hard-coded CMake config edit. The actual model commands are `rayimport input.ply ray 0,0,-0.1 --max_intensity 0`, `rayextract terrain tree_raycloud.ply`, then `rayextract trees tree_raycloud.ply tree_mesh.ply --max_diameter 0.9 --height_min 10`. No R operation or explicit leaf/wood separation appears in this notebook. TreeTools is built but not called in the original. No measured wood volume or biomass result is produced just by reading it.

The adapted Python notebook uses standard-library CSV/paths/subprocess/JSON; no NumPy requirement. It uses the pre-existing plot terrain (explicitly translated), a plain XYZRGB input with one synthetic non-black label, and `--segmented` so RayExtract models the current one-tree label. It retains the importer's synthetic 0,0,-0.1 ray as format scaffolding, prohibits real-ray inference from it and does not add `--use_rays`. A ray-cloud `.ply` needs acquisition-vector/time/alpha conventions; arbitrary CloudCompare normal fields do not satisfy that meaning. No synthetic scanner trajectory is represented as an observed one.

Change `height_min` from 10 m to configurable 2 m, retain 0.9 m `max_diameter` as an unvalidated starting parameter, and inspect both before modelling. The one-tree model may still fail. Expected RayExtract outputs are `*_trees.txt`, `*_trees_mesh.ply`, `*_segmented.ply`; check that there is exactly one plausible model before accepting any structure. The optional later `treeinfo` stage logs TreeTools output without guessing a volume schema. RayExtract text is not ITSMe's TreeQSM MAT format. Structural/taper priors and foliage contamination can bias inferred branch radii/wood volume. **Modelled wood volume is not biomass.**

### Software responsibilities and Windows setup (not executed)

| Component | Role | Verified local state |
|---|---|---|
| Python 3.13.14 | preliminary read-only height preparation; future QSM command wrapper | present; scientific libraries only in existing verification `_deps`, not default Python |
| JupyterLab / ipykernel | local notebook frontend and Python kernel | missing in the checked Python environment; no registered R kernel found in standard locations |
| R 4.5.2 | ITSMe analysis | present at `C:/Program Files/R/R-4.5.2/bin/Rscript.exe` |
| ITSMe / IRkernel | structural metrics and R notebook kernel | missing |
| ggplot2, data.table, Rvcg, lidR, nabor, sf, rgl, alphashape3d, concaveman, R.matlab, patchwork, ggforce, ggtext | ITSMe reader/geometry/plot dependencies | missing in checked R libraries |
| RayCloudTools / TreeTools native executables | ray conversion, geometric reconstruction, model summaries | not found on PATH; an unlisted custom installation remains possible |
| Docker Desktop CLI | simplest supported Windows route to the C++ tools | CLI present; Linux engine unavailable, local images unverified |
| Other WSL Linux | alternative build environment | only docker-desktop distro reported; no general-purpose Linux distro verified |

After your installation approval, the simplest route is **native Windows R + JupyterLab/IRkernel for ITSMe; Docker Desktop's Linux container for RayCloudTools/TreeTools**. No GPU requirement is assumed; these notebook stages are not automatically CUDA-accelerated. Use a separate Python virtual environment and R user library rather than the verification `_deps` folder. Example steps to carry out later, not instructions that have been executed:

```powershell
# Create a new dedicated environment only when you approve installation.
python -m venv "{W}\\.venv"
& "{W}\\.venv\\Scripts\\python.exe" -m pip install jupyterlab ipykernel
```

In R 4.5.2 after that Python environment is active/on PATH:

```r
install.packages(c("IRkernel", "remotes"), repos="https://cloud.r-project.org")
remotes::install_github("lmterryn/ITSMe", build_vignettes=FALSE)
IRkernel::installspec(user=TRUE)
```

ITSMe's spatial/compiled dependencies may need compatible Windows binaries or Rtools for the **installed R release** when source compilation is required. Pin and record the successful ITSMe commit/package versions; do not blindly assume current documentation matches an older installed version. Register IRkernel against the same Jupyter environment, then launch that environment's JupyterLab and select R for ITSMe / Python for QSM. Changing the system R version is not necessary to prepare these files.

For QSM later, start Docker Desktop with its Linux engine. If a compatible local image is not already installed, approve and run `docker pull ghcr.io/csiro-robotics/raycloudtools:latest` yourself or request that setup, then pin its immutable image ID/digest. The notebook uses `--pull=never`, so it cannot silently download an image. Confirm G: drive bind mounts work. The official current container builds both RayCloudTools and TreeTools; verify actual executable help before any model run. A native or previously configured Linux build can be selected instead; no dependency installation is in the working notebook.

## Test status and next stage

All R cells passed **parse-only** validation using the local R executable; all Python cells passed syntax parsing. The original notebooks remained unchanged. All ten primary PLYs, counts, attributes and byte hashes were checked, and local copies round-trip to absolute XYZ. Prepared ground references and terrain share the same per-tree translation.

**ITSMe smoke test: NOT RUN, dependency-blocked.** No load/height/DBH success is claimed. **QSM: inputs and conversion procedure prepared; not runtime-ready or end-to-end tested.** No converted ray cloud, model or woody volume was fabricated. Review `validation/environment_readiness.json`, `selected_input_validation.json`, `adapted_notebook_static_validation.json` and `final_package_validation.json`.

For future batch work, replace notebook state with one function per stable ID, a frozen manifest/approved-SHA filter, parameter/version hashes, per-tree error/status records and resumable independent output folders. Keep stable IDs fixed and join measurements to QC on **stable_tree_id + review_sha256 + dataset version**, not alphabetical position or a shortened filename. Carry original V2 filename, current review filename, source hash, human decision, ground method and uncertainty into every result row. A later approved segmentation change invalidates old measurements unless the source hash matches. Keep the ten-tree smoke-test workflow first; do not execute full modelling without approval.

Technical sources: [ITSMe APIs and reader](https://lmterryn.github.io/ITSMe/reference/index.html), [ITSMe dependencies](https://github.com/lmterryn/ITSMe/blob/main/DESCRIPTION), [IRkernel installation and registration](https://github.com/irkernel/irkernel), [JupyterLab installation](https://jupyterlab.readthedocs.io/en/stable/getting_started/installation.html), [Python virtual environments](https://docs.python.org/3.13/library/venv.html), [RayCloudTools Windows/container and format documentation](https://github.com/csiro-robotics/raycloudtools), [RayExtract command source](https://raw.githubusercontent.com/csiro-robotics/raycloudtools/main/raycloudtools/rayextract/rayextract.cpp), [TreeTools](https://github.com/csiro-robotics/treetools). Full method and source details are in `results/tree_height_ranking_methodology.md`.
'''
    (W/'measurement_pipeline_readme.md').write_text(readiness,encoding='utf-8')
    template=W/'results/human_review_template.csv'
    if not template.exists():csvwrite(template,[dict(stable_tree_id=r['stable_tree_id'],dataset_version='V2 current review',review_filename=r['review_ply_filename'],review_sha256=r['review_sha256'],original_v2_filename=r['original_v2_filename'],human_decision='PENDING',complete_tree_approved='PENDING',reviewer='',review_date='',base_ground_notes='',crown_top_notes='',ownership_notes='',measurement_release='PENDING') for r in manifest])
    # A concise reproducibility inventory does not modify any scientific input.
    dump(W/'validation/report_summary.json',dict(exports=len(rows),finite_preliminary_heights=len(rows),ground_locally_supported=ng,initial_numerically_screened=26,screened_after_visual_exclusions=eligible,review_status_counts=dict(counts),selected_ids=[r['stable_tree_id'] for r in manifest],selected_review_status_counts=dict(Counter(r['current_qc_status'] for r in manifest)),all_human_approval='PENDING',smoke_test='NOT_RUN_DEPENDENCIES_MISSING',QSM_run=False))
    print('REPORTS_WRITTEN',eligible,'eligible',dict(Counter(r['current_qc_status'] for r in manifest)),flush=True)

if __name__=='__main__':main()
