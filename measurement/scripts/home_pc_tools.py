"""Portable preparation/checks and explicit kernel configuration; never installs or measures."""
from pathlib import Path
import argparse,csv,json,sys,re,os
W=Path(__file__).resolve().parents[1];ROOT=W.parent
PATH_FIELDS=['input_ply_path','source_ply_path','local_xyz_path','local_xyzrgb_ply_path','local_terrain_mesh_path','local_ground_reference_path']
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2)+'\n',encoding='utf-8')
def relative(p):
    p=str(p).replace('\\','/');marker='/Codex_help/'
    if marker in p:return p.split(marker,1)[1]
    q=Path(p)
    if q.is_absolute():return q.relative_to(ROOT).as_posix()
    return p
def prepare():
    rows=readcsv(W/'results/top10_selection_manifest.csv')
    for r in rows:
        for k in PATH_FIELDS:r[k]=relative(r[k])
    manifest=W/'environment/home_selection_manifest.csv'
    with manifest.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    for kind,name in [('ITSMe','ITSMe_V2_10_selected_trees.ipynb'),('QSM','QSM_V2_10_selected_trees.ipynb')]:
        n=json.loads((W/'notebooks'/name).read_text(encoding='utf-8'))
        for c in n['cells']:
            if c['cell_type']!='code':continue
            s=''.join(c['source'])
            if kind=='ITSMe':
                if 'Project-local R package library' in s:
                    s='# Home kernel supplies the fresh project R library.\nif (!requireNamespace("IRkernel",quietly=TRUE)) stop("Configure the home R environment first.")\n'
                if re.search(r'^ROOT <- ',s,re.M):
                    finder='''find_root <- function() {
  configured <- Sys.getenv("INFO6003_PROJECT_ROOT", "")
  p <- normalizePath(if(nzchar(configured)) configured else getwd(), winslash="/", mustWork=TRUE)
  repeat {
    if(dir.exists(file.path(p,"manual_seg_v2")) && dir.exists(file.path(p,"measurement_pipeline"))) return(p)
    parent <- dirname(p)
    if(identical(parent,p)) stop("Open Jupyter inside Codex_help or set INFO6003_PROJECT_ROOT.")
    p <- parent
  }
}
ROOT <- find_root()'''
                    s=re.sub(r'^ROOT <- .*$',lambda _:finder,s,count=1,flags=re.M)
                    s=s.replace('"results", "top10_selection_manifest.csv"','"environment", "home_selection_manifest.csv"')
                    anchor='selected <- manifest[manifest$stable_tree_id == TREE_ID, , drop = FALSE]'
                    s=s.replace(anchor,anchor+'\nfor (name in c('+','.join('"'+k+'"' for k in PATH_FIELDS)+')) selected[[name]] <- file.path(ROOT, selected[[name]])')
                    s=s.replace('check.names = FALSE, stringsAsFactors = FALSE)','check.names = FALSE, stringsAsFactors = FALSE, fileEncoding="UTF-8-BOM")')
                    s=s.replace('read.csv(review_path, stringsAsFactors=FALSE)','read.csv(review_path, stringsAsFactors=FALSE, fileEncoding="UTF-8-BOM")')
                n['metadata']['kernelspec']={'name':'info6003-home-ir','display_name':'R (INFO6003 Home)','language':'R'}
            else:
                if re.search(r'^ROOT = Path\(',s,re.M):
                    finder='''def find_root():
    configured = __import__("os").environ.get("INFO6003_PROJECT_ROOT")
    start = Path(configured) if configured else Path.cwd()
    for p in [start, *start.parents]:
        if (p/"manual_seg_v2").is_dir() and (p/"measurement_pipeline").is_dir(): return p
    raise RuntimeError("Open Jupyter inside Codex_help or set INFO6003_PROJECT_ROOT")
ROOT = find_root()'''
                    s=re.sub(r'^ROOT = Path\(.*$',lambda _:finder,s,count=1,flags=re.M)
                    s=s.replace('WORK/"results/top10_selection_manifest.csv"','WORK/"environment/home_selection_manifest.csv"')
                    s=s.replace('selected = matches[0]','selected = matches[0]\nfor key in '+repr(PATH_FIELDS)+': selected[key] = str(ROOT/selected[key])')
            c['source']=s.splitlines(True);c['execution_count']=None;c['outputs']=[]
        n['cells'].insert(0,dict(cell_type='markdown',metadata={},id='home-portability-note',source=['# Home PC portable working copy\n','Generated from the latest working copy; original course notebooks and saved executed notebooks are unchanged. Paths resolve from the project root. Use the home environment setup first. Default one-tree height run only; QSM remains disabled.\n']))
        dump(W/'notebooks'/(kind+'_HOME_PORTABLE.ipynb'),n)
    return rows
def check():
    selected=readcsv(W/'environment/home_selection_manifest.csv');missing=[]
    for r in selected:
        for k in PATH_FIELDS:
            if not (ROOT/r[k]).is_file():missing.append(r[k])
    docs=['START_HERE_HOME_PC.md','PROJECT_CURRENT_STATUS.md','PROJECT_STRUCTURE.md','WORKFLOW_AND_SCRIPTS.md','HOME_PC_SETUP.md','PORTABLE_DRIVE_CHECKLIST.md','RESEARCH_RESULTS_AND_LIMITATIONS.md']
    for p in docs:
        if not (ROOT/p).is_file():missing.append(p)
    execution=json.loads((W/'validation/latest_itsme_notebook_execution.json').read_text())
    for k in ['executed_notebook','executed_html','metrics_directory']:
        if not (ROOT/relative(execution[k])).exists():missing.append(relative(execution[k]))
    n=json.loads((ROOT/relative(execution['executed_notebook'])).read_text(encoding='utf-8'));codes=[c for c in n['cells'] if c['cell_type']=='code']
    result=dict(project_root=str(ROOT),manual_V2_PLYs=len(list((ROOT/'manual_seg_v2').glob('*.ply'))),review_V2_PLYs=len(list((ROOT/'CloudCompare_review_v2').glob('*.ply'))),selected_input_PLYs=len(list((W/'input_trees').rglob('*.ply'))),selected_unique_IDs=len({r['stable_tree_id'] for r in selected}),executed_code_cells=len(codes),all_saved_code_cells_executed=all(c.get('execution_count') is not None for c in codes),cell_errors=sum(o.get('output_type')=='error' for c in codes for o in c.get('outputs',[])),missing_files=missing,scientific_data_read=False,packages_installed=False,home_PC_runtime_tested=False)
    result['passed']=not missing and result['manual_V2_PLYs']==result['review_V2_PLYs']==163 and result['selected_input_PLYs']==result['selected_unique_IDs']==10 and result['cell_errors']==0
    dump(W/'validation/home_portability_validation.json',result);print(json.dumps(result,indent=2));return result
def configure(rscript):
    rscript=Path(rscript).resolve()
    if not rscript.is_file():raise FileNotFoundError(rscript)
    candidates=[rscript.with_name('R.exe'),rscript.parent/'x64/R.exe']
    rex=next((p for p in candidates if p.is_file()),None)
    if rex is None:raise FileNotFoundError('Cannot locate R.exe alongside the configured Rscript.exe')
    if Path(sys.prefix).resolve()!=(W/'.home-venv').resolve():raise RuntimeError('Run configure with the newly recreated .home-venv Python, not the copied old environment')
    lib=W/'environment/home-R-library'
    if not (lib/'IRkernel').is_dir() or not (lib/'ITSMe').is_dir():raise RuntimeError('Install/verify the fresh home R library first; see HOME_PC_SETUP.md')
    dump(W/'.home-venv/share/jupyter/kernels/info6003-home-ir/kernel.json',dict(argv=[str(rex),'--vanilla','--slave','-e','IRkernel::main()','--args','{connection_file}'],display_name='R (INFO6003 Home)',language='R',env=dict(R_LIBS_USER=str(lib),LC_ALL='C',LANG='C',LANGUAGE='',RGL_USE_NULL='TRUE',INFO6003_PROJECT_ROOT=str(ROOT))))
    dump(W/'environment/home_runtime.json',dict(Rscript=str(rscript),R_executable=str(rex),R_library_relative='measurement_pipeline/environment/home-R-library',Python_relative='measurement_pipeline/.home-venv/Scripts/python.exe',kernel='info6003-home-ir'))
    print('Home kernel configured. Launch START_HOME_JUPYTER.cmd; no notebook executed.')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','check','configure']);parser.add_argument('--rscript');args=parser.parse_args()
    if args.action=='prepare':prepare();print('Portable notebook copies and root-relative manifest saved; no measurement executed.')
    elif args.action=='check':sys.exit(0 if check()['passed'] else 1)
    elif args.action=='configure':
        if not args.rscript:parser.error('--rscript is required on the home PC')
        configure(args.rscript)
