"""Field check sheet for the all-163 results: a small, reasoned sample of trees to measure by tape and hypsometer.

Usage: python -I field_check_sheet.py --final <ITSMe_all163_output_v6_FINAL folder> --out <folder>
Writes FIELD_CHECK_SHEET.xlsx (printable, blank columns for field values), field_check_trees.csv, field_check_map.png and README.md.
Read-only on the results. Selection is deterministic (see SELECTION below).
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import all163_common as C
from xlsx_styled import HEADER, TITLE, write_xlsx

SELECTION = """1. Five trees with all four core values VALID, spread over DBH (smallest, quartiles, median, largest): tests the core results.
2. Three trees with an ESTIMATED DBH, one per method (v4 pooled fit, v4b small-stem floor, v4b RANSAC), the median-DBH tree of each: tests the estimates.
3. tree_100 and tree_124: heights fell 9.5 m and 7.7 m after floating points above the crown were removed: tests that cleaning.
4. tree_095: DBH 36.7 cm with dense understorey round the stem base (repo README issue 7, resolved by slice plots): tests the clutter case (counted once if already chosen in group 1).
5. Two trees with a measured DBH whose height is REVIEW for ground uncertainty, with the largest difference between the two ground references: tests the height uncertainty."""


def utm_to_latlon(x, y, zone=56, south=True):
    """WGS84 UTM -> latitude/longitude (Snyder 1987, inverse transverse Mercator)."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    x -= 500000.0
    if south:
        y -= 10000000.0
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    n1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); t1 = math.tan(p1) ** 2; c1 = ep2 * math.cos(p1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5; d = x / (n1 * k0)
    lat = p1 - (n1 * math.tan(p1) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
                                          + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p1)
    return math.degrees(lat), (zone - 1) * 6 - 180 + 3 + math.degrees(lon)


def latlon_to_utm(lat, lon, zone=56, south=True):
    """WGS84 latitude/longitude -> UTM (Snyder 1987); used only to check the inverse."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon - ((zone - 1) * 6 - 180 + 3))
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2); t = math.tan(phi) ** 2; c = ep2 * math.cos(phi) ** 2; A = math.cos(phi) * lam
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi) - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    x = k0 * n * (A + (1 - t + c) * A ** 3 / 6 + (5 - 18 * t + t ** 2 + 72 * c - 58 * ep2) * A ** 5 / 120) + 500000.0
    y = k0 * (m + n * math.tan(phi) * (A ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * A ** 4 / 24 + (61 - 58 * t + t ** 2 + 600 * c - 330 * ep2) * A ** 6 / 720))
    return x, y + (10000000.0 if south else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    final, out = Path(a.final), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs = {r['tree']: r for r in json.loads((final / 'logs/records.json').read_text())}
    att = {r['tree_id']: r for r in C.rows(final / 'results/tree_attributes.csv')}
    heights = {r['stable_tree_id']: r for r in C.rows(C.MP / 'results/all_tree_preliminary_heights.csv')}
    preps = {t: json.loads((final / 'per_tree' / t / 'prep.json').read_text()) for t in recs}
    roi = json.loads((final / 'manifests/roi.json').read_text())['bbox_xy']
    f = lambda x: float(x) if x not in ('', 'NA', None) else None

    chosen = []   # (tree, reason)

    def take(t, why):
        if t not in [c[0] for c in chosen]:
            chosen.append((t, why))
    # 1. all-VALID trees spread over DBH
    av = sorted((recs[t]['dbh']['v'], t) for t in recs if recs[t]['all_core_valid'])
    for q in (0, .25, .5, .75, 1):
        d, t = av[round(q * (len(av) - 1))]
        take(t, f'all four core values VALID (DBH {d:.1f} cm, {"smallest" if q == 0 else "largest" if q == 1 else f"{int(q * 100)}th percentile"} of those trees)')
    # 2. one ESTIMATED DBH per method, median DBH within the method
    for m, label in (('v4', 'v4 pooled fit'), ('v4b FLOOR', 'v4b small-stem RMSE floor'), ('v4b RANSAC', 'v4b hollow-trunk RANSAC')):
        g = sorted((recs[t]['dbh_est']['v'], t) for t in recs if recs[t]['dbh_est'] and recs[t]['dbh_est']['method'] == m)
        if g:
            d, t = g[len(g) // 2]
            take(t, f'ESTIMATED DBH {d:.1f} cm ({label}); DBH column N/A')
    # 3. floating points removed above the crown
    take('tree_100', 'height fell 9.5 m after floating points above the crown were removed (now 17.28 m)')
    take('tree_124', 'height fell 7.7 m after floating points above the crown were removed (now 13.41 m)')
    # 4. clutter case
    take('tree_095', 'DBH 36.7 cm with dense understorey round the stem base; other fits gave 67-89 cm')
    # 5. ground-uncertain heights with a measured DBH
    gu = sorted(((abs(f(heights[t]['ground_reference_scenario_height_difference_m']) or 0), t) for t in recs
                 if recs[t]['height']['s'] == 'REVIEW' and 'ground reference uncertain' in recs[t]['height']['why']
                 and recs[t]['dbh']['s'] in ('VALID', 'REVIEW') and t not in [c[0] for c in chosen]), reverse=True)
    for d, t in gu[:2]:
        take(t, f'height REVIEW: ground uncertain (the two ground references differ by {d:.2f} m)')

    rows, csv_rows = [], []
    head = ['#', 'Tree', 'Why it is in the sample', 'Easting (m)', 'Northing (m)', 'Latitude', 'Longitude', 'Distance to plot edge (m)',
            'Our height (m)', 'Height status', 'Our DBH (cm)', 'DBH status', 'Stem lean (deg)',
            'FIELD DBH at 1.3 m (cm)', 'FIELD height (m)', 'Instrument / method', 'Fork, lean, damage, notes', 'Photo no.']
    for i, (t, why) in enumerate(chosen, 1):
        r, p = recs[t], preps[t]
        x, y = p['stem_xy']
        lat, lon = utm_to_latlon(x, y)
        xb, yb = latlon_to_utm(lat, lon)
        assert math.hypot(xb - x, yb - y) < 0.01, 'UTM round trip failed'
        dbh, dst = (r['dbh']['v'], r['dbh']['s']) if r['dbh']['v'] is not None else ((r['dbh_est']['v'], 'ESTIMATED') if r['dbh_est'] else (None, r['dbh']['s']))
        lean = r.get('lean')
        vals = [i, t, why, round(x, 2), round(y, 2), round(lat, 6), round(lon, 6), round(p['dist_to_roi_edge_m'], 1),
                round(r['height']['v'], 2), r['height']['s'], round(dbh, 1) if dbh is not None else 'N/A', dst, round(lean, 1) if lean is not None else '-']
        rows.append(vals + ['', '', '', '', ''])
        csv_rows.append(dict(zip(head, vals + ['', '', '', '', ''])))
    instructions = [
        [('Field check: how to measure', TITLE)], [],
        ['Purpose', 'Compare the TLS values with independent field measurements. Every accuracy figure so far compares methods with each other only.'],
        ['DBH', 'Diameter tape at 1.3 m above the ground on the uphill side. On a leaning stem, measure 1.3 m along the stem and at right angles to it. Record a fork below 1.3 m (measure each stem) or any swelling at 1.3 m.'],
        ['Height', 'Hypsometer or laser rangefinder from a point where the top is clearly visible, at least one tree height away. Take two readings from different sides; enter both or their mean. Aim at the highest foliage, not just the main stem.'],
        ['Finding the trees', 'Easting/Northing are EPSG:32756 (WGS 84 / UTM zone 56S), stem position at 1.3 m (or the stem foot where there is no stem axis). Latitude/longitude are WGS 84, converted with the standard UTM formulas (round trip < 1 cm). Use field_check_map.png for the layout.'],
        ['Statuses', 'VALID = passed all checks; REVIEW = value exists but a concern is open; ESTIMATED = DBH from the new fallback methods, not in the DBH column.'],
        ['Selection', SELECTION.replace('\n', ' ')],
        ['After the field day', 'Fill in the FIELD columns and bring the sheet back; the comparison (bias, error per status group) can then be computed directly.'],
    ]
    hdr = [[(h, HEADER) for h in head]]
    write_xlsx(out / 'FIELD_CHECK_SHEET.xlsx', [
        dict(name='Field sheet', rows=hdr + rows, freeze=(1, 2), widths=[4, 10, 52, 12, 13, 11, 11, 10, 9, 9, 9, 11, 8, 14, 12, 16, 30, 9]),
        dict(name='Instructions', rows=instructions, freeze=None, widths=[18, 140])])
    with (out / 'field_check_trees.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=head); w.writeheader(); w.writerows(csv_rows)
    # map
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    x0, y0, x1, y1 = roi
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.add_patch(plt.Rectangle((0, 0), x1 - x0, y1 - y0, fill=False, lw=1.5, ec='#444'))
    allxy = [(p['stem_xy'][0] - x0, p['stem_xy'][1] - y0) for p in preps.values()]
    ax.scatter(*zip(*allxy), s=12, c='#b7b5ad', label='other trees (163 in total)')
    for i, (t, _) in enumerate(chosen, 1):
        x, y = preps[t]['stem_xy']; ax.scatter([x - x0], [y - y0], s=70, c='#2a78d6', zorder=3)
        ax.annotate(f'{i}: {t[5:]}', (x - x0, y - y0), xytext=(5, 5), textcoords='offset points', fontsize=10, weight='bold')
    ax.set_aspect('equal'); ax.set_xlim(-2, x1 - x0 + 2); ax.set_ylim(-2, y1 - y0 + 2)
    ax.set_xlabel(f'metres east of plot corner (E {x0:.1f})'); ax.set_ylabel(f'metres north of plot corner (N {y0:.1f})')
    ax.annotate('N', xy=(0.95, 0.97), xytext=(0.95, 0.89), xycoords='axes fraction', ha='center', fontsize=14, arrowprops=dict(arrowstyle='->', lw=2))
    ax.set_title(f'Field check: {len(chosen)} sample trees (blue, numbered as in FIELD_CHECK_SHEET.xlsx)', loc='left')
    ax.grid(lw=.3); ax.legend(loc='lower right', frameon=False)
    fig.savefig(out / 'field_check_map.png', dpi=200, bbox_inches='tight'); plt.close(fig)
    lat0, lon0 = utm_to_latlon(x0, y0)
    (out / 'README.md').write_text(f"""# Field check sheet ({len(chosen)} trees)

Built from `{final.name}` with `measurement_pipeline/scripts/field_check_sheet.py` (read-only on the results).

- `FIELD_CHECK_SHEET.xlsx`: print the "Field sheet" tab and fill in the FIELD columns. The "Instructions" tab says how to measure.
- `field_check_trees.csv`: the same table.
- `field_check_map.png`: plot layout, with the sample trees numbered.
- Plot SW corner: E {x0:.1f}, N {y0:.1f} (EPSG:32756), about {lat0:.5f}, {lon0:.5f} (WGS 84).

## Selection
{SELECTION}

## Trees
""" + '\n'.join(f'{i}. **{t}**: {why}' for i, (t, why) in enumerate(chosen, 1)) + '\n', encoding='utf-8')
    print(json.dumps(dict(trees=[c[0] for c in chosen], out=str(out)), indent=1))


if __name__ == '__main__':
    main()
