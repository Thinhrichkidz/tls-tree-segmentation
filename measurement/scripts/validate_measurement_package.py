from preliminary_heights import *
import ast,struct,itertools

def main():
    rows=csvread(W/'results/all_tree_preliminary_heights.csv');selected=csvread(W/'results/top10_selection_manifest.csv');current=csvread(ROOT/'segmentation_v2_correction/new_cloudcompare_review_manifest.csv');byid={r['stable_tree_id']:r for r in current}
    assert len(rows)==len(byid)==163 and {r['stable_tree_id'] for r in rows}==set(byid)
    assert all(np.isfinite(float(r['preliminary_height_m'])) and float(r['preliminary_height_m'])>0 for r in rows)
    original_checks=[];review_checks=[]
    for r in rows:
        m=byid[r['stable_tree_id']];original=ROOT/'manual_seg_v2'/m['original_filename'];review=ROOT/'CloudCompare_review_v2'/m['review_filename']
        original_checks.append(dict(stable_tree_id=r['stable_tree_id'],match=sha(original)==m['original_sha256']))
        review_checks.append(dict(stable_tree_id=r['stable_tree_id'],match=sha(review)==m['review_sha256']==r['review_sha256']))
        assert r['original_v2_filename']==m['original_filename'] and r['review_ply_filename']==m['review_filename'] and int(r['point_count'])==int(m['output_point_count'])
    assert all(r['match'] for r in original_checks+review_checks)
    untouched=[]
    for entry in json.loads((ROOT/'segmentation_v2_analysis/validation/source_inventory_before.json').read_text()):
        if entry['relative_path'].split('/')[0] in ['raw','terrain']:
            p=ROOT/entry['relative_path'];untouched.append(dict(path=str(p),match=sha(p)==entry['sha256']))
    assert untouched and all(r['match'] for r in untouched)
    notebook_baseline=json.loads((W/'validation/original_notebook_hashes.json').read_text());assert all(sha(Path(r['path']))==r['sha256'] for r in notebook_baseline)
    disk=list((W/'input_trees').rglob('*.ply'));assert len(disk)==10 and len(selected)==10 and len({r['stable_tree_id'] for r in selected})==10
    assert {str(p) for p in disk}=={r['input_ply_path'] for r in selected}
    localchecks=[]
    for r in selected:
        tid=r['stable_tree_id'];source=read(Path(r['source_ply_path']));copy=read(Path(r['input_ply_path']));assert len(copy)==int(r['point_count']) and source.dtype==copy.dtype and sha(Path(r['input_ply_path']))==r['review_sha256']
        origin=np.array([float(r[f'translation_{a}_m']) for a in 'xyz']);plain=read(Path(r['local_xyzrgb_ply_path']));p=xyz(copy);lp=xyz(plain)
        assert len(lp)==len(p) and np.array_equal(lp+origin,p) and set(np.unique(plain['red']))=={200} and set(np.unique(plain['green']))=={100} and set(np.unique(plain['blue']))=={50}
        txt=np.loadtxt(r['local_xyz_path'],skiprows=1);assert txt.shape==p.shape and np.max(np.abs(txt+origin-p))<1e-8
        mesh=PlyData.read(r['local_terrain_mesh_path']);vertices=xyz(mesh['vertex'].data);faces=np.stack(mesh['face'].data['vertex_indices']);assert np.isfinite(vertices).all() and faces.min()>=0 and faces.max()<len(vertices)
        o=vertices[:,:2].min(0);interp=LinearTriInterpolator(Triangulation(vertices[:,0]-o[0],vertices[:,1]-o[1],faces),vertices[:,2]);foot_z=float(interp(-o[0],-o[1]));assert abs(foot_z)<1e-7
        ground=np.loadtxt(r['local_ground_reference_path'],skiprows=1);assert np.array_equal(ground,np.zeros(3))
        assert r['qc_screen_eligible']=='True' and r['human_approval']=='PENDING' and r['overall_height_confidence']=='MEDIUM_PROVISIONAL'
        assert (W/'qc_figures'/f'{tid}_selected_3D_sideviews.png').is_file()
        localchecks.append(dict(stable_tree_id=tid,primary_ply_matches_source=True,original_schema_preserved=True,point_count=len(copy),local_xyz_exact_roundtrip=True,TXT_error_m=float(np.max(np.abs(txt+origin-p))),local_mesh_interpolated_foot_z_m=foot_z,ground_reference_zero=True))
    python_nb=json.loads((W/'notebooks/QSM_V2_10_selected_trees.ipynb').read_text(encoding='utf-8'));r_nb=json.loads((W/'notebooks/ITSMe_V2_10_selected_trees.ipynb').read_text(encoding='utf-8'))
    for n in [python_nb,r_nb]:
        assert n['nbformat']==4 and n['cells'] and len({c['id'] for c in n['cells']})==len(n['cells'])
        assert all(c.get('execution_count') is None and c.get('outputs',[])==[] for c in n['cells'] if c['cell_type']=='code')
    assert r_nb['metadata']['kernelspec']['name']=='ir' and python_nb['metadata']['kernelspec']['name']=='python3'
    # Test only the standard-library conversion-file validator, not modelling/notebook stages.
    validation_cell=next(''.join(c['source']) for c in python_nb['cells'] if c['cell_type']=='code' and 'def iter_scalar_vertex_xyz' in ''.join(c['source']))
    tree=ast.parse(validation_cell);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Assign)) and (isinstance(n,ast.FunctionDef) or any(isinstance(t,ast.Name) and t.id=='scalar_types' for t in n.targets))]
    context={'Path':Path,'struct':struct};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<PLY validator only>','exec'),context)
    tested=next(r for r in selected if r['stable_tree_id']=='tree_146');actual=np.array(list(context['iter_scalar_vertex_xyz'](tested['local_xyzrgb_ply_path'])));assert np.array_equal(actual,xyz(read(Path(tested['local_xyzrgb_ply_path']))))
    syntax=json.loads((W/'validation/adapted_notebook_static_validation.json').read_text());assert syntax['R_parse_returncode']==0 and syntax['python_code_cells_parse']
    tall=csvread(W/'results/top5_tallest.csv');short=csvread(W/'results/top5_shortest.csv')
    assert len(tall)==len(short)==5 and [r['stable_tree_id'] for r in tall]==[r['stable_tree_id'] for r in selected if r['selection_group']=='5_tallest']
    assert [r['stable_tree_id'] for r in short]==[r['stable_tree_id'] for r in selected if r['selection_group']=='5_shortest']
    required=['results/all_tree_preliminary_heights.csv','results/top5_tallest.csv','results/top5_shortest.csv','results/top10_selection_manifest.csv','results/tree_height_ranking_methodology.md','measurement_pipeline_readme.md','notebooks/ITSMe_V2_10_selected_trees.ipynb','notebooks/QSM_V2_10_selected_trees.ipynb','terrain_reference/selected_tree_ground_references.csv']
    assert all((W/p).is_file() and (W/p).stat().st_size>0 for p in required)
    inventory=[]
    for p in W.rglob('*'):
        if p.is_file() and p.suffix in ['.csv','.md','.ipynb','.ply','.txt','.png'] and 'matplotlib' not in str(p):inventory.append(dict(relative_path=p.relative_to(W).as_posix(),bytes=p.stat().st_size))
    dump(W/'validation/final_package_validation.json',dict(preparation_validation_passed=True,export_count=163,finite_preliminary_heights=163,final_screened_population=24,selected_distinct_ids=10,selected_primary_ply_files=10,source_manual_PLY_hash_checks=original_checks,current_review_PLY_hash_checks=review_checks,raw_and_terrain_hash_checks=untouched,original_notebook_hashes_unchanged=True,all_selected_local_frame_checks=localchecks,R_syntax_parse=True,Python_syntax_parse=True,standard_library_PLY_parser_test=dict(tree_id='tree_146',point_count=len(actual),exact_XYZ_match=True),notebook_measurement_cells_executed=False,ITSMe_smoke_test='NOT_RUN: missing ITSMe, Jupyter/IRkernel',QSM='NOT_RUN: native tools missing, Docker engine unavailable; ray conversion not run',no_packages_installed=True,no_segmentation_generated_or_modified=True,all_human_approval='PENDING',status='PREPARED_WITH_QC_WARNINGS_AND_ENVIRONMENT_BLOCKERS',deliverable_inventory=inventory))
    print('FINAL_PREPARATION_VALIDATION_PASSED; no runtime measurement success claimed',flush=True)

if __name__=='__main__':main()
