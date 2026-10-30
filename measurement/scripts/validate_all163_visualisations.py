"""Validate the all-163 visualisation outputs against the final audited workbook and the source clouds.

Usage: python -I validate_all163_visualisations.py --vis <visualisation folder> --final <ITSMe_all163_output_v6_FINAL folder>
Writes <vis>/logs/visualisation_validation.json.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'verification_output' / '_deps'))
from PIL import Image
from xlsx_writer import read_xlsx_rows

ROOT = Path(__file__).resolve().parents[2]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vis', required=True)
    ap.add_argument('--final', required=True)
    a = ap.parse_args()
    vis, final = Path(a.vis), Path(a.final)
    rows = read_xlsx_rows(final / 'ITSMe_all163_results.xlsx')['All Tree Results']
    W = {r[0]: dict(zip(rows[0], r)) for r in rows[1:]}
    snap = {r['file']: r['sha256'] for r in csv.DictReader(open(ROOT / 'session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv', encoding='utf-8-sig'))}
    log = json.loads((vis / 'logs/render_log.json').read_text())
    index = list(csv.DictReader(open(vis / 'visualisation_index.csv', encoding='utf-8')))
    checks, problems = {}, []
    checks['all_163_trees_in_index_once'] = sorted(r['tree'] for r in index) == sorted(W) and len(index) == 163
    pngs = sorted((vis / 'individual_trees').glob('*_3D_sideviews.png'))
    checks['163_individual_pngs'] = len(pngs) == 163 and {p.name.split('_3D')[0] for p in pngs} == set(W)
    sizes = set()
    for p in pngs:
        tid = p.name.split('_3D')[0]
        meta = json.loads(p.with_suffix('.json').read_text())
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            sizes.add(im.size); dpi = im.info.get('dpi', (0, 0))
        w = W[tid]
        hs = w['Height status']
        expected_h = (f"{w['Height ITSMe (m)']:.3f} m {'preliminary' if hs == 'VALID' else 'REVIEW'}" if hs in ('VALID', 'REVIEW') else 'Height: N/A')
        expected = f"{tid}: {expected_h}; Human Approval: {w['Human approval']}"
        prep = json.loads((final / 'per_tree' / tid / 'prep.json').read_text())
        if meta['title'] != expected:
            problems.append((tid, 'title', meta['title'], expected))
        if meta['png_sha256'] != sha(p):
            problems.append((tid, 'png hash'))
        if meta['source_sha256'] != snap[w['Review file']] or meta['source_file'] != w['Review file']:
            problems.append((tid, 'source cloud mismatch'))
        if meta['stem_marker'] != (prep.get('axis_o') is not None):
            problems.append((tid, 'stem marker'))
        if meta['points'] != w['Points']:
            problems.append((tid, 'point count', meta['points'], w['Points']))
        if round(dpi[0]) < 299:
            problems.append((tid, 'dpi', dpi))
        if 'APPROVED' in meta['title'].upper() and 'PENDING' not in meta['title']:
            problems.append((tid, 'approval claimed'))
        for col, scol in [('DBH (cm)', 'DBH status'), ('Crown projected area (m2)', 'Crown area status'), ('Crown envelope volume (m3)', 'Crown volume status'),
                          ('Crown volume, 1 m slab hulls (m3)', 'Crown slab volume status')]:
            if f'[{w[scol]}]' not in meta['subtitle']:
                problems.append((tid, 'subtitle status', scol))
            if w[scol] == 'N/A' and isinstance(w[col], float):
                problems.append((tid, 'N/A with value', col))
        est = w.get('Estimated DBH (cm)')
        if w['DBH status'] == 'N/A' and isinstance(est, float) and f'ESTIMATED {est:.1f} cm' not in meta['subtitle']:
            problems.append((tid, 'estimated DBH missing from subtitle'))
        if w['DBH status'] != 'N/A' and 'ESTIMATED' in meta['subtitle']:
            problems.append((tid, 'estimate shown next to a measured DBH'))
    checks['images_open_300dpi_titles_sources_markers_correct'] = not problems
    checks['single_figure_size'] = len(sizes) == 1
    # Ranking checks: shortest / tallest 8 among VALID heights; largest/smallest VALID DBH and crown area
    def ranked(col, scol, rev):
        return [t for _, t in sorted(((W[t][col], t) for t in W if W[t][scol] == 'VALID' and isinstance(W[t][col], float)), reverse=rev)][:8]
    grids = {Path(g['figure']).name: g['trees'] for g in log['grids']}
    expect = {'shortest_8_trees.png': ranked('Height ITSMe (m)', 'Height status', False), 'tallest_8_trees.png': ranked('Height ITSMe (m)', 'Height status', True),
              'largest_dbh_trees.png': ranked('DBH (cm)', 'DBH status', True), 'smallest_dbh_trees.png': ranked('DBH (cm)', 'DBH status', False),
              'largest_crown_trees.png': ranked('Crown projected area (m2)', 'Crown area status', True),
              'smallest_crown_trees.png': ranked('Crown projected area (m2)', 'Crown area status', False)}
    checks['comparison_rankings_use_valid_values_only'] = all(grids.get(k, [])[:8] == v for k, v in expect.items())
    comp = sorted((vis / 'comparisons').glob('*.png'))
    ok = True
    for p in comp:
        with Image.open(p) as im:
            im.verify()
    checks['comparison_figures_open'] = len(comp) == len(log['grids']) and ok
    rep = sorted((vis / 'report_figures').glob('*.png'))
    checks['report_figures_png_and_pdf'] = len(rep) == len(log['report_figures']) and all(p.with_suffix('.pdf').exists() for p in rep)
    checks['validated_workbook_unchanged'] = log['workbook_sha256_before'] == log['workbook_sha256_after'] == sha(final / 'ITSMe_all163_results.xlsx')
    checks['no_render_failures'] = not log['failures']
    out = dict(checks=checks, all_passed=all(checks.values()), problems=problems, figure_size_px=sorted(sizes), expected_rankings=expect,
               counts=dict(individual=len(pngs), comparisons=len(comp), report_png=len(rep)))
    (vis / 'logs/visualisation_validation.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('checks', 'all_passed', 'figure_size_px', 'counts')}, indent=1, default=str))
    print('problems:', problems[:10])


if __name__ == '__main__':
    main()
