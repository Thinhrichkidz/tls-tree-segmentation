"""Every number the v8 report quotes, from a final all-163 folder (28 Oct 2026).
Usage: python report_stats_v8.py <final folder> [<v3 FINAL folder: re-checks that the definitions reproduce v7 values>]
Prints JSON. Read-only."""
import csv, json, math, statistics as S, sys
from collections import Counter
from pathlib import Path

F = Path(sys.argv[1]); V3 = Path(sys.argv[2]) if len(sys.argv) > 2 else None
recs = {r['tree']: r for r in json.loads((F / 'logs/records.json').read_text())}
att = {r['tree_id']: r for r in csv.DictReader(open(F / 'results/tree_attributes.csv', encoding='utf-8'))}
preps = {t: json.loads((F / 'per_tree' / t / 'prep.json').read_text()) for t in recs}
ress = {t: json.loads((F / 'per_tree' / t / 'result.json').read_text()) for t in recs}
summ = json.loads((F / 'results/summary.json').read_text())
out = {}


def med_rng(v, nd):
    v = sorted(v); return f'{S.median(v):.{nd}f} ({v[0]:.{nd}f}--{v[-1]:.{nd}f})' if v else '-'


for k, nd in (('height', 2), ('dbh', 2), ('crown_base', 2), ('crown_area', 2), ('crown_volume', 1), ('crown_volume_slab', 1)):
    c = Counter(r[k]['s'] for r in recs.values())
    out[k] = dict(VALID=c['VALID'], REVIEW=c['REVIEW'], NA=c['N/A'],
                  valid=med_rng([r[k]['v'] for r in recs.values() if r[k]['s'] == 'VALID'], nd),
                  all=med_rng([r[k]['v'] for r in recs.values() if r[k]['s'] in ('VALID', 'REVIEW')], nd))
# DBH detail
meas = [t for t, r in recs.items() if r['dbh']['s'] in ('VALID', 'REVIEW')]
na = [t for t, r in recs.items() if r['dbh']['s'] == 'N/A']
out['dbh_detail'] = dict(measured=len(meas), direct=sum(not (ress[t].get('dbh_method') or '').startswith('median') for t in meas),
                         slice_median=sum((ress[t].get('dbh_method') or '').startswith('median') for t in meas),
                         na_no_axis=sum(preps[t].get('axis_o') is None for t in na), na_withheld=['tree_033'] if 'tree_033' in na else [],
                         na_no_fit=sum(preps[t].get('axis_o') is not None and t != 'tree_033' for t in na),
                         estimated=sum(bool(r['dbh_est']) for r in recs.values()),
                         estimated_by_method=dict(Counter(r['dbh_est']['method'] for r in recs.values() if r['dbh_est'])),
                         estimated_no_axis=sum(bool(r['dbh_est']) and preps[t].get('axis_o') is None for t, r in recs.items()),
                         any_dbh=len(meas) + sum(bool(r['dbh_est']) for r in recs.values()),
                         estimated_median_range=med_rng([r['dbh_est']['v'] for r in recs.values() if r['dbh_est']], 1))
# crown base sources
src = Counter('rule' if (p.get('crown_base_source') or '').startswith('continuous-crown rule') else ('none' if p.get('crown_base_m') is None else 'chosen') for p in preps.values())
out['crown_base_source'] = dict(src)
# all four VALID
av = [t for t, r in recs.items() if r['all_core_valid']]
out['all_valid'] = dict(n=len(av), trees=[t[5:] for t in av], height=f"{S.median(recs[t]['height']['v'] for t in av):.1f}",
                        dbh=f"{S.median(recs[t]['dbh']['v'] for t in av):.1f}", envelope=f"{S.median(recs[t]['crown_volume']['v'] for t in av):.1f}",
                        slab=f"{S.median(recs[t]['crown_volume_slab']['v'] for t in av):.1f}")
out['tree_status'] = summ['tree_status']


# height-DBH
def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y); mx, my = S.fmean(rx), S.fmean(ry)
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))


pairs = [(recs[t]['height']['v'], recs[t]['dbh']['v'], recs[t]['height']['s'] == 'VALID' and recs[t]['dbh']['s'] == 'VALID') for t in meas if recs[t]['height']['v']]
ratio = [h / (d / 100) for h, d, _ in pairs]
vp = [(h, d) for h, d, ok in pairs if ok]
lx = [math.log(d) for h, d in vp]; ly = [math.log(h) for h, d in vp]; mx, my = S.fmean(lx), S.fmean(ly)
b = sum((a - mx) * (c - my) for a, c in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx); a0 = math.exp(my - b * mx)
r2 = 1 - sum((c - (math.log(a0) + b * a)) ** 2 for a, c in zip(lx, ly)) / sum((c - my) ** 2 for c in ly)
out['h_d'] = dict(n_pairs=len(pairs), ratio=f'{min(ratio):.1f}--{max(ratio):.1f} (median {S.median(ratio):.1f})', rho_all=round(spearman([p[0] for p in pairs], [p[1] for p in pairs]), 2),
                  n_valid=len(vp), rho_valid=round(spearman([h for h, d in vp], [d for h, d in vp]), 2), fit=f'H = {a0:.2f} D^{b:.2f}, R2 = {r2:.2f}')
# largest crowns
cv = max(recs, key=lambda t: recs[t]['crown_volume']['v'] or 0); ca = max(recs, key=lambda t: recs[t]['crown_area']['v'] or 0)
out['largest'] = dict(volume=(cv, round(recs[cv]['crown_volume']['v'], 1), recs[cv]['crown_volume']['s'], round(recs[cv]['crown_volume_slab']['v'], 1)),
                      area=(ca, round(recs[ca]['crown_area']['v'], 1), recs[ca]['crown_area']['s']))
# outliers
out['outliers'] = dict(Counter(r['reason'] for r in csv.DictReader(open(F / 'results/outliers.csv', encoding='utf-8'))))
out['outliers_total'] = sum(out['outliers'].values())
# structure
out['structure'] = dict(clusters2=sum((p.get('n_stems_at_1_3m') or 0) >= 2 for p in preps.values()), fork=sum(bool(p.get('flag_fork_near_dbh')) for p in preps.values()),
                        lean10=sum(a['flag_lean'] == 'TRUE' for a in att.values()), lean_na=sum(a['flag_lean'] == 'NA' for a in att.values()),
                        edge_touch=sum(bool(p.get('flag_crown_touches_edge')) for p in preps.values()), stems_2m=sum(p['dist_to_roi_edge_m'] < 2 for p in preps.values()),
                        all_valid_touching=sum(bool(preps[t].get('flag_crown_touches_edge')) for t in av))
# envelope vs slab
rat = [recs[t]['crown_volume']['v'] / recs[t]['crown_volume_slab']['v'] for t in recs if recs[t]['crown_volume']['v'] and recs[t]['crown_volume_slab']['v']]
out['envelope_over_slab'] = f'median {S.median(rat):.2f}, max {max(rat):.2f}, n {len(rat)}'


# sensitivity (definition checked against v7's 2.9 % on the v3 file)
def sens(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8'))); m = 0; who = None
    for r in rows:
        v = [float(r[c]) for c in ('dbh_circle_3cm_cm', 'dbh_circle_5cm_cm', 'dbh_circle_6cm_cm', 'dbh_circle_10cm_cm') if r[c] not in ('', 'NA')]
        ch = (max(v) - min(v)) / float(r['reported_dbh_cm']) * 100
        if ch > m: m, who = ch, r['tree']
    return round(m, 1), who, len(rows)


out['sensitivity_v6'] = sens(F / 'results/sensitivity.csv')
if V3: out['sensitivity_v3_check'] = sens(V3 / 'results/sensitivity.csv')


# independent re-fit (definition checked against v7: 14 compared, 5 failed, 9 median 0.16 max 2.16 tree_002)
def indep(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    comp = [r for r in rows if r['dbh_independent_cm'] not in ('', 'None') and r.get('dbh_workbook_cm', r.get('dbh_reported_cm', '')) not in ('', 'None')]
    key = 'dbh_workbook_cm' if 'dbh_workbook_cm' in rows[0] else [k for k in rows[0] if 'dbh' in k and ('workbook' in k or 'reported' in k)][0]
    comp = [r for r in rows if r['dbh_independent_cm'] not in ('', 'None', 'NA') and r[key] not in ('', 'None', 'NA')]
    ok = [r for r in comp if r['dbh_ind_passes'] in ('True', 'TRUE', '1')]
    d = sorted((abs(float(r['dbh_independent_cm']) - float(r[key])), r['tree']) for r in ok)
    hd = max(abs(float(r['height_diff_m'])) for r in rows if r['height_diff_m'] not in ('', 'None'))
    return dict(trees=len(rows), compared=len(comp), failed=len(comp) - len(ok), passing=len(ok), median=round(S.median(x for x, _ in d), 2), max=(round(d[-1][0], 2), d[-1][1]), height_max=hd)


out['independent_v6'] = indep(F / 'logs/independent_verification.csv')
if V3: out['independent_v3_check'] = indep(V3 / 'logs/independent_verification.csv')
# points
out['refined_points'] = sum(int(float(a['n_points'])) for a in att.values())
# height refinements
moved = [(t[5:], r['height_foot']['dz_m']) for t, r in recs.items() if r.get('height_foot', {}).get('source')]
out['moved_feet'] = dict(n=len(moved), dz=f"{min(d for _, d in moved):+.2f} to {max(d for _, d in moved):+.2f}", over10cm=sum(abs(d) > .10 for _, d in moved))
out['height_REVIEW_reasons'] = dict(Counter(x.strip().split('(')[0].split(':')[0].strip()[:55] for r in recs.values() if r['height']['s'] == 'REVIEW' for x in r['height']['why'].split(';') if x.strip()).most_common(9))
out['checks'] = len(json.loads((F / 'logs/validation.json').read_text())['checks'])
print(json.dumps(out, indent=1, default=str))
