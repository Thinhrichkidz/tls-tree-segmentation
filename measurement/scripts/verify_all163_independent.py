"""Independent recalculation of key measurements for sample trees (no ITSMe, no pipeline geometry code).

For each sample tree it reads the ORIGINAL global PLY (hash-checked) and recomputes:
  * ground: terrain-mesh Z interpolated at the foot XY used by the pipeline (checks the stored ground Z);
  * height: highest point minus that ground Z;
  * DBH: own circle fit (Kasa seed + robust geometric least squares) on a 6 cm slice at 1.3 m along the pipeline's stem
    axis, with its own bark-radius crop and 20-sector arc coverage (the axis is an input, the fit is independent);
  * crown: 2D convex-hull area and 3D convex-hull volume of ALL points above the crown base. ITSMe uses a concave
    area and only its classified crown points, so these are upper bounds: expect independent >= workbook.
Usage: python -I verify_all163_independent.py --out <all-163 output folder> [--trees ...]
Writes <out>/logs/independent_verification.csv and .json.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'verification_output' / '_deps'))
import numpy as np
from plyfile import PlyData
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from matplotlib.tri import Triangulation, LinearTriInterpolator
import hashlib

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ['tree_146', 'tree_151', 'tree_108', 'tree_105', 'tree_084', 'tree_103', 'tree_079', 'tree_026', 'tree_002', 'tree_063',
          'tree_093', 'tree_125', 'tree_087', 'tree_118', 'tree_001', 'tree_056', 'tree_080', 'tree_049', 'tree_099', 'tree_067',
          'tree_033', 'tree_030', 'tree_112', 'tree_102']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 23), b''):
            h.update(b)
    return h.hexdigest()


def rot(v):
    v = v / np.linalg.norm(v); z = np.array([0, 0, 1.]); k = np.cross(v, z); s = np.linalg.norm(k); c = v @ z
    if s < 1e-12:
        return np.eye(3)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)


def circle_fit(x, y):
    A = np.c_[x, y, np.ones_like(x)]
    p = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    c0 = [p[0] / 2, p[1] / 2, math.sqrt(max(p[2] + p[0] ** 2 / 4 + p[1] ** 2 / 4, 1e-12))]
    f = least_squares(lambda q: np.hypot(x - q[0], y - q[1]) - q[2], c0, loss='huber', f_scale=0.01)
    res = np.hypot(x - f.x[0], y - f.x[1]) - f.x[2]
    ang = np.arctan2(y - f.x[1], x - f.x[0])
    arc = len(np.unique(np.floor((ang + np.pi) / (2 * np.pi) * 20))) / 20
    return 2 * f.x[2], float(np.sqrt(np.mean(res ** 2))), arc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--trees', default='')
    a = ap.parse_args()
    out = Path(a.out)
    recs = {r['tree']: r for r in json.loads((out / 'logs/records.json').read_text())}
    mesh = np.load(ROOT / 'verification_output/terrain_arrays.npz')
    mv, mf = mesh['vertices'], mesh['faces']
    off = mv[:, :2].min(0)
    interp = LinearTriInterpolator(Triangulation(mv[:, 0] - off[0], mv[:, 1] - off[1], mf), mv[:, 2])
    snap = {r['file']: r['sha256'] for r in csv.DictReader(open(ROOT / 'session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv', encoding='utf-8-sig'))}
    rows = []
    for tid in (a.trees.split(',') if a.trees else SAMPLE):
        prep = json.loads((out / 'per_tree' / tid / 'prep.json').read_text())
        r = recs[tid]
        src = next((ROOT / 'CloudCompare_review_v2').glob(f'{tid}_*.ply'))
        assert sha(src) == snap[src.name] == prep['review_sha256']
        v = PlyData.read(str(src))['vertex']
        P = np.column_stack([np.asarray(v[k], float) for k in 'xyz'])
        t = np.array(prep['translation'])
        g_mesh = float(interp(t[0] - off[0], t[1] - off[1]))
        # Height foot moved under the trunk (height_refine_all163.py): own mesh interpolation at the reported foot XY
        hf = r.get('height_foot') or {}
        g_height, g_height_pipeline = g_mesh, t[2]
        if hf.get('source'):
            foot = json.loads((out / 'per_tree' / tid / 'height_refine.json').read_text())['foot_candidates'][hf['source']]
            g_height = float(interp(foot['xy'][0] - off[0], foot['xy'][1] - off[1]))
            g_height_pipeline = t[2] + hf['dz_m']
        row = dict(tree=tid, points=len(P), ground_z_pipeline=t[2], ground_z_mesh_at_foot=g_mesh, ground_diff_m=g_mesh - t[2],
                   height_foot_source=hf.get('source') or 'translation foot', height_ground_diff_m=g_height - g_height_pipeline,
                   height_independent=P[:, 2].max() - g_height, height_workbook=r['height']['v'], height_status=r['height']['s'])
        row['height_diff_m'] = row['height_independent'] - r['height']['v'] if r['height']['v'] is not None else None
        L = P - t
        if prep.get('axis_o') is not None:
            o = np.array(prep['axis_o'] + [0.]); s = np.array(prep['axis_s'] + [1.])
            Q = (L - o) @ rot(s).T
            band = Q[(Q[:, 2] >= 1.0) & (Q[:, 2] <= 1.6)]
            rho = np.hypot(band[:, 0], band[:, 1]); rho = rho[rho <= 0.8]
            hist = np.convolve(np.bincount(np.minimum((rho / 0.01).astype(int), 79), minlength=80), np.ones(3) / 3, 'same')
            crop = max(0.15, (np.argmax(hist) + 0.5) * 0.01 + 0.10)
            sl = Q[(np.abs(Q[:, 2] - 1.3) <= 0.03) & (np.hypot(Q[:, 0], Q[:, 1]) <= crop)]
            if len(sl) >= 8:
                d, rmse, arc = circle_fit(sl[:, 0], sl[:, 1])
                row.update(dbh_independent_cm=100 * d, dbh_ind_rmse_cm=100 * rmse, dbh_ind_arc=arc, dbh_ind_points=len(sl),
                           dbh_ind_passes=bool(0.03 < d < 2 and arc >= 0.6 and rmse <= min(0.04, max(0.01, 0.1 * d))))
        row.update(dbh_workbook=r['dbh']['v'], dbh_status=r['dbh']['s'], dbh_unaccepted=r['dbh_unaccepted_cm'])
        if row.get('dbh_independent_cm') is not None and r['dbh']['v'] is not None:
            row['dbh_diff_cm'] = row['dbh_independent_cm'] - r['dbh']['v']
        base = prep.get('crown_base_m')
        if base is not None:
            C = L[L[:, 2] >= base]
            if len(C) > 10:
                row.update(crown_area_convex_independent=ConvexHull(C[:, :2]).volume, crown_volume_convex_independent=ConvexHull(C).volume)
        row.update(crown_area_workbook=r['crown_area']['v'], crown_volume_workbook=r['crown_volume']['v'], crown_status=r['crown_volume']['s'])
        if row.get('crown_area_convex_independent') and r['crown_area']['v']:
            row['area_ratio_workbook_to_convex'] = r['crown_area']['v'] / row['crown_area_convex_independent']
            row['volume_ratio_workbook_to_convex'] = (r['crown_volume']['v'] or float('nan')) / row['crown_volume_convex_independent']
        rows.append(row)
        print(tid, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in row.items() if k not in ('tree',)}, flush=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with (out / 'logs/independent_verification.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    hd = [abs(r['height_diff_m']) for r in rows if r.get('height_diff_m') is not None]
    dd = [abs(r['dbh_diff_cm']) for r in rows if r.get('dbh_diff_cm') is not None]
    summary = dict(trees=len(rows), max_abs_height_diff_m=max(hd), max_abs_ground_diff_m=max(abs(r['ground_diff_m']) for r in rows), max_abs_height_ground_diff_m=max(abs(r['height_ground_diff_m']) for r in rows), moved_foot_trees=[r['tree'] for r in rows if r['height_foot_source'] != 'translation foot'],
                   dbh_compared=len(dd), median_abs_dbh_diff_cm=float(np.median(dd)) if dd else None, max_abs_dbh_diff_cm=max(dd) if dd else None,
                   area_ratio_range=[min(r['area_ratio_workbook_to_convex'] for r in rows if 'area_ratio_workbook_to_convex' in r),
                                     max(r['area_ratio_workbook_to_convex'] for r in rows if 'area_ratio_workbook_to_convex' in r)],
                   volume_ratio_range=[min(r['volume_ratio_workbook_to_convex'] for r in rows if 'volume_ratio_workbook_to_convex' in r),
                                       max(r['volume_ratio_workbook_to_convex'] for r in rows if 'volume_ratio_workbook_to_convex' in r)])
    (out / 'logs/independent_verification.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1, default=float), encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
