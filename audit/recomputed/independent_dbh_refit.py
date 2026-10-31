"""Auditor's own DBH re-fit (independent of ITSMe and of the project's verify script).

Usage: python -I independent_dbh_refit.py <FINAL_DIR> <OUT_CSV>
For every tree with a released DBH: load per_tree/<id>/<id>_local_xyz.txt, shift by the stored axis origin,
rotate the stored axis to vertical (Rodrigues), keep points within the stored crop radius, take the 6 cm slice
centred at 1.3 m, drop points whose nearest neighbour is > 5 cm away, and fit a circle by geometric least
squares (Kasa start). Also recomputes height = max(z) - 0 (local frame has ground at the foot at z = 0).
Compares with tree_attributes.csv. Read-only on inputs.
"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

final, out = Path(sys.argv[1]), Path(sys.argv[2])
ta = pd.read_csv(final / 'results/tree_attributes.csv').set_index('tree_id')
ta = ta[ta.dbh_cm.notna()]  # shortcut: only the 80 trees with a released DBH; drop this line to check all 163 heights

def rot_to_z(v):
    v = v / np.linalg.norm(v); z = np.array([0., 0., 1.]); c = v @ z; k = np.cross(v, z); s = np.linalg.norm(k)
    if s < 1e-12: return np.eye(3)
    k /= s; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K

def fit_circle(xy):
    A = np.c_[xy, np.ones(len(xy))]; b = (xy ** 2).sum(1)
    p = np.linalg.lstsq(A, b, rcond=None)[0]; c0 = p[:2] / 2; r0 = np.sqrt(p[2] + c0 @ c0)
    f = least_squares(lambda q: np.hypot(*(xy - q[:2]).T) - q[2], np.r_[c0, r0])
    res = np.hypot(*(xy - f.x[:2]).T) - f.x[2]
    return 2 * f.x[2], float(np.sqrt(np.mean(res ** 2)))

rows = []
t0 = time.time()
for tid in ta.index:
    pdir = final / 'per_tree' / tid
    prep = json.loads((pdir / 'prep.json').read_text()); res = json.loads((pdir / 'result.json').read_text())
    p = pd.read_csv(pdir / f'{tid}_local_xyz.txt', sep=' ', usecols=[0, 1, 2]).iloc[:, :3].to_numpy(float)
    row = dict(tree=tid, n=len(p), height_audit=p[:, 2].max(), height_report=ta.loc[tid, 'height_m'],
               dbh_report=ta.loc[tid, 'dbh_cm'], dbh_status=ta.loc[tid, 'dbh_status'])
    if prep.get('axis_o') is not None and res.get('crop_radius_m'):
        o = np.r_[prep['axis_o'], 0.]; v = np.r_[prep['axis_s'], 1.]
        q = (p - o) @ rot_to_z(v).T
        q = q[np.hypot(q[:, 0], q[:, 1]) <= res['crop_radius_m']]
        sl = q[np.abs(q[:, 2] - 1.3) <= 0.03][:, :2]
        if len(sl) > 3:
            d, _ = cKDTree(sl).query(sl, k=2); sl = sl[d[:, 1] <= 0.05]
        row['slice_points'] = len(sl)
        if len(sl) >= 5:
            row['dbh_audit_cm'], row['rmse_audit_cm'] = [100 * x for x in fit_circle(sl)]
    rows.append(row)
df = pd.DataFrame(rows)
df['height_diff_m'] = df.height_audit - df.height_report
df['dbh_diff_cm'] = df.get('dbh_audit_cm') - df.dbh_report
df.to_csv(out, index=False)
d = df.dropna(subset=['dbh_report', 'dbh_audit_cm'])
print('trees', len(df), 'seconds', round(time.time() - t0, 1))
print('height |diff| max (m):', df.height_diff_m.abs().max())
print('DBH compared:', len(d), 'median |diff| cm', d.dbh_diff_cm.abs().median(), 'max |diff|', d.dbh_diff_cm.abs().max())
for s in ['VALID', 'REVIEW']:
    e = d[d.dbh_status == s]
    print(s, len(e), 'median |diff|', round(e.dbh_diff_cm.abs().median(), 3), 'n |diff|>2 cm:', int((e.dbh_diff_cm.abs() > 2).sum()))
print(d.loc[d.dbh_diff_cm.abs() > 2, ['tree', 'dbh_status', 'dbh_report', 'dbh_audit_cm', 'slice_points']].round(2).to_string())
