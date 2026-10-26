"""Side views for the trees whose crown base the user must choose (read-only; no measurement is changed).

Group 1: rule found no continuous crown (crown base N/A). Group 2: automatic base excluded lower foliage layers (REVIEW).
Candidate bases = start of every crowned run (>= 0.75 m of layers wider than the crown threshold) above 1 m, labelled A, B, C...
in height order. Writes one figure per tree, contact sheets and candidates.csv into a new folder.
Usage: python -I crown_base_review_all163.py --out <ITSMe_all163_output folder>
"""
import argparse
import csv
import json
import os
import string
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import all163_common as C
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
batch = Path(ap.parse_args().out)
dest = C.MP / 'results' / f'CROWN_BASE_REVIEW_ALL163_{datetime.now():%Y%m%d_%H%M%S}'
dest.mkdir(exist_ok=False)
os.environ['MPLCONFIGDIR'] = str(dest / 'matplotlib_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

recs = {r['tree']: r for r in json.loads((batch / 'logs/records.json').read_text())}
groups = [('no_crown_base', sorted(t for t, r in recs.items() if r['crown_base']['s'] == 'N/A')),
          ('excluded_lower_foliage', sorted(t for t, r in recs.items() if r['crown_base']['s'] == 'REVIEW'))]
COLORS = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd', '#8c564b', '#e377c2']
rows = []
for gname, trees in groups:
    sheets = [trees[i:i + 12] for i in range(0, len(trees), 12)]
    for si, chunk in enumerate(sheets, 1):
        fig_s, ax_s = plt.subplots(2, 12, figsize=(48, 18), squeeze=False)
        for k, tid in enumerate(chunk):
            prep = json.loads((batch / 'per_tree' / tid / 'prep.json').read_text())
            P = np.loadtxt(prep['local_xyz_path'], skiprows=1)
            runs = [r for r in (prep.get('rule_crowned_runs_m') or '').split(' | ') if r]
            cands = sorted({float(r.split('-')[0]) for r in runs})
            labels = dict(zip(cands, string.ascii_uppercase))
            top = P[:, 2].max()
            auto = prep.get('crown_base_m')
            rows.append(dict(group=gname, tree=tid, height_m=round(top, 2), automatic_base_m=auto,
                             crowned_layers_m=' | '.join(runs) or 'none',
                             options=' ; '.join(f'{labels[c]} = {c:.2f} m' for c in cands) or 'no crowned layer above 1 m',
                             itsme_auto_crown_start_m=recs[tid]['auto'][2], sheet=f'{gname}_{si}.png'))
            sub = P[np.random.default_rng(1).permutation(len(P))[:60000]] if len(P) > 60000 else P
            fig, ax = plt.subplots(1, 3, figsize=(16, 8), gridspec_kw=dict(width_ratios=[1, 1, .8]))
            for j, (c, lab) in enumerate([(0, 'X'), (1, 'Y')]):
                ax[j].scatter(sub[:, c], sub[:, 2], s=.2, c='gray', alpha=.5)
                for i, z in enumerate(cands):
                    ax[j].axhline(z, color=COLORS[i % 7], lw=2, label=f'{labels[z]}: {z:.2f} m' + (' (automatic)' if auto is not None and abs(z - auto) < 1e-6 else ''))
                ax[j].set_aspect('equal'); ax[j].set_xlabel(f'{lab} local (m)'); ax[j].set_ylabel('height above stem-foot ground (m)')
                ax[j].set_title(f'{tid} {lab}-Z')
            if cands:
                ax[0].legend(fontsize=9, loc='lower right')
            # spread profile, same definition as the rule
            edges = np.arange(0, top + C.DZ, C.DZ)
            lay = np.clip(np.digitize(P[:, 2], edges) - 1, 0, len(edges) - 1)
            zc = edges[:-1] + C.DZ / 2
            r95 = [np.percentile(np.hypot(*(P[lay == i][:, :2] - np.median(P[lay == i][:, :2], 0)).T), 95) if (lay == i).sum() >= 5 else np.nan for i in range(len(zc))]
            ax[2].plot(r95, zc, 'k.-', ms=3)
            if prep.get('rule_threshold_m'):
                ax[2].axvline(prep['rule_threshold_m'], color='g', ls='--', label=f'crown if wider than {prep["rule_threshold_m"]:.2f} m')
                ax[2].legend(fontsize=8)
            for i, z in enumerate(cands):
                ax[2].axhline(z, color=COLORS[i % 7], lw=1)
            ax[2].set_xlabel('layer spread r95 (m)'); ax[2].set_title('spread profile')
            fig.suptitle(f'{tid}: {"no continuous crown found" if gname == "no_crown_base" else f"automatic base {auto:.2f} m excluded lower foliage"}')
            fig.tight_layout(); fig.savefig(dest / f'{tid}_crown_base_options.png', dpi=80); plt.close(fig)
            for row_i, c in enumerate((0, 1)):
                a = ax_s[row_i][k]
                a.scatter(sub[:, c], sub[:, 2], s=.05, c='gray', alpha=.4)
                for i, z in enumerate(cands):
                    a.axhline(z, color=COLORS[i % 7], lw=1.5)
                    a.text(a.get_xlim()[1] if False else sub[:, c].max(), z, f' {labels[z]}', color=COLORS[i % 7], fontsize=12, va='bottom', ha='right', weight='bold')
                a.set_aspect('equal'); a.tick_params(labelsize=7)
                a.set_title(f'{tid} {"XY"[c]}-Z\n' + ', '.join(f'{labels[z]} {z:.2f}' for z in cands), fontsize=11)
        for k in range(len(chunk), 12):
            ax_s[0][k].axis('off'); ax_s[1][k].axis('off')
        fig_s.suptitle(f'{gname.replace("_", " ")} — sheet {si}/{len(sheets)}. Coloured lines = candidate crown bases (start of each wide foliage layer)', fontsize=18)
        fig_s.tight_layout(); fig_s.savefig(dest / f'{gname}_{si}.png', dpi=55); plt.close(fig_s)
with (dest / 'candidates.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(dest)
for r in rows:
    print(r['group'][:8], r['tree'], r['height_m'], 'auto', r['automatic_base_m'], '|', r['options'])
