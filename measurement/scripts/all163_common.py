"""Shared geometry helpers for the all-163 batch. All functions are read-only on source data.

Reused methods (not changed):
  * supported_top: same rule as prepare_crown_volume_top20.py / prepare_corrected_four_tree_rerun.py.
  * refresh_axis: same low-stem axis fit as prepare_crown_volume_top20.py (circle helper extracted by AST from
    preliminary_heights.py without running that script).
  * crown_base_rule: the continuous-crown rule agreed by the user on 23 Oct 2026 (crown_base_proposal.py).
New indicator geometry (documented in methods.json): stem clusters at 1.3 m, fork flag, stem completeness,
ROI-edge distance and crown-edge contact.
"""
import ast
import csv
import hashlib
import json
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

# Agreed crown-base rule constants (CROWN_BASE_PROPOSAL_20261023_190901/method.json)
DZ, CROWN_FRACTION, FACTOR, CONTINUITY = 0.25, 0.3, 3.0, 0.7


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def points(path):
    v = PlyData.read(str(path), mmap='r')['vertex'].data
    p = np.column_stack([v[k] for k in ('x', 'y', 'z')]).astype('f8')
    assert np.isfinite(p).all()
    return p


def supported_top(p):
    ix = np.union1d(np.flatnonzero(p[:, 2] >= p[:, 2].max() - 3), np.argsort(p[:, 2])[-5000:])
    cap = p[ix]
    dd, _ = cKDTree(cap).query(cap, k=5, workers=1)
    ok = (dd[:, 4] <= .15) & (dd[:, 2] <= .08)
    assert ok.any()
    return int(ix[ok][np.argmax(cap[ok, 2])])


_src = MP / 'scripts/preliminary_heights.py'
_node = next(n for n in ast.parse(_src.read_text(encoding='utf-8-sig')).body if isinstance(n, ast.FunctionDef) and n.name == 'circle')
exec(compile(ast.Module(body=[_node], type_ignores=[]), str(_src), 'exec'), globals())
CIRCLE_SOURCE_SHA256 = sha(_src)


def refresh_axis(tid, p, ground, foot, interp, offset):
    """Low-stem axis from current points (copy of prepare_crown_volume_top20.refresh_axis). Raises on failure."""
    low = p[p[:, 2] < p[:, 2].min() + 4.5]
    gz = np.ma.filled(interp(low[:, 0] - offset[0], low[:, 1] - offset[1]), np.nan)
    near = low[np.isfinite(gz) & (low[:, 2] - gz > .3)]
    if len(near) < 60:
        near = p[(p[:, 2] > p[:, 2].min() + .15) & (p[:, 2] < p[:, 2].min() + 3.5)]
    stations = []
    rng = np.random.default_rng(6003 + int(tid.split('_')[1]) - 1)
    for z in np.arange(near[:, 2].min() + .12, near[:, 2].max(), .25):
        sl = near[np.abs(near[:, 2] - z) < .14]
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
            models.sort(key=lambda m: m['support'] * (m['coverage'] / 360) ** 1.5, reverse=True)
            stations.append(dict(z=float(z), **models[0]))
    assert len(stations) >= 4, 'fewer than 4 stem sections'
    zz = np.array([s['z'] for s in stations])
    cc = np.array([s['center'] for s in stations])
    zo = float(np.median(zz))
    a = np.c_[np.ones(len(zz)), zz - zo]
    fit = least_squares(lambda x: (a @ x.reshape(2, 2) - cc).ravel(),
                        np.linalg.lstsq(a, cc, rcond=None)[0].ravel(), loss='soft_l1', f_scale=.08)
    coeff = fit.x.reshape(2, 2)
    keep = np.linalg.norm(a @ coeff - cc, axis=1) < .15
    assert keep.sum() >= 4 and np.ptp(zz[keep]) >= .75, 'stem sections do not span 0.75 m'
    coeff = np.linalg.lstsq(a[keep], cc[keep], rcond=None)[0]
    rmse = float(np.sqrt(np.mean(np.sum((a[keep] @ coeff - cc[keep]) ** 2, axis=1))))
    assert rmse <= .1, 'axis RMSE above 0.1 m'
    axis_at_ground = coeff[0] + coeff[1] * (ground - zo)
    return dict(stem_sections=stations, stem_axis=dict(z_origin=zo, coeff=coeff.tolist()), axis_fit_rmse_m=rmse,
                axis_vertical_span_m=float(np.ptp(zz[keep])), offset_from_inherited_foot_m=float(np.linalg.norm(axis_at_ground - foot)))


def local_axis(stem_axis, t):
    """Global checkpoint axis -> local frame: xy(z_local) = o + s * z_local."""
    c0, sl = np.array(stem_axis['coeff'][0], float), np.array(stem_axis['coeff'][1], float)
    return c0 - t[:2] + sl * (t[2] - stem_axis['z_origin']), sl


def crown_base_rule(P):
    """Agreed continuous-crown rule. Returns dict with base (or None), first branch, crowned runs and profile summary."""
    top = P[:, 2].max()
    edges = np.arange(0, top + DZ, DZ)
    lay = np.clip(np.digitize(P[:, 2], edges) - 1, 0, len(edges) - 1)
    zc, raw = [], []
    for i in range(len(edges) - 1):
        s = P[lay == i]
        zc.append(edges[i] + DZ / 2)
        raw.append(np.percentile(np.hypot(*(s[:, :2] - np.median(s[:, :2], 0)).T), 95) if len(s) >= 5 else np.nan)
    zc, raw = np.array(zc), np.array(raw)
    r95 = np.array([np.nanmedian(raw[max(0, i - 1):i + 2]) if np.isfinite(raw[max(0, i - 1):i + 2]).any() else np.nan
                    for i in range(len(raw))])
    band = (zc >= 1.0) & (zc <= 0.6 * top)
    if not np.isfinite(r95[band]).any():
        return dict(base=None, first=None, runs='', trunk_r95=None, threshold=None, reason='no layers between 1 m and 60% of height')
    trunk = float(np.nanmin(r95[band]))
    thr = float(max(FACTOR * trunk, CROWN_FRACTION * np.nanmax(r95)))
    crowned = np.nan_to_num(r95) > thr
    ok = zc > 1.0
    first = next((float(zc[i] - DZ / 2) for i in range(len(zc)) if ok[i] and crowned[i]), None)
    base = next((float(zc[i] - DZ / 2) for i in range(len(zc)) if ok[i] and crowned[i] and crowned[i:].mean() >= CONTINUITY), None)
    runs, i = [], 0
    while i < len(zc):
        if ok[i] and crowned[i]:
            j = i
            while j < len(zc) and crowned[j]:
                j += 1
            if (j - i) * DZ >= 0.75:
                runs.append(f'{zc[i] - DZ / 2:.2f}-{zc[j - 1] + DZ / 2:.2f}')
            i = j
        else:
            i += 1
    return dict(base=base, first=first, runs=' | '.join(runs), trunk_r95=trunk, threshold=thr,
                reason=None if base is not None else 'no continuous crown found by the rule')


def _clusters(xy, link=0.10, min_points=8):
    if len(xy) < min_points:
        return 0
    pairs = cKDTree(xy).query_pairs(link, output_type='ndarray')
    n, labels = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                                                shape=(len(xy), len(xy))).tocsr(), directed=False)
    return int((np.bincount(labels) >= min_points).sum())


def stem_indicators(P, o, s, crown_base):
    """Indicator geometry in the local frame. o, s: local axis (or None)."""
    out = {}
    centre = (lambda z: o + s * z) if o is not None else (lambda z: np.zeros(2))
    for h in (1.0, 1.3, 1.6):
        layer = P[np.abs(P[:, 2] - h) <= 0.05]
        near = layer[np.hypot(*(layer[:, :2] - centre(h)).T) <= 1.0] if len(layer) else layer
        out[f'clusters_{h}'] = _clusters(near[:, :2]) if len(near) else 0
    out['n_stems_at_1_3m'] = out['clusters_1.3']
    out['flag_fork_near_dbh'] = bool(out['clusters_1.6'] > out['clusters_1.0'] and out['clusters_1.6'] >= 2)
    if o is not None and crown_base:
        tops = np.arange(0, crown_base, 0.5)
        filled = 0
        for z0 in tops:
            sl = P[(P[:, 2] >= z0) & (P[:, 2] < z0 + 0.5)]
            if len(sl) and (np.hypot(*(sl[:, :2] - centre(z0 + 0.25)).T) <= 0.5).any():
                filled += 1
        out['stem_completeness'] = filled / len(tops) if len(tops) else None
    else:
        out['stem_completeness'] = None
    return out
