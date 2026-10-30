"""Reference-style TLS figures for all 163 trees, comparison grids and report charts (read-only on all inputs).

Style reproduces measurement_pipeline/qc_figures/*_selected_3D_sideviews.png (prepare_selected_inputs.py) and
*_initial_screen.png (height_qc_figures.py): viridis by height, point size 0.25, 70,000-point display sample
(seed 6003), terrain-mesh vertices within +/-2.5 m of the foot in sienna, red stem-centre marker, 15 x 6 in panels.
Deliberate differences: 300 dpi; equal physical box aspect in 3D; no overlapping labels; titles and statuses come from
the final audited workbook; the red stem-centre marker is drawn only where a fitted stem axis exists; colour bar added.
Measurements are never recomputed here.
v3 (28 Oct 2026): subtitle adds the gap-aware crown volume (1 m slab hulls) and, where the DBH column is N/A, the ESTIMATED DBH;
extra distribution chart for the slab volume. Works with the v6 FINAL workbook.
Usage: python -I render_all163_figures.py --final <ITSMe_all163_output_v6_FINAL folder> [--out <folder>] [--workers N] [--trees ...]
"""
import argparse
import csv
import hashlib
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'verification_output' / '_deps'))
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / 'measurement_pipeline'
SAMPLE_N, SEED, NEAR_M = 70000, 6003, 2.5
STYLE_VERSION = 'all163-figures-v3'
NA = 'N/A'
STAT_FILL = {'VALID': '#D9EAD3', 'ESTIMATED': '#FFF2CC', 'N/A': '#F4CCCC', 'REVIEW': '#FCE5CD', 'UNKNOWN': '#E7E6E6'}
SERIES = {'VALID': ('#2a78d6', 'o'), 'REVIEW': ('#eb6834', '^')}   # dataviz reference palette slots 1-2, fixed order


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 23), b''):
            h.update(b)
    return h.hexdigest()


def workbook_rows(final):
    from xlsx_writer import read_xlsx_rows
    rows = read_xlsx_rows(final / 'ITSMe_all163_results.xlsx')['All Tree Results']
    head = rows[0]
    return {r[0]: dict(zip(head, r)) for r in rows[1:]}


def stem_sections(tid, prep):
    """Fitted stem-section centres (global) from the axis file the batch used; [] if none."""
    src = prep.get('axis_source') or ''
    if src.startswith('CORRECTED_FOUR_TREE_RERUN'):
        p = MP / f'results/CORRECTED_FOUR_TREE_RERUN_20261023_190059/axis/{tid}_height.json'
    elif src.startswith('CROWN_VOLUME_TOP20'):
        p = MP / f'results/CROWN_VOLUME_TOP20_20261023_164430/axis/{tid}_height.json'
    elif src.startswith('saved height checkpoint'):
        p = MP / f'checkpoints/{tid}_height.json'
    else:
        return []
    return json.loads(p.read_text()).get('stem_sections') or []


def fmt(v, unit, nd):
    return f'{v:.{nd}f} {unit}' if isinstance(v, float) else NA


def status_text(w, value_col, status_col, label, unit, nd):
    s = w[status_col]
    return f'{label} {fmt(w[value_col], unit, nd) if s in ("VALID", "REVIEW") else NA} [{s}]'


def dbh_text(w):
    t = status_text(w, 'DBH (cm)', 'DBH status', 'DBH', 'cm', 2)
    est = w.get('Estimated DBH (cm)')
    return t + (f' (ESTIMATED {est:.1f} cm)' if w['DBH status'] == 'N/A' and isinstance(est, float) else '')


def subtitle_for(w):
    return ' | '.join([dbh_text(w),
                       status_text(w, 'Crown projected area (m2)', 'Crown area status', 'crown area', 'm²', 2),
                       status_text(w, 'Crown envelope volume (m3)', 'Crown volume status', 'crown envelope', 'm³', 1),
                       status_text(w, 'Crown volume, 1 m slab hulls (m3)', 'Crown slab volume status', 'crown slab volume', 'm³', 1)])


def title_for(tid, w):
    s = w['Height status']
    if s in ('VALID', 'REVIEW') and isinstance(w['Height ITSMe (m)'], float):
        h = f"{w['Height ITSMe (m)']:.3f} m {'preliminary' if s == 'VALID' else 'REVIEW'}"
    elif s == 'ESTIMATED':
        h = f"{w['Height ITSMe (m)']:.3f} m ESTIMATED"
    else:
        h = 'Height: N/A'
    return f"{tid}: {h}; Human Approval: {w['Human approval']}"


_mesh = None


def _load_mesh():
    global _mesh
    if _mesh is None:
        _mesh = np.load(ROOT / 'verification_output/terrain_arrays.npz')['vertices']
    return _mesh


def load_tree(tid, prep, final):
    src = next((ROOT / 'CloudCompare_review_v2').glob(f'{tid}_*.ply'))
    assert sha(src) == prep['review_sha256'], f'{tid}: source changed since the numerical run'
    from plyfile import PlyData
    v = PlyData.read(str(src))['vertex']
    t = np.array(prep['translation'])
    P = np.column_stack([np.asarray(v[k], float) for k in 'xyz']) - t
    sp = P if len(P) < SAMPLE_N else P[np.random.default_rng(SEED).choice(len(P), SAMPLE_N, False)]
    m = _load_mesh() - t
    ground = m[np.all(np.abs(m[:, :2]) < NEAR_M, axis=1)]
    return src, P, sp, ground, t


def render_tree(job):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import colors
    tid, final, out_png, w = job['tree'], Path(job['final']), Path(job['png']), job['w']
    t0 = time.time()
    prep = json.loads((final / 'per_tree' / tid / 'prep.json').read_text())
    src, P, sp, ground, t = load_tree(tid, prep, final)
    top = float(P[:, 2].max())
    norm = colors.Normalize(vmin=0, vmax=max(top, 1e-6))   # colour = height above foot ground, 0 to tree top
    has_axis = prep.get('axis_o') is not None
    foot = np.array(prep['axis_o']) if has_axis else None
    plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#555555', 'grid.color': '#dddddd'})
    fig = plt.figure(figsize=(16, 6.4))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.15, 1, 1, 0.04], wspace=0.28, left=0.02, right=0.95, top=0.86, bottom=0.14)
    ax = fig.add_subplot(gs[0], projection='3d')
    ax.scatter(sp[:, 0], sp[:, 1], sp[:, 2], s=.25, c=sp[:, 2], cmap='viridis', norm=norm, alpha=.7, rasterized=True)   # as reference
    ax.scatter(ground[:, 0], ground[:, 1], ground[:, 2], s=.3, c='sienna', alpha=.4, rasterized=True, linewidths=0)
    if has_axis:
        ax.scatter([foot[0]], [foot[1]], [0], c='red', s=30, depthshade=False)
    allx = np.r_[sp[:, 0], ground[:, 0]]; ally = np.r_[sp[:, 1], ground[:, 1]]; allz = np.r_[sp[:, 2], ground[:, 2]]
    rng = [np.ptp(allx), np.ptp(ally), np.ptp(allz)]
    ax.set_box_aspect([max(r, 0.5) for r in rng], zoom=1.0)   # equal metre scaling on all three axes; zoom only enlarges the panel
    ax.set_xlabel('X offset (m)', labelpad=6); ax.set_ylabel('Y offset (m)', labelpad=6); ax.set_zlabel('Z above foot ground (m)', labelpad=4)
    ax.tick_params(labelsize=8)
    ylim = (min(allz.min(), 0) - 0.5, top + 0.5)
    for j, k in enumerate((0, 1)):
        a = fig.add_subplot(gs[j + 1])
        a.scatter(sp[:, k], sp[:, 2], s=.25, c=sp[:, 2], cmap='viridis', norm=norm, rasterized=True)   # as reference
        a.scatter(ground[:, k], ground[:, 2], s=.4, c='sienna', alpha=.4, rasterized=True, linewidths=0)
        a.axhline(0, color='red', lw=.6)
        if has_axis:
            a.scatter([foot[k]], [0], c='red', s=30, zorder=5)
        a.set_ylim(*ylim)
        a.set_aspect('equal', adjustable='datalim')
        a.set_xlabel(('X' if k == 0 else 'Y') + ' offset (m)'); a.set_ylabel('Z above foot ground (m)')
        a.set_title(('XZ' if k == 0 else 'YZ') + ' elevation', fontsize=10)
        a.grid(True, lw=.4)
    cax = fig.add_subplot(gs[3])
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap='viridis'), cax=cax, label='Z above foot ground (m)')
    fig.suptitle(title_for(tid, w), fontsize=14, y=0.975)
    sub = subtitle_for(w)
    note = (f"display sample {len(sp):,} of {len(P):,} points (seed {SEED}); brown = terrain-mesh vertices within ±{NEAR_M} m of the foot; "
            + ('red = fitted stem centre at ground' if has_axis else 'no fitted stem centre (no stem axis)'))
    fig.text(0.5, 0.905, sub, ha='center', fontsize=10)
    fig.text(0.5, 0.012, note, ha='center', fontsize=8, color='#52514e')
    out_png.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_png.with_suffix('.tmp.png')
    fig.savefig(tmp, dpi=300)
    plt.close(fig)
    os.replace(tmp, out_png)
    meta = dict(tree=tid, png=str(out_png), png_sha256=sha(out_png), source_file=src.name, source_sha256=prep['review_sha256'],
                points=len(P), display_points=len(sp), ground_vertices=len(ground), stem_marker=has_axis, title=title_for(tid, w),
                subtitle=sub, style=STYLE_VERSION, seconds=time.time() - t0)
    out_png.with_suffix('.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    return meta


def panel_label(kind, w):
    """Extra panel-title text for comparison grids (module level so worker processes can use it)."""
    if kind == 'dbh':
        return f" | DBH {w['DBH (cm)']:.1f} cm"
    if kind == 'area':
        return f" | crown {w['Crown projected area (m2)']:.1f} m²"
    if kind == 'quality':
        return ' | ' + '/'.join('NA' if w[s] == 'N/A' else w[s][0] for s in ('Height status', 'DBH status', 'Crown area status', 'Crown volume status'))
    return ''


def grid_figure(trees, label, suptitle, rows_w, final, out_png, kind=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(4, 4, figsize=(16, 20))
    for n, tid in enumerate(trees[:8]):
        w = rows_w[tid]
        prep = json.loads((final / 'per_tree' / tid / 'prep.json').read_text())
        src, P, sp, ground, t = load_tree(tid, prep, final)
        sp = P if len(P) <= 65000 else P[np.random.default_rng(SEED).choice(len(P), 65000, False)]   # as height_qc_figures.py
        sec = stem_sections(tid, prep)
        h = w['Height ITSMe (m)']
        for j, k in enumerate((0, 1)):
            ax = axs[n // 2, (n % 2) * 2 + j]
            ax.scatter(sp[:, k], sp[:, 2], s=.35, c=sp[:, 2], cmap='viridis', rasterized=True)
            if sec:
                ax.scatter(np.array([s['center'][k] for s in sec]) - t[k], np.array([s['z'] for s in sec]) - t[2], c='red', s=8)
            if prep.get('axis_o') is not None:
                ax.scatter([prep['axis_o'][k]], [0], c='red', marker='+', s=35)
            ax.axhline(0, color='red', lw=.7)
            ax.set_aspect('equal', adjustable='datalim')
            ax.set_xlabel('X offset (m)' if k == 0 else 'Y offset (m)'); ax.set_ylabel('Z above foot ground (m)')
            ax.set_title(f"{tid} {fmt(h, 'm', 3) if w['Height status'] in ('VALID', 'REVIEW') else 'Height N/A'} {'XZ' if k == 0 else 'YZ'}{panel_label(kind, w)}", fontsize=10)
    for n in range(len(trees[:8]), 8):
        for j in (0, 1):
            axs[n // 2, (n % 2) * 2 + j].axis('off')
    import textwrap
    lines = [suptitle] + (['Status letters after each title: height / DBH / crown area / crown volume (V = VALID, R = REVIEW, NA = N/A)']
                          if kind == 'quality' else [])
    text = '\n'.join(textwrap.fill(line, 115) for line in lines)
    fig.suptitle(text, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, .975 - 0.009 * text.count('\n')])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    return dict(figure=str(out_png), label=label, trees=trees[:8])


def grid_job(args):
    return grid_figure(*args)


def report_figures(rows_w, outdir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    outdir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#52514e',
                         'axes.labelcolor': '#0b0b0b', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.grid': True,
                         'grid.color': '#e6e6e3', 'grid.linewidth': .6, 'axes.axisbelow': True, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb'})
    W = list(rows_w.values())
    made, stats = [], {}

    def vals(col, scol, status):
        return [w[col] for w in W if w[scol] == status and isinstance(w[col], float)]

    def save(fig, name):
        for ext in ('png', 'pdf'):
            fig.savefig(outdir / f'{name}.{ext}', dpi=300, bbox_inches='tight')
        plt.close(fig)
        made.append(name)

    for col, scol, name, xlabel in [('Height ITSMe (m)', 'Height status', 'tree_height_distribution', 'Tree height above foot ground (m)'),
                                    ('DBH (cm)', 'DBH status', 'dbh_distribution', 'DBH, 1.3 m along stem (cm)'),
                                    ('Crown projected area (m2)', 'Crown area status', 'crown_area_distribution', 'Crown projected area (m²)'),
                                    ('Crown envelope volume (m3)', 'Crown volume status', 'crown_volume_distribution', 'Crown envelope volume (m³)'),
                                    ('Crown volume, 1 m slab hulls (m3)', 'Crown slab volume status', 'crown_slab_volume_distribution', 'Crown slab volume (sum of 1 m slab hulls, m³)')]:
        v, r = vals(col, scol, 'VALID'), vals(col, scol, 'REVIEW')
        na = sum(w[scol] == 'N/A' for w in W)
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        bins = np.histogram_bin_edges(v + r, bins=16)
        ax.hist([v, r], bins=bins, stacked=True, color=[SERIES['VALID'][0], SERIES['REVIEW'][0]], edgecolor='#fcfcfb', linewidth=2,
                label=[f'VALID (n = {len(v)})', f'REVIEW (n = {len(r)})'])
        ax.set_xlabel(xlabel); ax.set_ylabel('Number of trees')
        ax.set_title(f'{xlabel.split(",")[0].split(" (")[0]}: 163 trees ({na} N/A not shown)', loc='left', fontsize=12)
        ax.legend(frameon=False)
        save(fig, name)
        stats[name] = dict(valid_n=len(v), review_n=len(r), na_n=na, valid_median=float(np.median(v)) if v else None)
    pairs = [('DBH (cm)', 'DBH status', 'Height ITSMe (m)', 'Height status', 'dbh_vs_height', 'DBH (cm)', 'Tree height (m)'),
             ('DBH (cm)', 'DBH status', 'Crown projected area (m2)', 'Crown area status', 'dbh_vs_crown_area', 'DBH (cm)', 'Crown projected area (m²)'),
             ('Height ITSMe (m)', 'Height status', 'Crown projected area (m2)', 'Crown area status', 'height_vs_crown_area', 'Tree height (m)', 'Crown projected area (m²)')]
    for xc, xs, yc, ys, name, xl, yl in pairs:
        both = [(w[xc], w[yc]) for w in W if w[xs] == 'VALID' and w[ys] == 'VALID' and isinstance(w[xc], float) and isinstance(w[yc], float)]
        rev = [(w[xc], w[yc]) for w in W if {w[xs], w[ys]} <= {'VALID', 'REVIEW'} and 'REVIEW' in (w[xs], w[ys]) and isinstance(w[xc], float) and isinstance(w[yc], float)]
        fig, ax = plt.subplots(figsize=(7, 5))
        if rev:
            ax.scatter(*zip(*rev), s=40, marker=SERIES['REVIEW'][1], facecolor='none', edgecolor=SERIES['REVIEW'][0], linewidth=1.4,
                       label=f'at least one value REVIEW (n = {len(rev)})')
        ax.scatter(*zip(*both), s=40, marker='o', color=SERIES['VALID'][0], edgecolor='#fcfcfb', linewidth=1, label=f'both VALID (n = {len(both)})')
        x, y = np.log(np.array(both)).T
        b, a = np.polyfit(x, y, 1)
        r2 = 1 - np.sum((y - (a + b * x)) ** 2) / np.sum((y - y.mean()) ** 2)
        rho = float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])
        xs_ = np.linspace(x.min(), x.max(), 50)
        ax.plot(np.exp(xs_), np.exp(a + b * xs_), color='#52514e', lw=2, label=f'log-log fit, VALID only: y = {math.exp(a):.3g}·x^{b:.2f}, R² = {r2:.2f}')
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_title(f'{yl.split(" (")[0]} vs {xl.split(" (")[0]}', loc='left', fontsize=12)
        ax.legend(frameon=False, fontsize=9, loc='upper left')
        save(fig, name)
        stats[name] = dict(valid_pairs=len(both), review_pairs=len(rev), loglog_slope=b, loglog_intercept=a, loglog_r2=r2, spearman_rho=rho)
    metrics = [('Height', 'Height status'), ('DBH', 'DBH status'), ('Crown base', 'Crown base status'),
               ('Crown area', 'Crown area status'), ('Crown volume', 'Crown volume status')]
    order = ['VALID', 'REVIEW', 'N/A', 'ESTIMATED', 'UNKNOWN']
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ypos = np.arange(len(metrics))[::-1]
    left = np.zeros(len(metrics))
    counts = {m: {s: sum(w[sc] == s for w in W) for s in order} for m, sc in metrics}
    for s in order:
        c = np.array([counts[m][s] for m, _ in metrics])
        ax.barh(ypos, c, left=left, color=STAT_FILL[s], edgecolor='#52514e', linewidth=.8, height=.62, label=s)
        for yi, li, ci in zip(ypos, left, c):
            if ci >= 6:
                ax.text(li + ci / 2, yi, str(ci), ha='center', va='center', fontsize=10, color='#0b0b0b')
        left += c
    ax.set_yticks(ypos, [m for m, _ in metrics]); ax.set_xlabel('Number of trees (of 163)'); ax.set_xlim(0, 163)
    ax.set_title('Measurement status per metric (colours as in the workbook)', loc='left', fontsize=12)
    ax.legend(frameon=False, ncol=5, loc='upper center', bbox_to_anchor=(.5, -.16), fontsize=9)
    ax.grid(axis='y', visible=False)
    save(fig, 'measurement_status_counts')
    stats['measurement_status_counts'] = counts
    return made, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', required=True)
    ap.add_argument('--out', default='')
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--trees', default='')
    ap.add_argument('--skip-extras', action='store_true')
    a = ap.parse_args()
    final = Path(a.final)
    out = Path(a.out) if a.out else MP / 'results' / f'ITSMe_all163_visualisations_{datetime.now():%Y%m%d_%H%M%S}'
    for d in ('individual_trees', 'comparisons', 'report_figures', 'logs'):
        (out / d).mkdir(parents=True, exist_ok=True)
    wb_hash_before = sha(final / 'ITSMe_all163_results.xlsx')
    rows_w = workbook_rows(final)
    trees = [t for t in a.trees.split(',') if t] or sorted(rows_w)
    script_hash = sha(Path(__file__))
    t0 = time.time()
    jobs, done = [], []
    for tid in trees:
        png = out / 'individual_trees' / f'{tid}_3D_sideviews.png'
        side = png.with_suffix('.json')
        prep = json.loads((final / 'per_tree' / tid / 'prep.json').read_text())
        if png.exists() and side.exists():
            m = json.loads(side.read_text())
            if m.get('source_sha256') == prep['review_sha256'] and m.get('style') == STYLE_VERSION and m.get('title') == title_for(tid, rows_w[tid])                     and m.get('subtitle') == subtitle_for(rows_w[tid]) \
                    and m.get('png_sha256') == sha(png):
                done.append(dict(m, reused=True)); continue
        jobs.append(dict(tree=tid, final=str(final), png=str(png), w=rows_w[tid]))
    workers = a.workers or max(1, min(32, (os.cpu_count() or 2) // 2))
    failures = []
    with ProcessPoolExecutor(workers) as ex:
        futs = {j['tree']: ex.submit(render_tree, j) for j in jobs}
        for tid, f in futs.items():
            try:
                done.append(dict(f.result(), reused=False))
            except Exception as e:
                failures.append(dict(tree=tid, error=repr(e)))
    t_ind = time.time() - t0
    grids = []
    if not a.skip_extras:
        Wd = rows_w

        def ranked(col, scol, reverse):
            v = [(w[col], t) for t, w in Wd.items() if w[scol] == 'VALID' and isinstance(w[col], float)]
            return [t for _, t in sorted(v, reverse=reverse)]
        dbh_lbl, area_lbl, quality = 'dbh', 'area', 'quality'
        good = [t for t, w in Wd.items() if all(w[s] == 'VALID' for s in ('Height status', 'DBH status', 'Crown area status', 'Crown volume status'))]
        poor = sorted(Wd, key=lambda t: -sum((Wd[t][s] in ('N/A', 'REVIEW')) + (Wd[t][s] == 'N/A') for s in ('Height status', 'DBH status', 'Crown area status', 'Crown volume status')))
        unusual = ['tree_079', 'tree_087', 'tree_125', 'tree_118', 'tree_050', 'tree_152', 'tree_026', 'tree_001']
        G = out / 'comparisons'
        specs = [
            (ranked('Height ITSMe (m)', 'Height status', False), 'shortest_8', 'shortest 8 trees with VALID height: sampled display only; red fitted stem centres; no completeness approval', G / 'shortest_8_trees.png', None),
            (ranked('Height ITSMe (m)', 'Height status', True), 'tallest_8', 'tallest 8 trees with VALID height: sampled display only; red fitted stem centres; no completeness approval', G / 'tallest_8_trees.png', None),
            (ranked('DBH (cm)', 'DBH status', True), 'largest_dbh', 'largest 8 VALID DBH: sampled display only; red fitted stem centres', G / 'largest_dbh_trees.png', dbh_lbl),
            (ranked('DBH (cm)', 'DBH status', False), 'smallest_dbh', 'smallest 8 VALID DBH: sampled display only; red fitted stem centres', G / 'smallest_dbh_trees.png', dbh_lbl),
            (ranked('Crown projected area (m2)', 'Crown area status', True), 'largest_crown', 'largest 8 VALID crown areas: sampled display only', G / 'largest_crown_trees.png', area_lbl),
            (ranked('Crown projected area (m2)', 'Crown area status', False), 'smallest_crown', 'smallest 8 VALID crown areas: sampled display only', G / 'smallest_crown_trees.png', area_lbl),
            (sorted(good)[:4] + poor[:4], 'segmentation_quality', 'Segmentation and measurement quality: top 2 rows = all four core metrics VALID; bottom 2 rows = most N/A or REVIEW', G / 'segmentation_quality_comparison.png', quality),
            (unusual, 'unusual_structures', 'Unusual or irregular structures: 079 two merged trunks (very large crown), 087 leaning snag, 125 bent stem, 118 second leaning stem, 050 dead snag, 152 forked crown, 026 understorey at the base, 001 no stem axis', G / 'unusual_structures.png', quality)]
        with ProcessPoolExecutor(min(8, workers)) as ex:
            for g in ex.map(grid_job, [(tr, lab, st_, rows_w, final, png, lbl) for tr, lab, st_, png, lbl in specs]):
                grids.append(g)
        made, stats = report_figures(rows_w, out / 'report_figures')
    else:
        made, stats = [], {}
    wb_hash_after = sha(final / 'ITSMe_all163_results.xlsx')
    done.sort(key=lambda m: m['tree'])
    with (out / 'visualisation_index.csv').open('w', newline='', encoding='utf-8') as f:
        cols = ['tree', 'individual_figure', 'png_sha256', 'source_file', 'source_sha256', 'points', 'display_points', 'stem_marker',
                'height_status', 'dbh_status', 'crown_area_status', 'crown_volume_status', 'human_approval', 'title', 'comparison_figures']
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        for m in done:
            w = rows_w[m['tree']]
            wr.writerow(dict(tree=m['tree'], individual_figure=os.path.relpath(m['png'], out), png_sha256=m['png_sha256'], source_file=m['source_file'],
                             source_sha256=m['source_sha256'], points=m['points'], display_points=m['display_points'], stem_marker=m['stem_marker'],
                             height_status=w['Height status'], dbh_status=w['DBH status'], crown_area_status=w['Crown area status'],
                             crown_volume_status=w['Crown volume status'], human_approval=w['Human approval'], title=m['title'],
                             comparison_figures=';'.join(Path(g['figure']).name for g in grids if m['tree'] in g['trees'])))
    log = dict(final=str(final), individual=len(done), reused=sum(m['reused'] for m in done), failures=failures, workers=workers,
               seconds_individual=t_ind, seconds_total=time.time() - t0, grids=grids, report_figures=made, report_stats=stats,
               workbook_sha256_before=wb_hash_before, workbook_sha256_after=wb_hash_after, script_sha256=script_hash,
               sampling=dict(individual=f'{SAMPLE_N} random points, numpy default_rng({SEED}), when a tree has more', grids=f'65000, default_rng({SEED})'))
    (out / 'logs/render_log.json').write_text(json.dumps(log, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: log[k] for k in ('individual', 'reused', 'failures', 'workers', 'seconds_individual', 'seconds_total', 'report_figures')}, indent=1, default=float))
    print(out)


if __name__ == '__main__':
    main()
