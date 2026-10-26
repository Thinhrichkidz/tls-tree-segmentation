"""Read-only, terrain-referenced preliminary measurements; no segmentation changes."""
from pathlib import Path
import sys, os, json, csv, hashlib, time
W=Path(__file__).resolve().parents[1]; ROOT=W.parent
sys.path.insert(0,str(ROOT/'verification_output/_deps'))
os.environ['MPLCONFIGDIR']=str(W/'checkpoints/matplotlib')
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.optimize import least_squares
from plyfile import PlyData
import matplotlib
matplotlib.use('Agg')
from matplotlib.tri import Triangulation,LinearTriInterpolator

def xyz(v): return np.column_stack([v[k] for k in ('x','y','z')]).astype('f8')
def read(p): return PlyData.read(str(p),mmap='r')['vertex'].data
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8388608),b''):h.update(b)
    return h.hexdigest()
def dump(p,o):
    def default(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        if isinstance(x,Path):return str(x)
        raise TypeError(type(x).__name__)
    p.write_text(json.dumps(o,indent=2,default=default,allow_nan=False),encoding='utf-8')
def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def csvwrite(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

def circle(q,rng):
    """Location aid only. Radius is not a DBH result; horizontal cuts of lean are elliptical."""
    if len(q)<12:return None
    origin=np.median(q,axis=0);q=q-origin;best=None
    for _ in range(110):
        a,b,c=q[rng.choice(len(q),3,False)];m=2*np.array([b-a,c-a]);rhs=np.array([b@b-a@a,c@c-a@a])
        if abs(np.linalg.det(m))<1e-7:continue
        cen=np.linalg.solve(m,rhs);rad=np.linalg.norm(a-cen)
        if not .035<rad<1.0:continue
        tol=max(.035,min(.075,rad*.16));err=np.abs(np.linalg.norm(q-cen,axis=1)-rad);ok=err<tol
        if ok.sum()<12 or ok.mean()<.55:continue
        angles=np.arctan2(*(q[ok]-cen).T[::-1]);coverage=len(np.unique(np.floor((angles+np.pi)/(np.pi/12)).astype(int)))
        if coverage<11:continue
        score=ok.sum()*(coverage/24)**1.5
        if best is None or score>best[0]:best=(score,cen,rad,ok,tol)
    if best is None:return None
    _,cen,rad,ok,tol=best
    opt=least_squares(lambda x:np.linalg.norm(q[ok]-x[:2],axis=1)-x[2],np.r_[cen,rad],loss='soft_l1',f_scale=.025,bounds=([-2,-2,.025],[2,2,1.05]))
    cen=opt.x[:2];rad=opt.x[2];err=np.abs(np.linalg.norm(q-cen,axis=1)-rad);ok=err<tol
    if ok.sum()<12:return None
    angles=np.arctan2(*(q[ok]-cen).T[::-1]);cov=len(np.unique(np.floor((angles+np.pi)/(np.pi/12)).astype(int)))*15
    return dict(center=(cen+origin).tolist(),support=int(ok.sum()),coverage=cov,residual=float(np.median(err[ok])))

def main():
    print('Loading actual mesh and classified-ground support',flush=True)
    manifest=csvread(ROOT/'segmentation_v2_correction/new_tree_quality_report.csv')
    originals=list((W/'notebooks').glob('*ARS_TLS*.ipynb'))
    dump(W/'validation/original_notebook_hashes.json',[dict(path=str(p),sha256=sha(p)) for p in originals])
    mesh=np.load(ROOT/'verification_output/terrain_arrays.npz');mv=mesh['vertices'];mf=mesh['faces'];offset=mv[:,:2].min(0)
    tri=Triangulation(mv[:,0]-offset[0],mv[:,1]-offset[1],mf);finder=tri.get_trifinder();interp=LinearTriInterpolator(tri,mv[:,2])
    def ground(p):
        p=np.atleast_2d(p);return np.ma.filled(interp(p[:,0]-offset[0],p[:,1]-offset[1]),np.nan)
    raw=read(next((ROOT/'raw').glob('*.ply')));cls=raw['scalar_Classification'];gp=xyz(raw[cls==2]);gt=cKDTree(gp[:,:2])
    boundary=np.load(ROOT/'verification_output/mesh_boundary_edges.npy');bt=cKDTree(mv[np.unique(boundary),:2]);rows=[]
    for num,entry in enumerate(manifest):
        tid=entry['stable_tree_id'];cache=W/'checkpoints'/f'{tid}_height.json'
        if cache.exists():
            cached=json.loads(cache.read_text())['row']
            if cached['preliminary_height_m'] is not None:
                rows.append(cached);continue
        p=xyz(read(ROOT/'CloudCompare_review_v2'/entry['review_filename']));assert np.isfinite(p).all()
        old=json.loads((ROOT/'segmentation_v2_correction/checkpoints'/f'{tid}_screen.json').read_text())
        gz=ground(p);clear=p[:,2]-gz;near=p[np.isfinite(clear)&(clear>.30)&(p[:,2]<p[:,2].min()+4.5)]
        if len(near)<60:
            # Missing bases: fit observed low structure, never manufacture a stem.
            near=p[(p[:,2]>p[:,2].min()+.15)&(p[:,2]<p[:,2].min()+3.5)]
        stations=[];ambiguous=0;rng=np.random.default_rng(6003+num)
        if len(near):
            for z in np.arange(near[:,2].min()+.12,near[:,2].max(),.25):
                sl=near[np.abs(near[:,2]-z)<.14]
                if len(sl)<12:continue
                pairs=cKDTree(sl[:,:2]).query_pairs(.14,output_type='ndarray')
                _,lab=connected_components(coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(sl),len(sl))).tocsr(),directed=False)
                counts=np.bincount(lab);models=[]
                for j in np.argsort(counts)[-3:][::-1]:
                    q=sl[lab==j]
                    if len(q)<12:continue
                    if np.ptp(q[:,:2],axis=0).max()>2.2:continue
                    model=circle(q[:,:2],rng)
                    if model and model['coverage']>=165:models.append(model)
                if not models:continue
                models.sort(key=lambda m:m['support']*(m['coverage']/360)**1.5,reverse=True)
                if len(models)>1 and models[1]['support']>.35*models[0]['support']:ambiguous+=1
                stations.append(dict(z=float(z),**models[0]))
        foot_method='LOWEST_OBSERVATION_XY_FALLBACK_UNCERTAIN';foot=p[np.argmin(p[:,2]),:2].copy();axis_error=None;lean=None;axis_span=0.;lowest_station=None;axis_coeff=None
        if len(stations)>=4:
            zz=np.array([s['z'] for s in stations]);cc=np.array([s['center'] for s in stations]);zo=float(np.median(zz));a=np.c_[np.ones(len(zz)),zz-zo]
            fit=least_squares(lambda x:(a@x.reshape(2,2)-cc).ravel(),np.linalg.lstsq(a,cc,rcond=None)[0].ravel(),loss='soft_l1',f_scale=.08)
            coeff=fit.x.reshape(2,2);res=np.linalg.norm(a@coeff-cc,axis=1);keep=res<.15
            if keep.sum()>=4 and np.ptp(zz[keep])>=.75:
                coeff=np.linalg.lstsq(a[keep],cc[keep],rcond=None)[0];axis_error=float(np.sqrt(np.mean(np.sum((a[keep]@coeff-cc[keep])**2,axis=1))));axis_span=float(np.ptp(zz[keep]));lowest_station=float(zz[keep].min());lean=float(np.degrees(np.arctan(np.linalg.norm(coeff[1]))));axis_coeff=dict(z_origin=zo,coeff=coeff.tolist())
                trial=coeff[0]+(float(ground(cc[keep][0])[0])-zo)*coeff[1]
                for _ in range(20):
                    g=float(ground(trial)[0])
                    if not np.isfinite(g):break
                    nxt=coeff[0]+(g-zo)*coeff[1]
                    if np.linalg.norm(nxt-trial)<1e-7:trial=nxt;break
                    trial=nxt
                if np.isfinite(ground(trial)[0]):foot=trial;foot_method='ROBUST_LOW_STEM_SECTION_AXIS_INTERSECTION_WITH_ACTUAL_MESH'
        ground_z=float(ground(foot)[0]);ground_z=ground_z if np.isfinite(ground_z) else None
        triangle=int(finder(foot[0]-offset[0],foot[1]-offset[1]));edge_max=None
        if triangle>=0:
            tv=mv[mf[triangle],:2];edge_max=float(max(np.linalg.norm(tv[i]-tv[(i+1)%3]) for i in range(3)))
        ids=np.array(gt.query_ball_point(foot,1.0),dtype=int);gg=gp[ids];dist=np.linalg.norm(gg[:,:2]-foot,axis=1);gg=gg[dist>=.30]
        plane_z=None;plane_rmse=None;plane_n=len(gg);sectors=0
        if len(gg)>=20:
            delta=gg[:,:2]-foot;A=np.c_[np.ones(len(gg)),delta];fit=least_squares(lambda c:A@c-gg[:,2],np.linalg.lstsq(A,gg[:,2],rcond=None)[0],loss='soft_l1',f_scale=.04)
            err=A@fit.x-gg[:,2];ok=np.abs(err)<.10
            if ok.sum()>=20:
                co=np.linalg.lstsq(A[ok],gg[ok,2],rcond=None)[0];plane_z=float(co[0]);plane_rmse=float(np.sqrt(np.mean((A[ok]@co-gg[ok,2])**2)));plane_n=int(ok.sum());ang=np.arctan2(delta[ok,1],delta[ok,0]);sectors=len(np.unique(np.floor((ang+np.pi)/(np.pi/4)).astype(int)))
        disagreement=None if plane_z is None or ground_z is None else plane_z-ground_z
        base_gap=None if ground_z is None else float(p[:,2].min()-ground_z)
        axis_gap=None if ground_z is None or lowest_station is None else lowest_station-ground_z
        # A crown tip needs local support. Points are retained, including unsupported maxima.
        ix=np.union1d(np.flatnonzero(p[:,2]>=p[:,2].max()-3),np.argsort(p[:,2])[-5000:]);cap=p[ix];tree=cKDTree(cap);dd,_=tree.query(cap,k=min(5,len(cap)),workers=4)
        if len(cap)<5:
            supported=np.zeros(len(cap),dtype=bool)
        else:
            supported=(dd[:,4]<=.15)&(dd[:,2]<=.08)
        reliable=ix[supported];top_index=int(reliable[np.argmax(p[reliable,2])]) if len(reliable) else None
        top_z=None if top_index is None else float(p[top_index,2]);top_drop=None if top_z is None else float(p[:,2].max()-top_z)
        top_boundary=None if top_index is None else float(bt.query(p[top_index,:2])[0])
        # Boundary distances from previous full-tree sampling and newly checked actual tip.
        bdist=float(old['mesh_boundary_min_sample_distance_m']);fraction=float(old['largest_component_fraction']);contacts=int(old['cross_tree_contact_sample_points'])
        ground_ok=(ground_z is not None and plane_z is not None and abs(disagreement)<=.15 and plane_rmse<=.07 and plane_n>=40 and sectors>=5 and edge_max is not None and edge_max<=2.)
        base_ok=(foot_method.startswith('ROBUST') and axis_error<=.10 and axis_gap is not None and axis_gap<=1.15 and base_gap<=.60 and ambiguous<=1)
        top_ok=(top_z is not None and top_drop<=.20 and fraction>=.98 and bdist>=.75 and top_boundary>=1.)
        single_ok=(fraction>=.98 and contacts<=50 and int(old['significant_voxel_components'])<=2 and tid not in ['tree_074','tree_079','tree_098','tree_163'])
        # A supported tip cannot prove biological crown completeness. Further visual screen below.
        eligible=bool(ground_ok and base_ok and top_ok and single_ok)
        flags=[]
        if not ground_ok:flags.append('GROUND_REFERENCE_UNCERTAIN')
        if not base_ok:flags.append('STEM_FOOT_OR_BASE_UNCERTAIN')
        if not top_ok:flags.append('TOP_OR_BOUNDARY_REVIEW')
        if not single_ok:flags.append('SINGLE_TREE_OWNERSHIP_REVIEW')
        if top_drop and top_drop>0:flags.append('UNSUPPORTED_MAXIMUM_NOT_USED_FOR_HEIGHT')
        if entry['processing_status']=='AUTO_CANDIDATE':flags.append('CORRECTION_NOT_HUMAN_APPROVED')
        if tid=='tree_079':flags.append('PRIOR_GROUND_AND_CROWN_WARNINGS_PRESERVED')
        h=None if top_z is None or ground_z is None else top_z-ground_z
        row=dict(stable_tree_id=tid,original_v2_filename=entry['original_filename'],review_ply_filename=entry['review_filename'],point_count=len(p),minimum_observed_z_m=float(p[:,2].min()),maximum_observed_z_m=float(p[:,2].max()),raw_z_range_m=float(np.ptp(p[:,2])),stem_foot_x_m=float(foot[0]),stem_foot_y_m=float(foot[1]),estimated_local_ground_z_m=ground_z,highest_supported_z_m=top_z,preliminary_height_m=h,height_method='Supported observed top minus actual-triangle mesh at estimated stem foot',foot_method=foot_method,ground_reference_reliability='LOCALLY_SUPPORTED' if ground_ok else 'LOW_OR_UNKNOWN',tree_top_reliability='LOCALLY_SUPPORTED_OBSERVED_TIP' if top_ok else 'REVIEW_REQUIRED',stem_base_completeness='OBSERVATIONS_NEAR_SUPPORTED_FOOT' if base_ok else 'MISSING_OR_UNCERTAIN',crown_completeness='NOT_CERTIFIED; observed upper geometry only',possible_neighbouring_tree_contamination='PROXIMITY_CONTACTS_REVIEW' if contacts else 'NO_CONTACT_IN_PRIOR_SAMPLE; NOT_PROOF',current_qc_status=entry['processing_status'],overall_height_confidence='MEDIUM_PROVISIONAL' if eligible else 'LOW_OR_UNKNOWN',qc_screen_eligible=eligible,human_approval='PENDING',ground_plane_z_m=plane_z,plane_minus_mesh_m=disagreement,ground_plane_inlier_n=plane_n,ground_plane_rmse_m=plane_rmse,ground_angular_sectors_of_8=sectors,foot_triangle_max_edge_m=edge_max,lowest_point_above_foot_ground_m=base_gap,lowest_fitted_section_above_ground_m=axis_gap,stem_axis_fit_rmse_m=axis_error,stem_axis_fit_vertical_span_m=axis_span,estimated_low_stem_lean_degrees=lean,ambiguous_stem_sections=ambiguous,unsupported_top_drop_m=top_drop,highest_supported_point_row=top_index,prior_largest_component_fraction=fraction,prior_significant_components=old['significant_voxel_components'],prior_cross_tree_sample_contacts=contacts,mesh_boundary_min_sample_distance_m=bdist,tip_boundary_distance_m=top_boundary,prior_qc_flags=entry['qc_flags'],height_qc_flags='|'.join(flags),review_sha256=sha(ROOT/'CloudCompare_review_v2'/entry['review_filename']))
        assert row['review_sha256']==entry['review_sha256']
        dump(cache,dict(row=row,stem_sections=stations,stem_axis=axis_coeff,top_xyz=None if top_index is None else p[top_index].tolist(),interpretation='No biological completeness or human approval asserted.'))
        rows.append(row)
        print(tid,'h=',None if h is None else round(h,3),'eligible=',eligible,'ground',ground_ok,'base',base_ok,'top',top_ok,'single',single_ok,flush=True)
    csvwrite(W/'results/all_tree_preliminary_heights.csv',rows)
    valid=[r for r in rows if r['preliminary_height_m'] is not None];valid.sort(key=lambda r:r['preliminary_height_m'])
    screened=[r for r in valid if r['qc_screen_eligible']]
    print('SCREENED',len(screened),[r['stable_tree_id'] for r in screened],flush=True)
    for label,arr in [('all_exports',valid),('screened_initial',screened)]:
        for name,rr in [('shortest',arr[:5]),('tallest',arr[::-1][:5])]:
            if rr:csvwrite(W/'results'/f'top5_{name}_{label}.csv',[dict(rank=i+1,ranking_set=label,**r) for i,r in enumerate(rr)])
    dump(W/'validation/height_calculation_summary.json',dict(exports=len(rows),finite_heights=len(valid),initial_screened=len(screened),raw_class2_points=len(gp),terrain_vertices=len(mv),terrain_triangles=len(mf),all_review_hashes_match=True,source_coordinates_modified=False))

if __name__=='__main__':main()
