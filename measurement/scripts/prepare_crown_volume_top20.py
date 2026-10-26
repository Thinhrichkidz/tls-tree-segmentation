"""Versioned preparation for ten tallest and ten shortest from the existing screened ID pool.

Reads review PLYs only. Retains earlier terrain/foot references, refreshes edited-tree tops,
and fits edited low-stem axes to current points without overwriting previous checkpoints.
"""
import ast
import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import sys

MP = Path(__file__).resolve().parents[1]
ROOT = MP.parent
sys.path.insert(0, str(ROOT / 'verification_output' / '_deps'))
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.optimize import least_squares
from plyfile import PlyData

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_rows(path, data, fields=None):
    with Path(path).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(data[0]))
        w.writeheader()
        w.writerows(data)

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else x.tolist()) + '\n', encoding='utf-8')

def points(path):
    v = PlyData.read(str(path), mmap='r')['vertex'].data
    p = np.column_stack([v[k] for k in ('x', 'y', 'z')]).astype('f8')
    assert np.isfinite(p).all()
    return p

tag = f'CROWN_VOLUME_TOP20_{datetime.now():%Y%m%d_%H%M%S}'
batch = MP / 'results' / tag
batch.mkdir(exist_ok=False)
(batch / 'inputs').mkdir()
(batch / 'axis').mkdir()
os.environ['MPLCONFIGDIR'] = str(batch / 'matplotlib_cache')

# Freeze a before-state and verify all 163 against the latest handover.
frozen = rows(ROOT / 'session2_claude_20261023/state/CloudCompare_review_v2_state_20261023.csv')
current = []
for r in frozen:
    path = ROOT / 'CloudCompare_review_v2' / r['file']
    current.append(dict(file=r['file'], sha256=sha(path), expected_sha256=r['sha256']))
assert len(list((ROOT / 'CloudCompare_review_v2').glob('*.ply'))) == len(frozen) == 163
assert all(r['sha256'] == r['expected_sha256'] for r in current), 'Review files changed since Session 2; inspect before proceeding.'
write_rows(batch / 'protected_inputs_before.csv', current)
heights = rows(MP / 'results/all_tree_preliminary_heights.csv')
old_manifest = rows(MP / 'environment/home_selection_manifest_CURRENT_20261023.csv')
old_by_id = {r['stable_tree_id']: r for r in old_manifest}
current_hash = {r['file']: r['sha256'] for r in current}
eligible = [dict(r) for r in heights if r['qc_screen_eligible'].lower() == 'true']
changed_points = {}
refresh = []
for r in eligible:
    actual = current_hash[r['review_ply_filename']]
    if actual == r['review_sha256']:
        continue
    p = points(ROOT / 'CloudCompare_review_v2' / r['review_ply_filename'])
    changed_points[r['stable_tree_id']] = p
    ix = np.union1d(np.flatnonzero(p[:, 2] >= p[:, 2].max() - 3), np.argsort(p[:, 2])[-5000:])
    cap = p[ix]
    dd, _ = cKDTree(cap).query(cap, k=5, workers=2)
    supported = (dd[:, 4] <= .15) & (dd[:, 2] <= .08)
    assert supported.any()
    top_ix = int(ix[supported][np.argmax(cap[supported, 2])])
    previous = r['preliminary_height_m']
    ground = float(r['estimated_local_ground_z_m'])
    r.update(point_count=str(len(p)), review_sha256=actual,
             minimum_observed_z_m=str(p[:, 2].min()), maximum_observed_z_m=str(p[:, 2].max()),
             raw_z_range_m=str(np.ptp(p[:, 2])), highest_supported_z_m=str(p[top_ix, 2]),
             highest_supported_point_row=str(top_ix),
             preliminary_height_m=str(p[top_ix, 2] - ground),
             unsupported_top_drop_m=str(p[:, 2].max() - p[top_ix, 2]),
             lowest_point_above_foot_ground_m=str(p[:, 2].min() - ground))
    refresh.append(dict(stable_tree_id=r['stable_tree_id'], previous_height_m=previous,
                        refreshed_supported_height_m=r['preliminary_height_m'],
                        full_cloud_height_m=float(p[:, 2].max() - ground),
                        reference='Inherited stem foot and actual-mesh ground from previous measurement; screened-ID eligibility is inherited, not reapproved.'))
    print('Refreshed', r['stable_tree_id'], previous, '->', r['preliminary_height_m'], flush=True)

ordered = sorted(eligible, key=lambda r: float(r['preliminary_height_m']))
selected = [('10_tallest_screened', i+1, r) for i, r in enumerate(ordered[::-1][:10])]
selected += [('10_shortest_screened', i+1, r) for i, r in enumerate(ordered[:10])]
assert len({r['stable_tree_id'] for _, _, r in selected}) == 20
write_rows(batch / 'ranking_refreshed_screened_pool.csv', ordered)
dump(batch / 'edited_tree_height_refresh.json', refresh)

# Extract the exact existing low-stem circle-fitting helper, without executing the old preparation script.
original = MP / 'scripts/preliminary_heights.py'
tree = ast.parse(original.read_text(encoding='utf-8-sig'))
circle_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'circle')
exec(compile(ast.Module(body=[circle_node], type_ignores=[]), str(original), 'exec'), globals())

def refresh_axis(tid, p, r):
    from matplotlib.tri import Triangulation, LinearTriInterpolator
    mesh = np.load(ROOT / 'verification_output/terrain_arrays.npz')
    mv, mf = mesh['vertices'], mesh['faces']
    offset = mv[:, :2].min(0)
    tri = Triangulation(mv[:, 0]-offset[0], mv[:, 1]-offset[1], mf)
    interp = LinearTriInterpolator(tri, mv[:, 2])
    low = p[p[:, 2] < p[:, 2].min() + 4.5]
    gz = np.ma.filled(interp(low[:, 0]-offset[0], low[:, 1]-offset[1]), np.nan)
    near = low[np.isfinite(gz) & (low[:, 2]-gz > .3)]
    if len(near) < 60:
        near = p[(p[:, 2] > p[:, 2].min()+.15) & (p[:, 2] < p[:, 2].min()+3.5)]
    stations = []
    rng = np.random.default_rng(6003 + int(tid.split('_')[1])-1)
    for z in np.arange(near[:, 2].min()+.12, near[:, 2].max(), .25):
        sl = near[np.abs(near[:, 2]-z) < .14]
        if len(sl) < 12:
            continue
        pairs = cKDTree(sl[:, :2]).query_pairs(.14, output_type='ndarray')
        _, labels = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                                                     shape=(len(sl), len(sl))).tocsr(), directed=False)
        models = []
        for j in np.argsort(np.bincount(labels))[-3:][::-1]:
            q = sl[labels == j]
            if len(q) < 12 or np.ptp(q[:, :2], axis=0).max() > 2.2:
                continue
            model = circle(q[:, :2], rng)
            if model and model['coverage'] >= 165:
                models.append(model)
        if models:
            models.sort(key=lambda m: m['support']*(m['coverage']/360)**1.5, reverse=True)
            stations.append(dict(z=float(z), **models[0]))
    assert len(stations) >= 4, f'No stable current axis for {tid}'
    zz = np.array([s['z'] for s in stations])
    cc = np.array([s['center'] for s in stations])
    zo = float(np.median(zz))
    a = np.c_[np.ones(len(zz)), zz-zo]
    fit = least_squares(lambda x: (a @ x.reshape(2, 2)-cc).ravel(),
                        np.linalg.lstsq(a, cc, rcond=None)[0].ravel(), loss='soft_l1', f_scale=.08)
    coeff = fit.x.reshape(2, 2)
    keep = np.linalg.norm(a @ coeff-cc, axis=1) < .15
    assert keep.sum() >= 4 and np.ptp(zz[keep]) >= .75
    coeff = np.linalg.lstsq(a[keep], cc[keep], rcond=None)[0]
    rmse = float(np.sqrt(np.mean(np.sum((a[keep] @ coeff-cc[keep])**2, axis=1))))
    assert rmse <= .1
    ground = float(r['estimated_local_ground_z_m'])
    foot = np.array([float(r['stem_foot_x_m']), float(r['stem_foot_y_m'])])
    axis_at_ground = coeff[0] + coeff[1]*(ground-zo)
    checkpoint = dict(row=r, stem_sections=stations,
                      stem_axis=dict(z_origin=zo, coeff=coeff.tolist()),
                      interpretation='Fresh low-stem axis from current points using the original fitting helper; earlier foot-ground reference retained for comparability.',
                      axis_fit_rmse_m=rmse, axis_vertical_span_m=float(np.ptp(zz[keep])),
                      offset_from_inherited_foot_m=float(np.linalg.norm(axis_at_ground-foot)),
                      fit_source_sha256=sha(original))
    return checkpoint

manifest = []
review = []
reviews = rows(MP / 'results/human_review_template_CURRENT_20261023.csv')
review_by_id = {r['stable_tree_id']: r for r in reviews}
template = old_by_id['tree_146']
fields = list(template)
for group, rank, r in selected:
    tid = r['stable_tree_id']
    src = ROOT / 'CloudCompare_review_v2' / r['review_ply_filename']
    p = changed_points.get(tid)
    if p is None:
        p = points(src)
    t = np.array([float(r['stem_foot_x_m']), float(r['stem_foot_y_m']), float(r['estimated_local_ground_z_m'])])
    n = {k: r.get(k, '') for k in fields}
    if tid in old_by_id:
        n.update(old_by_id[tid])
        # Bring stale numerical fields forward from the refreshed ranking record.
        n.update({k: v for k, v in r.items() if k in fields})
    else:
        out = batch / 'inputs' / tid
        out.mkdir()
        local = p-t
        txt = out / f'{tid}_local_xyz.txt'
        np.savetxt(txt, local, fmt='%.12f', header='X Y Z', comments='')
        foot = out / f'{tid}_foot_ground_local_xyz.txt'
        foot.write_text('X Y Z\n0 0 0\n', encoding='ascii')
        error = float(np.abs((np.loadtxt(txt, skiprows=1)+t)-p).max())
        assert error < 1e-9
        dump(out / 'coordinate_transform.json', dict(stable_tree_id=tid, source_file=src.relative_to(ROOT).as_posix(),
             source_sha256=r['review_sha256'], point_count=len(p), absolute_to_local_subtract_xyz=t.tolist(),
             inverse='absolute = local + subtract_xyz', txt_max_roundtrip_error_m=error,
             operation='Translation only; inherited stem-foot XY and actual-mesh ground Z; no resampling or point changes.'))
        n.update(local_xyz_path=txt.relative_to(ROOT).as_posix(),
                 local_ground_reference_path=foot.relative_to(ROOT).as_posix(), local_xyzrgb_ply_path='', local_terrain_mesh_path='')
    # Verify each prepared text against the current PLY, including order and every observation.
    local = np.loadtxt(ROOT / n['local_xyz_path'], skiprows=1)
    assert local.shape == p.shape
    assert np.max(np.abs((local+t)-p)) < 1e-8, f'Stale prepared text for {tid}'
    n.update(selection_group=group, rank=str(rank), selection_reason='Ten observed height extremes within the inherited screened ID pool; current edited-tree tops refreshed with earlier foot-ground references.',
             source_ply_path=src.relative_to(ROOT).as_posix(), input_ply_path=src.relative_to(ROOT).as_posix(),
             review_sha256=sha(src), input_sha256=sha(src),
             translation_x_m=repr(float(t[0])), translation_y_m=repr(float(t[1])), translation_z_m=repr(float(t[2])),
             coordinate_operation='Translation only, local = global - inherited stem-foot XY and mesh ground Z')
    ck = json.loads((MP / 'checkpoints' / f'{tid}_height.json').read_text())
    if ck['row']['review_sha256'] != n['review_sha256']:
        ck = refresh_axis(tid, p, r)
        print('Fresh axis', tid, 'RMSE', ck['axis_fit_rmse_m'], 'foot offset', ck['offset_from_inherited_foot_m'], flush=True)
    dump(batch / 'axis' / f'{tid}_height.json', ck)
    manifest.append(n)
    rv = dict(review_by_id.get(tid, {k: '' for k in reviews[0]}))
    rv.update(stable_tree_id=tid, dataset_version='Current review: 20-tree crown-envelope test',
              review_filename=r['review_ply_filename'], review_sha256=n['review_sha256'],
              original_v2_filename=r['original_v2_filename'], human_decision=rv.get('human_decision') or 'PENDING',
              complete_tree_approved=rv.get('complete_tree_approved') or 'PENDING', measurement_release='PENDING')
    review.append(rv)
    print(group, rank, tid, len(p), r['preliminary_height_m'], flush=True)

manifest_name = tag + '_manifest.csv'
review_name = tag + '_human_review.csv'
write_rows(MP / 'environment' / manifest_name, manifest, fields)
write_rows(MP / 'results' / review_name, review, list(reviews[0]))
config = dict(batch=str(batch), project_root=str(ROOT), manifest_name=manifest_name, review_name=review_name,
              trees=[r['stable_tree_id'] for r in manifest],
              axis_relative=(batch / 'axis').relative_to(ROOT).as_posix(),
              screened_pool_count=len(eligible), selection_caveat='Earlier screened ID eligibility retained; not a fresh completeness/ownership certification. Ranking heights retain earlier ground references. No field validation.')
dump(batch / 'batch_config.json', config)
print('CONFIG=' + str(batch / 'batch_config.json'), flush=True)
