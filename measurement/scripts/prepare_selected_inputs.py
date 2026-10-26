from preliminary_heights import *
import shutil
from plyfile import PlyElement
import matplotlib.pyplot as plt

VISUAL_EXCLUSIONS={
    'tree_088':'Bare upper stem without an observed foliage crown; broken/dead stem versus complete live tree unresolved. Exclude from complete-tree comparison.',
    'tree_050':'Bare main leader/branches, no convincing complete upper crown in both side views. Biological completeness unresolved.'}
VISUALLY_INSPECTED=['tree_088','tree_108','tree_152','tree_056','tree_146','tree_151','tree_033','tree_050','tree_103','tree_084','tree_069','tree_026','tree_102','tree_060','tree_114','tree_093']

def main():
    rows=csvread(W/'results/all_tree_preliminary_heights.csv')
    for r in rows:
        r['visual_review']='SIDE_VIEWS_INSPECTED' if r['stable_tree_id'] in VISUALLY_INSPECTED else 'AUTOMATIC_GEOMETRIC_SCREEN_ONLY'
        r['visual_exclusion_reason']=VISUAL_EXCLUSIONS.get(r['stable_tree_id'],'')
        if r['stable_tree_id'] in VISUAL_EXCLUSIONS:
            r['qc_screen_eligible']='False';r['overall_height_confidence']='LOW_OR_UNKNOWN';r['crown_completeness']='BARE_OR_MISSING_CROWN_REVIEW';r['height_qc_flags']+='|BARE_OR_MISSING_CROWN_VISUAL_REVIEW'
        r['comparison_caveat']='Preliminary observed geometry; biological completeness and ownership not certified; human approval PENDING'
    csvwrite(W/'results/all_tree_preliminary_heights.csv',rows)
    eligible=sorted([r for r in rows if r['qc_screen_eligible']=='True'],key=lambda r:float(r['preliminary_height_m']))
    assert len(eligible)>=10
    selected=[]
    for group,arr in [('5_tallest',eligible[::-1][:5]),('5_shortest',eligible[:5])]:
        ranked=[]
        for rank,r in enumerate(arr,1):
            reason='Nominal height extreme among conservatively screened observed trees; supported base/ground/top, no conspicuous multi-tree geometry in side views.'
            ranked.append(dict(rank=rank,ranking_set='QC_SCREENED_PROVISIONAL_NOT_HUMAN_APPROVED',selection_reason=reason,**r))
            selected.append(dict(selection_group=group,rank=rank,selection_reason=reason,**r))
        csvwrite(W/'results'/('top5_tallest.csv' if group=='5_tallest' else 'top5_shortest.csv'),ranked)
    assert len({r['stable_tree_id'] for r in selected})==10
    mm=np.load(ROOT/'verification_output/terrain_arrays.npz');mv=mm['vertices'];mf=mm['faces'];tmin=mv[mf,:2].min(1);tmax=mv[mf,:2].max(1)
    groundrows=[];checks=[]
    for r in selected:
        tid=r['stable_tree_id'];src=ROOT/'CloudCompare_review_v2'/r['review_ply_filename'];dst=W/'input_trees'/r['selection_group']/src.name
        if dst.exists():assert sha(dst)==sha(src),'Existing destination differs: '+str(dst)
        else:shutil.copy2(src,dst)
        v=read(dst);p=xyz(v);origin=np.array([float(r['stem_foot_x_m']),float(r['stem_foot_y_m']),float(r['estimated_local_ground_z_m'])]);local=p-origin
        folder=W/'terrain_reference'/tid;folder.mkdir(exist_ok=True)
        txt=folder/f'{tid}_local_xyz.txt';np.savetxt(txt,local,fmt='%.12f',header='X Y Z',comments='')
        plain=np.empty(len(p),dtype=[('x','f8'),('y','f8'),('z','f8'),('red','u1'),('green','u1'),('blue','u1')])
        for k,name in enumerate(['x','y','z']):plain[name]=local[:,k]
        plain['red']=200;plain['green']=100;plain['blue']=50
        localply=folder/f'{tid}_local_xyzrgb.ply';PlyData([PlyElement.describe(plain,'vertex')],text=False,byte_order='<',comments=['Explicit translation only; original absolute PLY retained','Synthetic uniform colour for single-tree identity; no acquisition rays or surface normals']).write(str(localply))
        lo=p[:,:2].min(0)-1;hi=p[:,:2].max(0)+1;faces=mf[np.all(tmax>=lo,axis=1)&np.all(tmin<=hi,axis=1)];used,inv=np.unique(faces,return_inverse=True);lp=mv[used]-origin;lf=inv.reshape(-1,3).astype('i4')
        vertices=np.empty(len(lp),dtype=[('x','f8'),('y','f8'),('z','f8')])
        for k,name in enumerate(['x','y','z']):vertices[name]=lp[:,k]
        ff=np.empty(len(lf),dtype=[('vertex_indices','i4',(3,))]);ff['vertex_indices']=lf
        meshpath=folder/f'{tid}_terrain_local.ply';PlyData([PlyElement.describe(vertices,'vertex'),PlyElement.describe(ff,'face')],text=False,byte_order='<',comments=['Subset of original mesh triangles with shared explicit translation; no retriangulation']).write(str(meshpath))
        np.savetxt(folder/f'{tid}_terrain_local_xyz.txt',lp,fmt='%.12f',header='X Y Z',comments='')
        groundpath=folder/f'{tid}_foot_ground_local_xyz.txt';groundpath.write_text('X Y Z\n0 0 0\n',encoding='ascii')
        converted=np.loadtxt(txt,skiprows=1);error=float(np.max(np.abs(converted+origin-p)));assert error<1e-8 and len(converted)==len(p)
        assert np.array_equal(xyz(read(localply))+origin,p)
        assert sha(src)==sha(dst)==r['review_sha256']
        r.update(input_ply_path=str(dst),source_ply_path=str(src),input_sha256=sha(dst),local_xyz_path=str(txt),local_xyzrgb_ply_path=str(localply),local_terrain_mesh_path=str(meshpath),local_ground_reference_path=str(groundpath),translation_x_m=origin[0],translation_y_m=origin[1],translation_z_m=origin[2],coordinate_operation='local XYZ = absolute XYZ - (stem-foot X, stem-foot Y, mesh ground Z); constant translation, NOT pointwise terrain flattening',local_colour_policy='uniform RGB 200,100,50 in conversion copy only; source attributes remain in byte-identical primary PLY')
        dump(folder/'coordinate_transform.json',dict(stable_tree_id=tid,absolute_original_filename=r['original_v2_filename'],review_filename=src.name,absolute_to_local_subtract_xyz=origin.tolist(),inverse='absolute = local + subtract_xyz',rotation_or_scaling=False,pointwise_dtm_normalisation=False,metres=True,absolute_coordinate_system='Inherited source global coordinates; previous project records EPSG:32756, no CRS transformation applied',original_attributes='All retained in primary PLY; derivative XYZ/XYZRGB intentionally omit ray/normal/scalar fields',ground_status=r['ground_reference_reliability'],mesh_ground_z_m=origin[2],annular_ground_plane_z_m=float(r['ground_plane_z_m']),plane_minus_mesh_m=float(r['plane_minus_mesh_m']),terrain_face_selection='Original triangle XY bounding boxes intersect full tree XY bounding box expanded by 1m; no new topology',terrain_original_vertex_indices_count=len(used),terrain_triangle_count=len(faces),txt_max_roundtrip_error_m=error))
        groundrows.append({k:r[k] for k in ['stable_tree_id','stem_foot_x_m','stem_foot_y_m','estimated_local_ground_z_m','ground_plane_z_m','plane_minus_mesh_m','ground_reference_reliability','stem_axis_fit_rmse_m','estimated_low_stem_lean_degrees','local_ground_reference_path','local_terrain_mesh_path']})
        checks.append(dict(stable_tree_id=tid,readable=True,count=len(p),source_byte_identical=True,source_attributes=list(v.dtype.names),all_local_xyz_roundtrip_preserved=True,txt_max_roundtrip_error_m=error,mesh_vertices=len(lp),mesh_triangles=len(lf),human_approval='PENDING'))
        # Separate translated displays; scientific files remain unaltered.
        sp=local if len(local)<70000 else local[np.random.default_rng(6003).choice(len(local),70000,False)]
        fig=plt.figure(figsize=(15,6));ax=fig.add_subplot(131,projection='3d');ax.scatter(sp[:,0],sp[:,1],sp[:,2],s=.25,c=sp[:,2],cmap='viridis',alpha=.7,rasterized=True)
        # Mesh shown close to the foot for legible base context.
        near=np.all(np.abs(lp[:,:2])<2.5,axis=1);ax.scatter(lp[near,0],lp[near,1],lp[near,2],s=.3,c='sienna',alpha=.4);ax.scatter([0],[0],[0],c='red',s=30);ax.set_xlabel('X offset m');ax.set_ylabel('Y offset m');ax.set_zlabel('Z above foot ground m')
        for j,k in enumerate([0,1]):
            ax=fig.add_subplot(1,3,j+2);ax.scatter(sp[:,k],sp[:,2],s=.25,c=sp[:,2],cmap='viridis',rasterized=True);ax.scatter(lp[near,k],lp[near,2],s=.4,c='sienna',alpha=.4);ax.scatter([0],[0],c='red',s=30);ax.axhline(0,color='brown',lw=.6);ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel(('X' if k==0 else 'Y')+' offset m');ax.set_ylabel('Z above foot ground m')
        fig.suptitle(f"{tid}: {float(r['preliminary_height_m']):.3f} m preliminary; human approval PENDING");fig.tight_layout();fig.savefig(W/'qc_figures'/f'{tid}_selected_3D_sideviews.png',dpi=150);plt.close(fig)
        print('PREPARED',tid,flush=True)
    csvwrite(W/'results/top10_selection_manifest.csv',selected);csvwrite(W/'terrain_reference/selected_tree_ground_references.csv',groundrows)
    dump(W/'validation/selected_input_validation.json',dict(selected_count=10,screened_population=len(eligible),overlap_ids=[],checks=checks,visual_exclusions=VISUAL_EXCLUSIONS))

if __name__=='__main__':main()
