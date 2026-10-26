"""Read user-cleaned review clouds; save new inputs, axes and DBH sensitivity runs."""
import ast, csv, hashlib, json, os, subprocess, sys
from pathlib import Path
from datetime import datetime
MP=Path(__file__).resolve().parents[1]; ROOT=MP.parent
sys.path.insert(0,str(ROOT/'verification_output/_deps'))
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.optimize import least_squares
from plyfile import PlyData
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist()),encoding='utf-8')
def points(p):
    v=PlyData.read(str(p))['vertex'].data
    a=np.column_stack([v[n] for n in ('x','y','z')]).astype('f8');assert np.isfinite(a).all();return a
tag='CLEANED_TRUNK_DBH_'+datetime.now().strftime('%Y%m%d_%H%M%S')
batch=MP/'results'/tag;batch.mkdir();(batch/'axis').mkdir();(batch/'inputs').mkdir()
os.environ['MPLCONFIGDIR']=str(batch/'matplotlib_cache')
files=sorted((ROOT/'CloudCompare_review_v2').glob('*.ply'))
before={p.name:sha(p) for p in files};assert len(before)==163
dump(batch/'protected_inputs_before.json',before)
previous=json.loads((MP/'results/CROWN_VOLUME_TOP20_20261023_164430/protected_inputs_after.json').read_text())
oldhash={r['file']:r['after'] for r in previous}
changed=[n for n,h in before.items() if h!=oldhash[n]]
print('Changed since previous batch:',changed,flush=True)
dump(batch/'user_changes_since_previous_batch.json',changed)
original=MP/'scripts/preliminary_heights.py'
for source,name in [(original,'circle'),(MP/'scripts/prepare_crown_volume_top20.py','refresh_axis')]:
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),globals())
manifest=rows(MP/'environment/CROWN_VOLUME_TOP20_20261023_164430_manifest.csv')
template=(MP/'results/DBH_remaining_band_review_20261023_172945/tree_103/dbh_pc_check/wrapper_review.R').read_text()
prepared=[];changes=[]
for tid in ['tree_103','tree_067','tree_033','tree_108']:
    r=next(dict(r) for r in manifest if r['stable_tree_id']==tid)
    source=ROOT/'CloudCompare_review_v2'/r['review_ply_filename'];p=points(source)
    oldn=int(r['point_count']);oldh=r['review_sha256']
    assert sha(source)!=oldh,f'{tid}: source unchanged; do not reuse stale results'
    t=np.array([float(r['translation_x_m']),float(r['translation_y_m']),float(r['translation_z_m'])])
    folder=batch/'inputs'/tid;folder.mkdir();txt=folder/f'{tid}_local_xyz.txt'
    np.savetxt(txt,p-t,fmt='%.12f',header='X Y Z',comments='')
    err=float(np.abs(np.loadtxt(txt,skiprows=1)+t-p).max());assert err<1e-8
    r.update(review_sha256=sha(source),input_sha256=sha(source),point_count=str(len(p)),local_xyz_path=txt.relative_to(ROOT).as_posix())
    # Axis fitting retains the inherited foot and terrain reference for comparison.
    for k,v in zip(['stem_foot_x_m','stem_foot_y_m','estimated_local_ground_z_m'],t):r[k]=str(v)
    checkpoint=refresh_axis(tid,p,r);dump(batch/'axis'/f'{tid}_height.json',checkpoint)
    dump(folder/'coordinate_transform.json',dict(source=str(source),source_sha256=sha(source),subtract_xyz=t.tolist(),point_count=len(p),roundtrip_error_m=err))
    prepared.append(r)
    changes.append(dict(tree=tid,old_points=oldn,new_points=len(p),removed_points=oldn-len(p),old_sha256=oldh,new_sha256=sha(source),axis_rmse_m=checkpoint['axis_fit_rmse_m'],axis_foot_offset_m=checkpoint['offset_from_inherited_foot_m'],user_note='User cleaned bushes around trunk; tree_033 source data remains poor' if tid=='tree_033' else 'User cleaned bushes around trunk'))
    print('Prepared',tid,oldn,'->',len(p),'axis RMSE',checkpoint['axis_fit_rmse_m'],flush=True)
manifest_path=batch/'cleaned_manifest.csv'
with manifest_path.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(prepared[0]));w.writeheader();w.writerows(prepared)
dump(batch/'input_changes.json',changes)
env=os.environ.copy();env.update(R_LIBS_USER=str(MP/'environment/R-library'),RGL_USE_NULL='TRUE',LC_ALL='C',LANG='C')
completed=[]
for tid in ['tree_103','tree_067','tree_033','tree_108']:
    out=batch/tid;out.mkdir()
    script=template.replace('TREE_ID <- "tree_103"',f'TREE_ID <- "{tid}"')
    script=script.replace('manifest <- read.csv(file.path(WORK,"environment","CROWN_VOLUME_TOP20_20261023_164430_manifest.csv"),',f'manifest <- read.csv("{manifest_path.as_posix()}",')
    script=script.replace('RUN_DIR <- "G:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results/DBH_remaining_band_review_20261023_172945/tree_103/dbh_pc_check"',f'RUN_DIR <- "{out.as_posix()}"')
    script=script.replace('measurement_pipeline/results/CROWN_VOLUME_TOP20_20261023_164430/axis',(batch/'axis').relative_to(ROOT).as_posix())
    script=script.replace('paste0("tree_103_band_",','paste0(TREE_ID,"_band_",')
    # Compare the wrapper with direct fitting at the same five widths.
    script+='\nrows_direct <- list()\nfor(w in c(.06,.10,.15,.20,.30)) {\n d <- tryCatch(ITSMe::diameter_slice_pc(pc=rc,slice_height=1.3,slice_thickness=w,dtm=ground0,r=1.5,functional=TRUE,plot=TRUE),error=function(e) NULL)\n if(is.null(d)) next\n rows_direct[[length(rows_direct)+1]] <- data.frame(band_cm=w*100,diameter_cm=d$diameter*100,arc=d$arc_coverage,rmse_mm=sqrt(d$R2)*1000,accepted=accept(d$arc_coverage,d$R2,d$diameter))\n ggsave(file.path(RUN_DIR,paste0(TREE_ID,"_direct_",w*100,"cm.png")),plot=d$plot,width=7,height=7)\n}\nif(length(rows_direct)) write.csv(do.call(rbind,rows_direct),file.path(RUN_DIR,"direct_band_comparison.csv"),row.names=FALSE)\n'
    rp=out/'review.R';rp.write_text(script,encoding='utf-8')
    with (out/'console.txt').open('w') as log:
        proc=subprocess.run([r'C:\Program Files\R\R-4.5.2\bin\Rscript.exe',str(rp)],env=env,stdout=log,stderr=subprocess.STDOUT)
    result=dict(tree=tid,exit_code=proc.returncode,directory=str(out))
    if (out/'band_comparison.csv').exists():result['bands']=rows(out/'band_comparison.csv')
    if (out/'direct_band_comparison.csv').exists():result['direct_bands']=rows(out/'direct_band_comparison.csv')
    completed.append(result);dump(batch/'runs.json',completed)
    print(json.dumps(result),flush=True)
after={p.name:sha(p) for p in files};assert before==after
dump(batch/'protected_inputs_verified.json',dict(files=163,unchanged_during_run=True,sha256=after))
print('BATCH='+str(batch),flush=True)
