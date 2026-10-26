from pathlib import Path
import sys,json,csv,subprocess,hashlib,math,shutil,datetime,os
import nbformat
from nbconvert import HTMLExporter
W=Path(__file__).resolve().parents[1]
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jwrite(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def link(p):return '['+p.name+']('+p.as_posix()+')'

def main():
    os.environ['PATH']=str(W/'.venv/Scripts')+os.pathsep+os.environ['PATH']
    execution=json.loads((W/'validation/latest_itsme_notebook_execution.json').read_text());assert execution['success']
    metrics=Path(execution['metrics_directory']);nb=Path(execution['executed_notebook']);out=nb.parent
    # Correct narrative inherited from the earlier static preparation; measurement code/output stays intact.
    for p in [nb,out/'ITSMe_tree_146_test_input.ipynb']:
        n=nbformat.read(p,as_version=4)
        for c in n.cells:
            if c.cell_type=='markdown':
                c.source=c.source.replace('No measurements have been executed in this notebook.','This executed test copy contains actual R-kernel measurements for tree_146 only.')
                c.source=c.source.replace('sensitivity batch/QSM disabled','source-notebook DBH parameter alternatives and ground-reference sensitivity checked; no multi-tree batch or QSM')
        nbformat.validate(n);nbformat.write(n,p)
    n=nbformat.read(nb,as_version=4);codes=[c for c in n.cells if c.cell_type=='code']
    assert len(codes)==8 and all(c.execution_count is not None for c in codes)
    assert all(o.output_type!='error' for c in codes for o in c.outputs)
    html,_=HTMLExporter().from_notebook_node(n);Path(execution['executed_html']).write_text(html,encoding='utf-8')
    comparison=rows(metrics/'tree_146_height_method_comparison.csv')[0];values=rows(metrics/'tree_146_provisional_metric_fields.csv');precision=rows(metrics/'tree_146_PLY_reader_precision.csv');sensitivity=rows(metrics/'tree_146_DBH_sensitivity.csv')
    vals={(r['stage'],r['field']):r['value'] for r in values}
    assert abs(float(comparison['difference_m']))<1e-6
    assert precision[0]['suitable_for_precision_sensitive_diameter']=='FALSE' and precision[1]['suitable_for_precision_sensitive_diameter']=='TRUE'
    assert int(sensitivity[0]['input_band_observation_count'])==17 and float(sensitivity[0]['arc_coverage'])==.7
    frozen=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout
    (W/'environment/python-requirements-lock.txt').write_text(frozen,encoding='utf-8')
    kernels=subprocess.run([sys.executable,'-m','jupyter','kernelspec','list','--json'],capture_output=True,text=True,check=True).stdout
    (W/'environment/jupyter_kernels.json').write_text(kernels,encoding='utf-8')
    assert 'info6003-ir' in json.loads(kernels)['kernelspecs']
    packages=rows(W/'environment/R_package_versions.csv')
    baselines=json.loads((W/'validation/original_notebook_hashes.json').read_text());assert all(sha(Path(r['path']))==r['sha256'] for r in baselines)
    selection=next(r for r in rows(W/'results/top10_selection_manifest.csv') if r['stable_tree_id']=='tree_146')
    assert sha(Path(selection['input_ply_path']))==sha(Path(selection['source_ply_path']))==selection['review_sha256']
    environment=dict(verified_date='2026-10-21 Australia/Sydney',project_python=sys.executable,Python_version=sys.version,R_version='4.5.2',ITSMe_version='2.0.0',ITSMe_git_commit='6cfb11c18efb3b12a4e12d38ea1cbf426b777e7b',R_library=str(W/'environment/R-library'),R_package_count=len(packages),kernel_name='info6003-ir',all_notebook_code_cells_executed=len(codes),notebook_test_passed=True,tree_id='tree_146',project_local_install=True,original_notebooks_unchanged=True,selected_original_PLY_unchanged=True,QSM_run=False,human_approval='PENDING',notes='Old environment_readiness.json and static preparation reports describe the pre-installation state and are retained as historical evidence.')
    jwrite(W/'validation/itsme_runtime_environment.json',environment)
    result=dict(environment=environment,execution=execution,height_comparison=comparison,metric_fields=values,reader_precision=precision,DBH_sensitivity=sensitivity,checks=dict(eight_code_cells_have_execution_counts=True,no_cell_error_outputs=True,height_matches_prepared_reference=True,original_notebooks_unchanged=True,selected_PLY_hashes_match=True,kernel_registered_in_project_environment=True),scientific_accuracy='NOT_INDEPENDENTLY_VALIDATED; no field or independently measured reference height/DBH available',interpretation='Software works on the tested tree; height is consistent with supplied ground/top; DBH and crown remain provisional and QC-limited')
    jwrite(out/'ITSMe_runtime_validation.json',result)
    table=['| Case | Circle DBH (cm) | Functional DBH (cm) | Arc coverage | Band observations |','|---|---:|---:|---:|---:|']
    for r in sensitivity:table.append(f"| {r['case']} | {float(r['circle_DBH_cm']):.3f} | {float(r['functional_DBH_cm']):.3f} | {100*float(r['arc_coverage']):.0f}% | {r['input_band_observation_count']} |")
    report=f'''# ITSMe installation and actual notebook execution

Date: 21 October 2026, Australia/Sydney. **Software test: PASS on tree_146. Scientific measurement accuracy: not independently validated.**

## What was installed

- Python JupyterLab 4.6.4, ipykernel, nbclient and nbconvert, with their dependencies, under `{W/'.venv'}`.
- ITSMe 2.0.0 at author repository commit `6cfb11c18efb3b12a4e12d38ea1cbf426b777e7b`, IRkernel and {len(packages)} total project-library R packages under `{W/'environment/R-library'}`. Existing R 4.5.2 was reused; no R upgrade or global R library installation was required.
- An isolated `info6003-ir` Jupyter kernel under `.venv/share/jupyter/kernels/`; environment settings are in `.env`. That text file is configuration, not the Python environment itself; `.venv` is the actual environment. The launcher applies the settings.
- Python lock versions, R package versions, ITSMe commit and kernel spec are recorded in `environment/` and `validation/itsme_runtime_environment.json`.

## What actually ran

{link(nb)} was executed through the real **R Jupyter kernel**, not replaced by Python calculations. All eight code cells completed without an error. It uses the prepared ITSMe working copy on **one tree only**, `tree_146` / `tree_146_UNCHANGED.ply`, original V2 filename `{selection['original_v2_filename']}`. All 25,948 observations were loaded. The test ran height, DBH, original DBH parameter alternatives, diameters at 1.0/1.5/1.9 m, crown classification and projected area, plus reader/ground-reference checks. No QSM or multi-tree modelling was run. No scientific point cloud, human decision or original course notebook was changed.

Readable output with embedded plots: {link(Path(execution['executed_html']))}. Metrics, R objects, parameters, software versions and diagnostic PNGs: `{metrics}`. The two earlier failed setup attempts were retained for audit; the final run linked here completed successfully.

## Measured test outputs — provisional

| Quantity | Output | Interpretation |
|---|---:|---|
| Ground-referenced ITSMe height | {float(comparison['ITSMe_ground_referenced_height_m']):.6f} m | Same chosen ground/top as preparation; consistency check only |
| Earlier Python supported-top height | {float(comparison['prepared_supported_top_height_m']):.6f} m | Difference {float(comparison['difference_m']):.3g} m; no independent reference |
| ITSMe default max-Z minus min-Z | {float(comparison['ITSMe_default_cloud_min_height_m']):.6f} m | About 0.157 m lower because retained minimum is above estimated foot ground |
| Circle-fit DBH | {100*float(vals[('DBH','dbh')]):.3f} cm | Horizontal slice 1.3 m vertically above mesh foot ground; not field validated |
| Functional/hull DBH | {100*float(vals[('DBH','fdbh')]):.3f} cm | Alternative geometric measure, not an accuracy correction |
| Projected crown area | {float(vals[('projected_crown_area','pa')]):.3f} m² | Exploratory; automatic crown definition and foliage ownership require review |

The input stem lean estimate is 4.03 degrees. The nominal DBH input band is 0.06 m thick and contains only **17 observations**, with **70% angular-sector coverage**. The circle fit does not independently establish a correct stem circumference. Its package `R2` field is the **mean squared radial fit residual**, not the statistical coefficient of determination; do not read it as a percentage accuracy. Here its square root is approximately {1000*math.sqrt(float(vals[('DBH','R2')])):.2f} mm. The original package plot labels this field confusingly; `tree_146_dbh_inspection.png` uses an explicit DBH/coverage/count title while retaining the original package figure separately. `inner_circle_empty=NA` is expected for this small fitted radius with the package's 0.06 m inner-buffer default, not a passed hollow-centre check.

The crown classifier puts everything above its detected first widening (around 2 m in the plot) into the crown, including a long bare upper stem and lower leafy material. This follows the source notebook's method; it **does not establish the biological live-crown boundary or prove that all foliage belongs to this tree**. Do not accept the 2.784 m² crown area without inspecting classification and ownership.

## Limited DBH sensitivity check

{'\n'.join(table)}

These six cases are distinct assumptions, not replicate measurements or a confidence interval. Circle estimates range about **10.13–10.66 cm**; functional estimates about **10.71–12.72 cm**. Changing the band to 0.20 m increases observations to 60 and angular coverage to 100%, but also changes the geometry and functional result; it must not be selected merely to improve the appearance of the fit. The annular ground plane is 0.065 m below the mesh reference, changing the breast-height band. Independent tape/caliper measurements, or a documented manual high-resolution stem-section comparison with known ground, are needed before claiming accuracy. No artificial confidence percentage is assigned.

## Critical direct-PLY precision finding

**The original absolute-coordinate PLY is intact, but ITSMe's Rvcg reader loses precision on this tested global-coordinate input.** The direct reader retained 25,948 records yet reduced distinct Y values from **6,588 to 5**. Against the original observations, median nearest-XYZ discrepancy was **0.02574 m** and maximum **0.24804 m**. This is unacceptable for a roughly 0.107 m stem-diameter measurement. These are observed reader effects, not point-cloud corruption and not a newly applied CloudCompare shift.

The identically shaped, explicitly translated local PLY retained all **6,588** distinct Y values and maximum nearest-XYZ discrepancy only **9.6e-8 m**. The notebook measurements use the separately prepared local **XYZ text** input, with all records retained and a reversible origin recorded in `coordinate_transform.json`. Its XYZ foot-ground reference is in the same frame. **Keep this local-input route for ITSMe; do not feed these global-coordinate PLYs directly into the package reader for precision-sensitive diameter work.** No original coordinates were changed.

## Compatibility fixes and warnings

- Explicit UTF-8-BOM handling fixes Windows R reading the first stable-ID CSV header; explicit case-insensitive boolean parsing handles Python-generated True/False values. These were found by actual execution and corrected in the working copy and preparation code.
- Notebook uses the isolated R library and project kernel. Its foot-height plot title was shortened to avoid clipping. All package/parameter diagnostics and data provenance remain saved.
- The package emits colour-scale replacement messages while generating some plots. They did not stop the run or establish a numerical failure. All warning/error output remains in the executed notebook and console log.
- Original course notebook has Colab-specific mixed-language setup and cannot run unchanged as a local R notebook. This is an executed **adapted working copy**, preserving the ITSMe measurement functions and using the explicit terrain ground reference.

## Open or repeat the test

Double-click `{W/'START_ITSME_JUPYTER.cmd'}` to launch the project JupyterLab, then open the executed notebook to inspect saved outputs. Choose **R (INFO6003 ITSMe)** when running an R notebook. The general working copy is `notebooks/ITSMe_V2_10_selected_trees.ipynb`; it defaults to a height-only run on tree_146. Enable optional stages deliberately after inspection. Executing the notebook creates a new timestamped metric directory. The special test copy additionally runs the single-tree sensitivity/precision checks.

Human approval remains **PENDING**. The package is installed and demonstrated to work; segmentation completeness, foot-ground accuracy, sparse DBH sampling and crown identity still limit scientific accuracy. Before batching, inspect the tree in CloudCompare and validate measurements against an independent reference. Do not extend a successful one-tree runtime test to a claim of accuracy for all 163 exports.

Technical references: [ITSMe package](https://github.com/lmterryn/ITSMe), [height and diameter implementation](https://github.com/lmterryn/ITSMe/blob/main/R/basic_metrics_pc.R), [PLY/TXT reader](https://github.com/lmterryn/ITSMe/blob/main/R/read_tree_pc.R), [IRkernel installation](https://irkernel.github.io/installation/), [executing and saving actual notebook outputs](https://nbclient.readthedocs.io/en/latest/client.html). Exact installed function bodies/version evidence are retained locally; the numerical findings above come from this executed test.
'''
    (W/'ITSMe_RUNTIME_TEST_REPORT.md').write_text(report,encoding='utf-8')
    readme=W/'measurement_pipeline_readme.md';archive=W/'environment/measurement_pipeline_readme_before_installation.md'
    if not archive.exists():shutil.copy2(readme,archive)
    readme.write_text(f'''# INFO6003 measurement workspace

Updated 21 October 2026, Australia/Sydney. **ITSMe installed and tested successfully on tree_146 through a real R Jupyter kernel.** Results remain provisional; no tree has been human-approved. QSM remains untested and was not installed or run in this stage.

## Open the notebook

Double-click `{W/'START_ITSME_JUPYTER.cmd'}`. It launches the project JupyterLab using `.venv` and the separate R library. Choose **R (INFO6003 ITSMe)** for ITSMe notebooks.

- Executed notebook with results: {link(nb)}
- Browser-readable executed output: {link(Path(execution['executed_html']))}
- Full findings, accuracy limitations and direct-PLY precision warning: {link(W/'ITSMe_RUNTIME_TEST_REPORT.md')}
- General reusable working copy: `notebooks/ITSMe_V2_10_selected_trees.ipynb`. Select a stable tree ID from the ten-tree manifest. Height is enabled; optional DBH/crown stages default off in the general copy. Results get new timestamped directories.

## Actual one-tree results

For tree_146, height **12.067 m**, circle DBH **10.659 cm**, functional DBH **11.375 cm**, exploratory projected crown area **2.784 m²**. Height agrees numerically with the earlier ground-referenced calculation, but that is not independent validation. The default cloud-minimum height was **11.910 m**. DBH used only **17 observations** with **70% arc coverage**; sensitivity to ground/band choices and crown ownership still require inspection.

**Precision warning:** direct loading of the absolute-coordinate PLY through ITSMe/Rvcg introduced up to **0.248 m** nearest-XYZ discrepancy on the tested tree. Keep using the prepared local XYZ text input and its matching fixed foot-ground reference. The original PLY is intact. The separate translated local PLY passed the precision comparison; the text route remains preferred.

## Environment

- Python environment: `.venv/`; configuration: `.env`; installed Python versions: `environment/python-requirements-lock.txt`.
- Existing R 4.5.2; isolated packages: `environment/R-library/`; installed ITSMe 2.0.0 commit `6cfb11c18efb3b12a4e12d38ea1cbf426b777e7b`; package versions: `environment/R_package_versions.csv`.
- Project-only kernel: `.venv/share/jupyter/kernels/info6003-ir/kernel.json`; runtime evidence: `validation/itsme_runtime_environment.json`.
- The old `validation/environment_readiness.json`, static syntax validation and preparation reports describe the earlier **pre-installation** state. They remain as historical evidence. The old README is preserved in `environment/measurement_pipeline_readme_before_installation.md`.

## Prepared inputs and ranking evidence

- `results/all_tree_preliminary_heights.csv`: terrain-referenced preliminary estimates and uncertainty for all 163 exports.
- `results/top5_tallest.csv`, `top5_shortest.csv`: selected screened nominal extremes, not verified complete biological-tree rankings. Separate `top5_*_all_exports.csv` and `all_export_preliminary_ranking.csv` retain the all-export comparisons.
- `results/top10_selection_manifest.csv`: ten distinct stable IDs, exact original/review/copied filenames, hashes, pending QC and auxiliary paths.
- `input_trees/5_tallest/` and `5_shortest/`: primary PLYs copied byte-identically, retaining all original XYZ and attributes.
- `terrain_reference/tree_NNN/`: all-point local XYZ text, local XYZRGB PLY, matching original terrain-face subset and fixed foot-ground XYZ, with reversible `coordinate_transform.json`. Constant translation only; no pointwise terrain flattening or change to scientific originals.
- `qc_figures/`: selected 3D and side views. `results/tree_height_ranking_methodology.md`: thresholds, screening and uncertainties. The initial screening tables are audit intermediates, superseded by the final ranked CSVs.
- `results/human_review_template.csv`: record your human decision against stable ID **and exact review SHA-256**. It remains PENDING; runtime success is not segmentation approval.

## Before further measurement

Inspect bases, crown/tip completeness, single-tree identity, neighbouring foliage and terrain alignment in CloudCompare. tree_108 and tree_103 need leaning-stem DBH review; tree_152 has a ground disagreement close to the screening threshold; tree_026/056 have foliage-ownership concerns. The two tallest nominal heights are too close to establish a robust first/second order under the available ground uncertainty. tree_074/079/098/163 retain their previous special warnings.

Use an independent reference to assess height/DBH accuracy. Join later measurements to quality decisions by `stable_tree_id + review_sha256 + dataset version`, carrying ground method, parameters, software versions and source filenames. A changed source hash invalidates an old decision/result association. Test approved individual trees before a resumable batch; do not interpret successful code execution as confirmation of biological completeness.

`notebooks/QSM_V2_10_selected_trees.ipynb` remains a prepared, disabled modelling workflow. Do not run it as part of this ITSMe test. No QSM models, volume or biomass were computed here.
''',encoding='utf-8')
    jwrite(W/'validation/ITSMe_installation_and_test_complete.json',dict(passed=True,scope='Installation and actual single-tree R-notebook execution; no independent accuracy claim',runtime_report=str(W/'ITSMe_RUNTIME_TEST_REPORT.md'),executed_notebook=str(nb),executed_HTML=execution['executed_html'],metrics_directory=str(metrics),source_PLY_unchanged=True,original_notebooks_unchanged=True,all_8_code_cells_executed=True,remaining_issues=['Sparse DBH band and partial arc','Ground/top/ownership require human and independent-reference validation','Direct global-PLY reader precision loss; use local input','Crown classification not independently verified'],QSM_run=False))
    print(json.dumps(dict(report=str(W/'ITSMe_RUNTIME_TEST_REPORT.md'),notebook=str(nb),metrics_directory=str(metrics),height_m=float(comparison['ITSMe_ground_referenced_height_m']),DBH_cm=100*float(vals[('DBH','dbh')]),R_package_count=len(packages),all_code_cells_executed=len(codes)),indent=2))

if __name__=='__main__':main()
