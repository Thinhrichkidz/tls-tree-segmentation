"""Execute a one-tree ITSMe notebook through a real project-local IRkernel."""
from pathlib import Path
import os,json,sys,datetime,hashlib,shutil,subprocess,re
W=Path(__file__).resolve().parents[1]
R_EXE=Path('C:/Program Files/R/R-4.5.2/bin/x64/R.exe')
LIB=W/'environment/R-library'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_json(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def configure():
    kernel=W/'.venv/share/jupyter/kernels/info6003-ir';kernel.mkdir(parents=True,exist_ok=True)
    write_json(kernel/'kernel.json',dict(argv=[str(R_EXE),'--vanilla','--slave','-e','IRkernel::main()','--args','{connection_file}'],display_name='R (INFO6003 ITSMe)',language='R',env=dict(R_LIBS_USER=str(LIB),LC_ALL='C',LANG='C',LANGUAGE='',RGL_USE_NULL='TRUE')))
    notebook=W/'notebooks/ITSMe_V2_10_selected_trees.ipynb'
    import nbformat
    n=nbformat.read(notebook,as_version=4)
    for c in n.cells:
        if c.cell_type=='code':
            c.source=c.source.replace('check.names = FALSE, stringsAsFactors = FALSE)','check.names = FALSE, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM")')
            c.source=c.source.replace('read.csv(review_path, stringsAsFactors=FALSE)','read.csv(review_path, stringsAsFactors=FALSE, fileEncoding="UTF-8-BOM")')
            c.source=c.source.replace('title=paste(TREE_ID, "provisional ground-referenced height")','title=paste(TREE_ID, "\\nGround-referenced height (provisional)")')
    if not any('Project-local R package library' in c.source for c in n.cells):
        n.cells.insert(1,nbformat.v4.new_code_cell('# Project-local R package library; no installation performed inside the notebook\nproject_lib <- "'+LIB.as_posix()+'"\nif (!dir.exists(project_lib)) stop("Run the project environment setup first.")\n.libPaths(c(project_lib, .Library))\nSys.setenv(RGL_USE_NULL="TRUE")\n'))
    n.metadata.kernelspec={'name':'info6003-ir','display_name':'R (INFO6003 ITSMe)','language':'R'}
    nbformat.validate(n);nbformat.write(n,notebook)
    launcher='''@echo off
set "PIPELINE_DIR=%~dp0"
set "R_LIBS_USER=%PIPELINE_DIR%environment\\R-library"
set "LC_ALL=C"
set "LANG=C"
set "RGL_USE_NULL=TRUE"
set "PATH=%PIPELINE_DIR%.venv\\Scripts;%PATH%"
"%PIPELINE_DIR%.venv\\Scripts\\python.exe" -m jupyterlab --notebook-dir "%PIPELINE_DIR%."
'''
    (W/'START_ITSME_JUPYTER.cmd').write_text(launcher,encoding='ascii')
    (W/'.env').write_text('# Project-local runtime configuration; START_ITSME_JUPYTER.cmd applies these settings.\nR_LIBS_USER='+LIB.as_posix()+'\nRGL_USE_NULL=TRUE\nLC_ALL=C\n',encoding='utf-8')
    return n

def main():
    os.environ.update(R_LIBS_USER=str(LIB),RGL_USE_NULL='TRUE',LC_ALL='C',LANG='C',LANGUAGE='')
    os.environ['PATH']=str(W/'.venv/Scripts')+os.pathsep+os.environ['PATH']
    import nbformat
    from nbclient import NotebookClient
    from nbconvert import HTMLExporter
    n=configure()
    stamp=datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=11))).strftime('%Y%m%d_%H%M%S')
    out=W/'results'/('ITSMe_notebook_test_tree_146_'+stamp);out.mkdir(exist_ok=False)
    originals=[W/'notebooks/04_ARS_TLS_practical_ITSME.ipynb',W/'notebooks/03_ARS_TLS_practical_QSM.ipynb']
    baseline={str(p):digest(p) for p in originals}
    for c in n.cells:
        if c.cell_type=='code':
            c.source=c.source.replace('RUN_DBH <- FALSE','RUN_DBH <- TRUE').replace('RUN_OTHER_DIAMETERS <- FALSE','RUN_OTHER_DIAMETERS <- TRUE').replace('RUN_CROWN <- FALSE','RUN_CROWN <- TRUE').replace('RUN_SENSITIVITY <- FALSE','RUN_SENSITIVITY <- TRUE')
    for c in n.cells:
        if c.cell_type=='markdown':c.source=c.source.replace('No measurements have been executed in this notebook.','This executed test copy contains actual R-kernel measurements for tree_146 only.')
    n.cells.insert(0,nbformat.v4.new_markdown_cell('# Executed one-tree ITSMe runtime test\n\nUser authorised package installation and testing on 21 October 2026 (Australia/Sydney). Actual R-kernel execution, not Python substitutes for ITSMe. Tree_146 only. Height, provisional DBH, diameter slices, crown routines and the source notebook\'s DBH parameter alternatives enabled. Ground-reference sensitivity checked. No multi-tree batch or QSM. All segmentation decisions remain PENDING. Agreement with an algebraic height reference is a software consistency check, not independent biological validation.'))
    n.cells.append(nbformat.v4.new_markdown_cell('## Runtime validation and PLY-reader precision\nCompare the actual ITSMe output against the prepared geometry, inspect diameter diagnostics, and check precision of the direct PLY-loading route. These checks do not validate crown completeness, terrain survey accuracy or biological ownership.'))
    n.cells.append(nbformat.v4.new_code_cell(r'''
raw_default <- ITSMe::tree_height_pc(pc=tree1, plot=FALSE)
grounded_expected <- max(tree1$Z)
stopifnot(abs(h1$h-grounded_expected)<1e-8)
stopifnot(abs(h1$h-selected$preliminary_height_m)<1e-6)
input_hash <- digest::digest(file=selected$input_ply_path,algo="sha256")
stopifnot(input_hash==selected$review_sha256)
comparison <- data.frame(stable_tree_id=TREE_ID, point_count=nrow(tree1),
  ITSMe_ground_referenced_height_m=h1$h, prepared_supported_top_height_m=selected$preliminary_height_m,
  difference_m=h1$h-selected$preliminary_height_m,
  ITSMe_default_cloud_min_height_m=raw_default$h,
  default_minus_ground_referenced_height_m=raw_default$h-h1$h,
  ground_plane_minus_mesh_m=selected$plane_minus_mesh_m,
  estimated_low_stem_lean_degrees=selected$estimated_low_stem_lean_degrees,
  human_approval="PENDING", validation="SOFTWARE_CONSISTENCY_ONLY_NOT_FIELD_ACCURACY")
write.csv(comparison,file.path(RUN_DIR,paste0(TREE_ID,"_height_method_comparison.csv")),row.names=FALSE)
print(comparison)
scalar_fields <- function(object,stage) {
  vals <- object[vapply(object,function(v) is.atomic(v) && length(v)==1L,logical(1))]
  if(!length(vals))return(NULL)
  data.frame(stable_tree_id=TREE_ID, stage=stage,field=names(vals),value=vapply(vals,as.character,character(1)),
    original_v2_filename=selected$original_v2_filename,review_filename=selected$review_ply_filename,
    review_sha256=selected$review_sha256,human_approval="PENDING",stringsAsFactors=FALSE)
}
metric_rows <- rbind(scalar_fields(h1,"height"),if(exists("dbh1")) scalar_fields(dbh1,"DBH") else NULL,
  if(exists("ca1")) scalar_fields(ca1,"projected_crown_area") else NULL)
write.csv(metric_rows,file.path(RUN_DIR,paste0(TREE_ID,"_provisional_metric_fields.csv")),row.names=FALSE)
slice_count <- sum(tree1$Z>1.3-0.03 & tree1$Z<1.3+0.03)
inspect_plot <- dbh1$plot+ggplot2::labs(title=sprintf("%s: provisional DBH %.2f cm\nInput band: %d observations; arc coverage %.0f%%",TREE_ID,dbh1$dbh*100,slice_count,dbh1$arc_coverage*100))+
  ggplot2::theme(plot.title=ggplot2::element_text(size=12))
ggplot2::ggsave(file.path(RUN_DIR,paste0(TREE_ID,"_dbh_inspection.png")),plot=inspect_plot,width=8,height=7)
sensitivity_objects <- list(baseline_0.06m=dbh1,R2_threshold_0.002=dbh1a,band_0.20m=dbh1b,concavity_3=dbh1c)
plane_ground <- data.frame(X=0,Y=0,Z=selected$plane_minus_mesh_m)
sensitivity_objects$annular_plane_ground <- run_stage("DBH_annular_plane_ground",function()
  ITSMe::dbh_pc(pc=tree1,dtm=plane_ground,r=ground_lookup_radius,functional=TRUE,plot=FALSE))
sensitivity_objects$cloud_min_default_ground <- run_stage("DBH_cloud_min_default_ground",function()
  ITSMe::dbh_pc(pc=tree1,functional=TRUE,plot=FALSE))
ground_levels <- c(0,0,0,0,selected$plane_minus_mesh_m,min(tree1$Z))
bands <- c(.06,.06,.20,.06,.06,.06)
ss <- lapply(seq_along(sensitivity_objects),function(i) {
  obj <- sensitivity_objects[[i]];z <- 1.3+ground_levels[i]
  data.frame(case=names(sensitivity_objects)[i],circle_DBH_cm=obj$dbh*100,functional_DBH_cm=obj$fdbh*100,
    arc_coverage=obj$arc_coverage,package_R2_fit_residual=obj$R2,band_thickness_m=bands[i],
    ground_local_Z_m=ground_levels[i],band_centre_local_Z_m=z,
    input_band_observation_count=sum(tree1$Z>z-bands[i]/2 & tree1$Z<z+bands[i]/2))
})
sensitivity_table <- do.call(rbind,ss)
write.csv(sensitivity_table,file.path(RUN_DIR,paste0(TREE_ID,"_DBH_sensitivity.csv")),row.names=FALSE)
saveRDS(sensitivity_objects,file.path(RUN_DIR,paste0(TREE_ID,"_DBH_sensitivity_objects.rds")))
writeLines(deparse(body(ITSMe::diameter_slice_pc)),file.path(RUN_DIR,"installed_diameter_function_body.txt"))
print(sensitivity_table)
if(exists("diameters")) {
  for(i in seq_along(diameters)) {
    ggplot2::ggsave(file.path(RUN_DIR,paste0(TREE_ID,"_diameter_",names(diameters)[i],".png")),plot=diameters[[i]]$plot,width=7,height=7)
  }
}
absolute_reference <- tree1
absolute_reference$X <- tree1$X+selected$translation_x_m
absolute_reference$Y <- tree1$Y+selected$translation_y_m
absolute_reference$Z <- tree1$Z+selected$translation_z_m
reader_checks <- lapply(c(absolute_PLY=selected$input_ply_path,local_PLY=selected$local_xyzrgb_ply_path), function(path) {
  type <- if(path==selected$input_ply_path) "absolute_PLY" else "local_PLY"
  tryCatch({
    loaded <- ITSMe::read_tree_pc(path=path,samplefactor=1)
    ref <- if(type=="absolute_PLY") absolute_reference else tree1
    distance <- nabor::knn(data=as.matrix(ref[,c("X","Y","Z")]),query=as.matrix(loaded[,c("X","Y","Z")]),k=1)$nn.dists[,1]
    data.frame(reader=type,success=TRUE,point_count=nrow(loaded),reference_count=nrow(ref),
      nearest_XYZ_error_median_m=median(distance),nearest_XYZ_error_max_m=max(distance),
      distinct_Y_values=length(unique(loaded$Y)),reference_distinct_Y_values=length(unique(ref$Y)),
      suitable_for_precision_sensitive_diameter=nrow(loaded)==nrow(ref) && max(distance)<0.0001,
      error="",stringsAsFactors=FALSE)
  },error=function(e) data.frame(reader=type,success=FALSE,point_count=NA,reference_count=nrow(tree1),
      nearest_XYZ_error_median_m=NA,nearest_XYZ_error_max_m=NA,distinct_Y_values=NA,
      reference_distinct_Y_values=NA,suitable_for_precision_sensitive_diameter=FALSE,
      error=conditionMessage(e),stringsAsFactors=FALSE))
})
reader_checks <- do.call(rbind,reader_checks)
write.csv(reader_checks,file.path(RUN_DIR,paste0(TREE_ID,"_PLY_reader_precision.csv")),row.names=FALSE)
print(reader_checks)
saveRDS(list(height=h1,dbh=if(exists("dbh1"))dbh1 else NULL,
  diameter_slices=if(exists("diameters"))diameters else NULL,
  crown_area=if(exists("ca1"))ca1 else NULL,comparison=comparison,reader_checks=reader_checks),
  file.path(RUN_DIR,paste0(TREE_ID,"_runtime_validation_objects.rds")))
writeLines(capture.output(sessionInfo()),file.path(RUN_DIR,"executed_session_info.txt"))
cat("ITSME_RUN_DIR=",normalizePath(RUN_DIR,winslash="/"),"\n",sep="")
'''))
    n.metadata['info6003_execution']={'tree_id':'tree_146','single_tree_only':True,'R_library':str(LIB),'source_working_notebook':str(W/'notebooks/ITSMe_V2_10_selected_trees.ipynb')}
    nbformat.write(n,out/'ITSMe_tree_146_test_input.ipynb')
    executed=out/'ITSMe_tree_146_EXECUTED.ipynb';error=None
    def done(cell,cell_index,**kwargs):print('Executed cell',cell_index,flush=True)
    try:
        NotebookClient(n,kernel_name='info6003-ir',timeout=600,startup_timeout=120,resources={'metadata':{'path':str(W/'notebooks')}},on_cell_executed=done).execute()
    except Exception as e:
        error=repr(e);print('NOTEBOOK_EXECUTION_ERROR',error,flush=True)
    finally:
        nbformat.write(n,executed)
        html,_=HTMLExporter().from_notebook_node(n);(out/'ITSMe_tree_146_EXECUTED.html').write_text(html,encoding='utf-8')
        text='\n'.join(o.get('text','') for c in n.cells if c.cell_type=='code' for o in c.get('outputs',[]) if o.get('output_type')=='stream')
        (out/'execution_console.txt').write_text(text,encoding='utf-8')
        matches=re.findall(r'ITSME_RUN_DIR=(.+)',text)
        result=dict(success=error is None,error=error,executed_notebook=str(executed),executed_html=str(out/'ITSMe_tree_146_EXECUTED.html'),metrics_directory=matches[-1].strip() if matches else None,original_notebooks_unchanged=all(digest(Path(p))==h for p,h in baseline.items()),tree_id='tree_146',kernel='info6003-ir',height_DBH_diameter_crown_requested=True,QSM_run=False,human_approval='PENDING')
        write_json(out/'execution_result.json',result);write_json(W/'validation/latest_itsme_notebook_execution.json',result)
        print(json.dumps(result,indent=2),flush=True)
    if error:sys.exit(1)

if __name__=='__main__':main()
