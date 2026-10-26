"""Versioned inputs for the four user-cleaned trees (103, 108, 067, 033) with the user's 23 Oct 2026 decisions.

Decisions (user, in chat, after CLEANED_TRUNK_DIAGNOSIS_20261023_185259):
  * 103, 108: use the corrected stem base (independent slice-centre line meeting the preserved terrain mesh).
  * 033: use the earlier near-vertical axis (the fresh cleaned-cloud axis crossed the stem); foot unchanged.
  * 067: foot/axis unchanged; DBH uses the outer-outline filter (set in the manifest, applied in memory by the notebook).
  * 103: report circle-fit and area-equivalent DBH; 108: DBH stays provisional.
Reads review PLYs only. Writes a new batch folder, a new manifest and a new review sheet; overwrites nothing.
"""
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
from plyfile import PlyData
from matplotlib.tri import Triangulation, LinearTriInterpolator

CLEANED = MP / 'results/CLEANED_TRUNK_DBH_20261023_180414'
DIAG = MP / 'results/CLEANED_TRUNK_DIAGNOSIS_20261023_185259'
TOP20 = MP / 'results/CROWN_VOLUME_TOP20_20261023_164430'
TREES = ['tree_103', 'tree_108', 'tree_067', 'tree_033']

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_rows(path, data, fields):
    with Path(path).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else x.tolist()) + '\n', encoding='utf-8')

def points(path):
    v = PlyData.read(str(path), mmap='r')['vertex'].data
    return np.column_stack([v[k] for k in ('x', 'y', 'z')]).astype('f8')

tag = f'CORRECTED_FOUR_TREE_RERUN_{datetime.now():%Y%m%d_%H%M%S}'
batch = MP / 'results' / tag
batch.mkdir(exist_ok=False)
(batch / 'inputs').mkdir()
(batch / 'axis').mkdir()
os.environ['MPLCONFIGDIR'] = str(batch / 'matplotlib_cache')

# All 163 review PLYs must still match the Session 3 snapshot.
snap = rows(ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv')
state = [dict(file=r['file'], sha256=sha(ROOT / 'CloudCompare_review_v2' / r['file']), expected_sha256=r['sha256']) for r in snap]
assert len(list((ROOT / 'CloudCompare_review_v2').glob('*.ply'))) == len(snap) == 163
assert all(r['sha256'] == r['expected_sha256'] for r in state), 'Review files changed since the Session 3 snapshot; prepare a fresh baseline first.'
write_rows(batch / 'protected_inputs_before.csv', state, ['file', 'sha256', 'expected_sha256'])

cleaned = {r['stable_tree_id']: r for r in rows(CLEANED / 'cleaned_manifest.csv')}
fields = list(next(iter(cleaned.values())))
extra = ['dbh_outline_filter', 'dbh_report_mode', 'reference_decision', 'previous_translation_xyz', 'base_shift_xyz_m']
diag = json.loads((DIAG / 'base_and_067_checks.json').read_text())

def supported_top(p):
    # Same supported-top rule as prepare_crown_volume_top20.py.
    ix = np.union1d(np.flatnonzero(p[:, 2] >= p[:, 2].max() - 3), np.argsort(p[:, 2])[-5000:])
    cap = p[ix]
    dd, _ = cKDTree(cap).query(cap, k=5, workers=2)
    ok = (dd[:, 4] <= .15) & (dd[:, 2] <= .08)
    assert ok.any()
    return int(ix[ok][np.argmax(cap[ok, 2])])

manifest, report = [], []
for tid in TREES:
    r = dict(cleaned[tid])
    src = ROOT / 'CloudCompare_review_v2' / r['review_ply_filename']
    assert sha(src) == r['review_sha256']
    p = points(src)
    t_old = np.array([float(r['translation_x_m']), float(r['translation_y_m']), float(r['translation_z_m'])])
    shift = np.zeros(3)
    ck = json.loads((CLEANED / 'axis' / f'{tid}_height.json').read_text())
    if tid in ('tree_103', 'tree_108'):
        # Corrected base: XY where the independent slice-centre line meets the terrain, Z = terrain mesh there.
        terrain = json.loads((MP / f'terrain_reference/{tid}/coordinate_transform.json').read_text())
        assert np.allclose(terrain['absolute_to_local_subtract_xyz'], t_old, atol=1e-9)
        ply = PlyData.read(str(MP / f'terrain_reference/{tid}/{tid}_terrain_local.ply'))
        v = ply['vertex']
        tri = Triangulation(np.asarray(v['x'], float), np.asarray(v['y'], float), np.vstack(ply['face']['vertex_indices']))
        interp = LinearTriInterpolator(tri, np.asarray(v['z'], float))
        fx, fy = diag[tid[5:]]['independent_line_foot_xy']
        fz = float(interp(fx, fy))
        assert np.isfinite(fz) and abs(fz - diag[tid[5:]]['independent_line_foot_ground_z']) < 1e-9
        shift = np.array([fx, fy, fz])
        decision = 'Corrected base accepted by user 23 Oct 2026: inherited foot lay beside the trunk; new local origin = slice-centre line meeting preserved terrain mesh.'
        ck['interpretation'] = 'Fresh cleaned-cloud low-stem axis (confirmed by independent slice tracking); used with the corrected base.'
    elif tid == 'tree_033':
        old = json.loads((TOP20 / 'axis' / f'{tid}_height.json').read_text())
        ck = dict(row=ck['row'], stem_sections=old['stem_sections'], stem_axis=old['stem_axis'],
                  interpretation='Earlier near-vertical axis (fitted before cleaning) reused on the cleaned points by user decision 23 Oct 2026; the fresh cleaned-cloud axis crossed the stem. Source data poor per user.',
                  axis_source_file=str((TOP20 / 'axis' / f'{tid}_height.json').relative_to(ROOT).as_posix()),
                  axis_source_sha256=sha(TOP20 / 'axis' / f'{tid}_height.json'))
        decision = 'Earlier near-vertical axis kept by user decision 23 Oct 2026; foot unchanged. Source data poor per user; DBH not released.'
    else:
        decision = 'Foot and axis unchanged; DBH uses outer-outline filter by user decision 23 Oct 2026.'
    t = t_old + shift
    out = batch / 'inputs' / tid
    out.mkdir()
    txt = out / f'{tid}_local_xyz.txt'
    np.savetxt(txt, p - t, fmt='%.12f', header='X Y Z', comments='')
    foot = out / f'{tid}_foot_ground_local_xyz.txt'
    foot.write_text('X Y Z\n0 0 0\n', encoding='ascii')
    err = float(np.abs((np.loadtxt(txt, skiprows=1) + t) - p).max())
    assert err < 1e-8
    dump(out / 'coordinate_transform.json', dict(stable_tree_id=tid, source_file=src.relative_to(ROOT).as_posix(),
         source_sha256=r['review_sha256'], point_count=len(p), absolute_to_local_subtract_xyz=t.tolist(),
         inverse='absolute = local + subtract_xyz', txt_max_roundtrip_error_m=err,
         previous_subtract_xyz=t_old.tolist(), base_shift_xyz_m=shift.tolist(),
         operation='Translation only; no resampling or point changes.', reference_decision=decision))
    sa = ck['stem_axis']
    lean = float(np.degrees(np.arctan(np.hypot(*sa['coeff'][1]))))
    ck['row'] = dict(ck['row'], review_sha256=r['review_sha256'])
    dump(batch / 'axis' / f'{tid}_height.json', ck)
    top = supported_top(p)
    r.update(stem_foot_x_m=repr(float(t[0])), stem_foot_y_m=repr(float(t[1])), estimated_local_ground_z_m=repr(float(t[2])),
             translation_x_m=repr(float(t[0])), translation_y_m=repr(float(t[1])), translation_z_m=repr(float(t[2])),
             highest_supported_z_m=repr(float(p[top, 2])), highest_supported_point_row=str(top),
             preliminary_height_m=repr(float(p[top, 2] - t[2])), lowest_point_above_foot_ground_m=repr(float(p[:, 2].min() - t[2])),
             estimated_low_stem_lean_degrees=repr(lean),
             local_xyz_path=txt.relative_to(ROOT).as_posix(), local_ground_reference_path=foot.relative_to(ROOT).as_posix(),
             foot_method='USER_ACCEPTED_CORRECTED_BASE_20261023' if shift.any() else r['foot_method'],
             coordinate_operation='Translation only, local = global - corrected stem-foot XY and terrain-mesh ground Z' if shift.any() else r['coordinate_operation'],
             dbh_outline_filter='TRUE' if tid == 'tree_067' else 'FALSE',
             dbh_report_mode={'tree_103': 'CIRCLE_AND_AREA_EQUIVALENT', 'tree_108': 'PROVISIONAL_ONLY',
                              'tree_067': 'OUTLINE_FILTERED_CIRCLE', 'tree_033': 'NOT_RELEASED_SOURCE_LIMITED'}[tid],
             reference_decision=decision, previous_translation_xyz=json.dumps(t_old.tolist()), base_shift_xyz_m=json.dumps(shift.tolist()))
    manifest.append(r)
    report.append(dict(tree=tid, base_shift_xyz_m=shift.tolist(), previous_height_m=cleaned[tid]['preliminary_height_m'],
                       supported_height_m=float(p[top, 2] - t[2]), axis_lean_deg=lean, decision=decision))
    print(tid, 'shift', np.round(shift, 3), 'supported height', round(float(p[top, 2] - t[2]), 3), 'lean', round(lean, 1), flush=True)

manifest_name = tag + '_manifest.csv'
review_name = tag + '_human_review.csv'
write_rows(MP / 'environment' / manifest_name, manifest, fields + extra)
reviews = rows(MP / 'results/CROWN_VOLUME_TOP20_20261023_164430_human_review.csv')
review = []
for m in manifest:
    rv = dict(next(x for x in reviews if x['stable_tree_id'] == m['stable_tree_id']))
    rv.update(dataset_version='Cleaned trunk, corrected references (user decisions 23 Oct 2026)', review_sha256=m['review_sha256'],
              base_ground_notes=m['reference_decision'], human_decision='PENDING', complete_tree_approved='PENDING', measurement_release='PENDING')
    review.append(rv)
write_rows(MP / 'results' / review_name, review, list(reviews[0]))
dump(batch / 'reference_changes.json', report)
dump(batch / 'batch_config.json', dict(batch=str(batch), project_root=str(ROOT), manifest_name=manifest_name, review_name=review_name,
     trees=TREES, axis_relative=(batch / 'axis').relative_to(ROOT).as_posix(),
     note='Four user-cleaned trees with corrected references. Earlier batches remain unchanged and historical for these four.'))
print('CONFIG=' + str(batch / 'batch_config.json'), flush=True)
