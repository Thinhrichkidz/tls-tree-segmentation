"""Read-only crown-base proposal for the 20 test trees (no ITSMe rerun, no source changes).

For each 0.25 m height layer: r95 = 95th-percentile horizontal distance of the layer's points from the layer's median XY.
Trunk-only layers have r95 close to the trunk radius; layers with branches/foliage spread much wider.
  * r95 is smoothed with a running median of 3 layers (0.75 m).
  * trunk_r95 = smallest smoothed r95 between 1 m and 60% of tree height (the cleanest bare-trunk stretch;
    robust to leftover shrubs near the base).
  * a layer is "crowned" when smoothed r95 > max(3 x trunk_r95, 0.3 x widest smoothed layer r95)
    (scales with each tree's own crown size, so small trees are not missed).
  * first_branch_z = lowest crowned layer above 1.0 m (sensitive to single low branches and leftover shrubs).
  * continuous_crown_base_z = lowest crowned layer above 1.0 m from which >= 80% of layers up to the top are crowned.
Outputs a CSV, one figure per tree and a contact sheet. The volume preview is a convex hull of ALL points above the base,
for orientation only; the agreed rerun would apply the base to ITSMe's own crown points.
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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

OUT = MP / 'results' / f'CROWN_BASE_PROPOSAL_{datetime.now():%Y%m%d_%H%M%S}'
OUT.mkdir(exist_ok=False)
os.environ['MPLCONFIGDIR'] = str(OUT / 'matplotlib_cache')
TOP20 = MP / 'results/CROWN_VOLUME_TOP20_20261023_164430'
RERUN = MP / 'results/CORRECTED_FOUR_TREE_RERUN_20261023_190059'
DZ, CROWN_FRACTION, FACTOR, CONTINUITY = 0.25, 0.3, 3.0, 0.7

def rows(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

snap = {r['file']: r['sha256'] for r in rows(ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv')}
man = {r['stable_tree_id']: r for r in rows(MP / 'environment/CROWN_VOLUME_TOP20_20261023_164430_manifest.csv')}
new = json.loads((RERUN / 'batch_config.json').read_text())
man.update({r['stable_tree_id']: r for r in rows(MP / 'environment' / new['manifest_name'])})
old_runs = {r['stable_tree_id']: r for r in rows(TOP20 / 'all_20_tree_results.csv')}
new_runs = json.loads((RERUN / 'all_runs.json').read_text())
order = [r['stable_tree_id'] for r in rows(TOP20 / 'all_20_tree_results.csv')]

def itsme_crown(tid):
    run = Path(new_runs[tid]['run_dir']) if tid in new_runs else Path(old_runs[tid]['run_directory'])
    q = run / 'batch_quality_diagnostics.csv'
    vol = (new_runs[tid]['summary'] if tid in new_runs else old_runs[tid])['crown_volume_m3']
    z = rows(q)[0]['crown_min_z_m'] if q.exists() else 'NA'
    f = lambda v: float(v) if v not in ('NA', '', None) else None
    return f(z), f(vol), run.name

results = []
fig_all, ax_all = plt.subplots(2, 10, figsize=(30, 14))
for k, tid in enumerate(order):
    m = man[tid]
    assert snap[m['review_ply_filename']] == m['review_sha256'], f'{tid}: manifest is not the current source version'
    P = np.loadtxt(ROOT / m['local_xyz_path'], skiprows=1)
    assert len(P) == int(m['point_count'])
    top = P[:, 2].max()
    edges = np.arange(0, top + DZ, DZ)
    lay = np.clip(np.digitize(P[:, 2], edges) - 1, 0, len(edges) - 1)
    zc, r95, n = [], [], []
    for i in range(len(edges) - 1):
        s = P[lay == i]
        zc.append(edges[i] + DZ / 2); n.append(len(s))
        if len(s) < 5:
            r95.append(np.nan); continue
        r95.append(np.percentile(np.hypot(*(s[:, :2] - np.median(s[:, :2], 0)).T), 95))
    zc, raw = np.array(zc), np.array(r95)
    r95 = np.array([np.nanmedian(raw[max(0, i - 1):i + 2]) if np.isfinite(raw[max(0, i - 1):i + 2]).any() else np.nan
                    for i in range(len(raw))])
    trunk = np.nanmin(r95[(zc >= 1.0) & (zc <= 0.6 * top)])
    thr = max(FACTOR * trunk, CROWN_FRACTION * np.nanmax(r95))
    crowned = np.nan_to_num(r95) > thr
    ok = zc > 1.0
    first = next((zc[i] - DZ / 2 for i in range(len(zc)) if ok[i] and crowned[i]), None)
    cont = next((zc[i] - DZ / 2 for i in range(len(zc)) if ok[i] and crowned[i] and crowned[i:].mean() >= CONTINUITY), None)
    # Every alternative base: start of each crowned run >= 0.75 m long above 1 m (for user choice on ambiguous trees).
    starts, i = [], 0
    while i < len(zc):
        if ok[i] and crowned[i]:
            j = i
            while j < len(zc) and crowned[j]:
                j += 1
            if (j - i) * DZ >= 0.75:
                starts.append(f'{zc[i] - DZ / 2:.2f}-{zc[j - 1] + DZ / 2:.2f}')
            i = j
        else:
            i += 1
    with (OUT / f'{tid}_spread_profile.csv').open('w', newline='') as f:
        csv.writer(f).writerows([['layer_mid_z_m', 'points', 'r95_raw_m', 'r95_smoothed_m', 'crowned']] +
                                [[round(a, 3), b, c, d, e] for a, b, c, d, e in zip(zc, n, raw, r95, crowned)])
    iz, ivol, run = itsme_crown(tid)
    prev = None
    if cont is not None:
        A = P[P[:, 2] >= cont]
        prev = ConvexHull(A[::max(1, len(A) // 200000)]).volume if len(A) > 10 else None
    results.append(dict(tree=tid, height_m=round(top, 3), trunk_r95_m=round(trunk, 3), crowned_threshold_m=round(thr, 3),
                        itsme_crown_start_m=iz, first_branch_z_m=first, continuous_crown_base_m=cont,
                        crowned_runs_m=' | '.join(starts),
                        crown_length_m=None if cont is None else round(top - cont, 2),
                        crown_ratio=None if cont is None else round((top - cont) / top, 2),
                        current_envelope_m3=ivol, preview_envelope_above_base_m3=None if prev is None else round(prev, 1),
                        current_run=run, source_sha256=m['review_sha256']))
    sub = P[::max(1, len(P) // 60000)]
    fig, ax = plt.subplots(1, 3, figsize=(16, 8), gridspec_kw=dict(width_ratios=[1, 1, .8]))
    for j, (c, lab) in enumerate([(0, 'X'), (1, 'Y')]):
        ax[j].scatter(sub[:, c], sub[:, 2], s=.1, c='gray', alpha=.5)
        for z, col, ls, name in [(iz, 'red', '--', 'ITSMe crown start (current)'), (first, 'orange', ':', 'first branch layer'),
                                 (cont, 'blue', '-', 'PROPOSED continuous crown base')]:
            if z is not None:
                ax[j].axhline(z, color=col, ls=ls, lw=2, label=f'{name}: {z:.2f} m')
        ax[j].set_aspect('equal'); ax[j].set_xlabel(f'{lab} local (m)'); ax[j].set_ylabel('height above stem-foot ground (m)')
        ax[j].set_title(f'{tid} {lab}-Z side view')
    ax[0].legend(fontsize=8, loc='lower right')
    ax[2].plot(r95, zc, 'k.-', ms=3); ax[2].axvline(thr, color='g', ls='--', label=f'crowned if wider than {thr:.2f} m')
    if cont is not None: ax[2].axhline(cont, color='blue')
    ax[2].set_xlabel('layer spread r95 (m)'); ax[2].set_ylabel('height (m)'); ax[2].legend(fontsize=8); ax[2].set_title('spread profile')
    fig.tight_layout(); fig.savefig(OUT / f'{tid}_crown_base.png', dpi=80); plt.close(fig)
    a = ax_all.ravel()[k]
    a.scatter(sub[:, 0], sub[:, 2], s=.05, c='gray', alpha=.4)
    if iz is not None: a.axhline(iz, color='red', ls='--', lw=1.5)
    if cont is not None: a.axhline(cont, color='blue', lw=1.5)
    a.set_title(f'{tid}\nred {iz if iz is None else round(iz, 2)} / blue {cont if cont is None else round(cont, 2)} m', fontsize=10)
    a.set_aspect('equal'); a.tick_params(labelsize=7)
    print(tid, 'trunk', round(trunk, 2), 'thr', round(thr, 2), 'itsme', iz, 'first', first, 'cont', cont, 'vol', ivol, '->', prev, flush=True)
fig_all.suptitle('X-Z side views. Red dashed = current ITSMe crown start; blue = proposed continuous crown base', fontsize=16)
fig_all.tight_layout(); fig_all.savefig(OUT / 'ALL_20_crown_base_contact_sheet.png', dpi=70)
with (OUT / 'crown_base_proposal.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
(OUT / 'method.json').write_text(json.dumps(dict(layer_m=DZ, crown_fraction=CROWN_FRACTION, trunk_factor=FACTOR, continuity=CONTINUITY,
    definition=__doc__), indent=1), encoding='utf-8')
print(OUT)
