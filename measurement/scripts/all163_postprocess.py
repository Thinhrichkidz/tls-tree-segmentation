"""All-163 post-processing: per-metric QC status, Excel workbook, data-request tables, summary and validation.

Usage: python -I all163_postprocess.py --out <ITSMe_all163_output folder>
Reads only the batch folder, the inherited QC table and earlier result files; never touches source clouds.
Status rules (also written to methods.json and the Methodology sheet):
  VALID     computed by the documented method and passes its quality rule, with no open concern.
  REVIEW    a value exists but a documented concern needs a human check (reason given).
  N/A       no reliable value: the method failed or the value failed its quality rule (reason given).
  UNKNOWN   the information needed to decide is missing.
  ESTIMATED not used: REPORT_DATA_REQUEST.md rule 1 forbids estimates; the column is kept empty on purpose.
"""
import argparse
import csv
import json
import math
import statistics
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import all163_common as C
from xlsx_styled import HEADER, TITLE, write_xlsx

MP, ROOT = C.MP, C.ROOT
COL = dict(VALID='D9EAD3', ESTIMATED='FFF2CC', **{'N/A': 'F4CCCC'}, REVIEW='FCE5CD', UNKNOWN='E7E6E6')
CORRECTED = {'tree_033', 'tree_067', 'tree_103', 'tree_108'}
AGREED_20 = MP / 'results/CROWN_BASE_RERUN_20261023_191046'
AXIS_FOOT_TOL_M = 0.25   # audit rule: axis/foot offsets above this caused the wrong bases on 103 and 108
EARLIER_PROVISIONAL = {'tree_056': 'earlier 10 cm-band review gave 10.66 cm (provisional, not adopted)',
                       'tree_080': 'earlier 15 cm-band review gave 16.44 cm (provisional, not adopted)'}


def f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def metric(value, status, reason=''):
    return dict(v=value if status in ('VALID', 'REVIEW') else None, s=status, why=reason)


def assess(tid, h, prep, res):
    rec = dict(tree=tid)
    errors = res.get('errors') or {}
    # ---------------- Height ----------------
    hv = f(res.get('itsme_height_m'))
    why = []
    if tid == 'tree_033':
        why.append('poor source data (user)')
    if tid in ('tree_103', 'tree_108'):
        pass  # corrected stem base agreed by the user
    else:
        if h['ground_reference_reliability'] != 'LOCALLY_SUPPORTED':
            why.append('ground reference uncertain (inherited QC)')
        if not h['foot_method'].startswith('ROBUST'):
            why.append('stem foot is a fallback (lowest observation)')
    if h['tree_top_reliability'] != 'LOCALLY_SUPPORTED_OBSERVED_TIP':
        why.append('tree top needs review (inherited QC)')
    if hv is not None and abs(hv - prep['supported_height_m']) > 0.5:
        why.append(f'highest point not locally supported ({hv - prep["supported_height_m"]:.2f} m above supported top)')
    if h['visual_exclusion_reason']:
        why.append(h['visual_exclusion_reason'])
    if h['review_sha256'] != prep['review_sha256'] and tid not in CORRECTED and tid != 'tree_102':
        why.append('cloud edited after the inherited QC; ground and QC flags not re-checked')
    off = f(prep.get('axis_offset_from_foot_m'))
    if off is not None and off > AXIS_FOOT_TOL_M:
        why.append(f'stem axis meets the ground {off:.2f} m from the foot used for the ground height (foot may be off the trunk)')
    rec['height'] = metric(hv, 'N/A', 'ITSMe height failed: ' + errors.get('height', '')) if hv is None else \
        metric(hv, 'REVIEW' if why else 'VALID', '; '.join(why))
    # ---------------- DBH ----------------
    dbh = f(res.get('dbh_m'))
    raw13 = f(res.get('dbh13_m'))
    arc, r2 = f(res.get('dbh13_arc')), f(res.get('dbh13_R2'))
    rmse = math.sqrt(r2) if r2 is not None else None
    unaccepted, note = None, ''
    if prep.get('axis_o') is None:
        rec['dbh'] = metric(None, 'N/A', 'no stem axis could be fitted (' + (prep.get('axis_failure') or 'unavailable') + ')')
    elif tid == 'tree_033':
        rec['dbh'] = metric(None, 'N/A', 'not released: poor source data (user), stem base missing; fits at 1.1-1.5 m inconsistent')
    elif dbh is None:
        fail = []
        if raw13 is None:
            fail.append('no circle fit at 1.3 m' + (' (' + errors['dbh'] + ')' if 'dbh' in errors else ''))
        else:
            lim = min(0.04, max(0.01, 0.1 * raw13))
            if arc is not None and arc < 0.6:
                fail.append(f'arc coverage {arc:.2f} < 0.60')
            if rmse is not None and rmse > lim:
                fail.append(f'RMSE {100 * rmse:.2f} cm > limit {100 * lim:.2f} cm')
            if not (0.03 < raw13 < 2):
                fail.append('diameter outside 3-200 cm')
            unaccepted = 100 * raw13
        if tid == 'tree_108':
            fail.append('3 cm point spacing is coarser than the screen allows for a ~9 cm stem; kept provisional (user decision)')
        if tid in EARLIER_PROVISIONAL:
            note = EARLIER_PROVISIONAL[tid]
        rec['dbh'] = metric(None, 'N/A', 'fit failed quality screen: ' + '; '.join(fail) + ('; ' + note if note else ''))
    else:
        why = []
        if prep['axis_source'].startswith('refitted'):
            why.append('stem axis refitted on current points')
        if not h['foot_method'].startswith('ROBUST') and tid not in CORRECTED:
            why.append('stem foot is a fallback; 1.3 m height uncertain')
        if prep.get('n_stems_at_1_3m', 1) >= 2:
            why.append(f'{prep["n_stems_at_1_3m"]} point clusters within 1 m of the stem at 1.3 m (second stem, branch or understorey?)')
        if res.get('dbh_method', '').startswith('median'):
            why.append('median of accepted 1.1-1.5 m slices, not a direct 1.3 m fit')
        off = f(prep.get('axis_offset_from_foot_m'))
        if off is not None and off > AXIS_FOOT_TOL_M:
            why.append(f'stem axis meets the ground {off:.2f} m from the foot; 1.3 m measurement height uncertain')
        rec['dbh'] = metric(100 * dbh, 'REVIEW' if why else 'VALID', '; '.join(why))
    rec['dbh_unaccepted_cm'] = unaccepted
    rec['dbh_fit_ok'] = dbh is not None and rec['dbh']['s'] in ('VALID', 'REVIEW')
    rec['dbh_rmse_cm'] = 100 * rmse if rmse is not None else None
    rec['dbh_arc'] = arc
    rec['dbh_points'] = res.get('dbh13_points')
    rec['dbh_method'] = res.get('dbh_method') if prep.get('axis_o') is not None else 'not attempted (no stem axis)'
    rec['area_eq_cm'] = 100 * f(res['area_equivalent_d_m']) if prep.get('dbh_report_mode') == 'CIRCLE_AND_AREA_EQUIVALENT' and f(res.get('area_equivalent_d_m')) else None
    rec['ellipse'] = (f(res.get('ellipse_minor_m')), f(res.get('ellipse_major_m')))
    rec['lean'] = f(res.get('axis_lean_deg')) if res.get('axis_lean_deg') is not None else f(prep.get('axis_lean_deg'))
    # ---------------- Crown ----------------
    base = f(prep.get('crown_base_m'))
    agreed = prep.get('crown_base_source', '') or ''
    user_reviewed = 'agreed 23 Oct 2026)' in agreed and 'automatic' not in agreed or 'user choice' in agreed
    excluded = [r for r in (prep.get('rule_crowned_runs_m') or '').split(' | ') if r and base is not None and f(r.split('-')[0]) < base - 1e-6]
    if base is None:
        rec['crown_base'] = metric(None, 'N/A', (prep.get('crown_base_failure') or prep.get('rule_failure')) or 'no crown base')
    elif not user_reviewed and excluded:
        rec['crown_base'] = metric(base, 'REVIEW', 'lower foliage layers below the base excluded (' + ', '.join(excluded) + ' m); ownership not checked')
    else:
        rec['crown_base'] = metric(base, 'VALID', '')
    crown = res.get('crown') or {}
    cwhy = []
    if res.get('crown_method', '').startswith('ALL_TREE_POINTS'):
        cwhy.append('ITSMe crown classification unavailable; crown = all tree points above the base')
    if rec['crown_base']['s'] == 'REVIEW':
        cwhy.append('crown base needs review')
    if prep.get('flag_crown_touches_edge'):
        cwhy.append('crown reaches the ROI boundary (may be truncated)')
    if tid == 'tree_033':
        cwhy.append('poor source data (user)')
    if h['crown_completeness'].startswith('BARE'):
        cwhy.append('bare or missing crown (inherited QC)')
    a = f(crown.get('area_m2'))
    v = f(crown.get('volume_m3'))
    ratio = f(crown.get('slab_ratio_1m'))
    if base is None:
        rec['crown_area'] = metric(None, 'N/A', 'no crown base: ' + ((prep.get('crown_base_failure') or prep.get('rule_failure')) or ''))
        rec['crown_volume'] = metric(None, 'N/A', 'no crown base: ' + ((prep.get('crown_base_failure') or prep.get('rule_failure')) or ''))
    else:
        rec['crown_area'] = metric(a, 'N/A', 'crown area failed: ' + str(crown.get('area_error') or errors.get('crown_envelope', ''))) if a is None else \
            metric(a, 'REVIEW' if cwhy else 'VALID', '; '.join(cwhy))
        vwhy = cwhy + ([f'envelope bridges large gaps (1 m slab ratio {ratio:.2f} > 2)'] if ratio and ratio > 2 else [])
        rec['crown_volume'] = metric(v, 'N/A', 'crown envelope failed: ' + str(crown.get('volume_error') or errors.get('crown_envelope', ''))) if v is None else \
            metric(v, 'REVIEW' if vwhy else 'VALID', '; '.join(vwhy))
    rec['slab_ratio'] = ratio
    rec['crown_points'] = crown.get('points')
    rec['crown_method'] = res.get('crown_method') or ''
    rec['auto'] = (f((res.get('auto') or {}).get('area_m2')), f((res.get('auto') or {}).get('volume_m3')), f(res.get('auto_crown_min_z_m')))

    def derived(val, parts, why_na):
        """Status of a derived value = worst status of its inputs. parts: {name: metric}."""
        sts = [p['s'] for p in parts.values()]
        if val is None or 'N/A' in sts:
            return metric(None, 'N/A', why_na)
        rev = [k for k, p in parts.items() if p['s'] == 'REVIEW']
        return metric(val, 'REVIEW' if rev else 'VALID', 'follows ' + ' and '.join(rev) + ' status' if rev else '')
    H, B = rec['height'], rec['crown_base']
    rec['crown_length'] = derived(H['v'] - B['v'] if H['v'] is not None and B['v'] is not None else None,
                                  {'height': H, 'crown base': B}, 'needs height and crown base')
    rec['crown_ratio'] = derived(rec['crown_length']['v'] / H['v'] if rec['crown_length']['v'] is not None else None,
                                 {'height': H, 'crown base': B}, 'needs height and crown base')
    rec['crown_diameter'] = derived(2 * math.sqrt(rec['crown_area']['v'] / math.pi) if rec['crown_area']['v'] is not None else None,
                                    {'crown area': rec['crown_area']}, 'needs crown area')
    rec['point_density'] = derived(rec['crown_points'] / rec['crown_volume']['v'] if rec['crown_volume']['v'] and rec['crown_points'] else None,
                                   {'crown volume': rec['crown_volume']}, 'needs crown volume')
    # ---------------- Flags ----------------
    rec['flag_lean'] = None if rec['lean'] is None else rec['lean'] >= 10
    rec['flag_truncated_top'] = h['tree_top_reliability'] != 'LOCALLY_SUPPORTED_OBSERVED_TIP' or 'TOP_OR_BOUNDARY_REVIEW' in h['height_qc_flags']
    core = [rec[k]['s'] for k in ('height', 'dbh', 'crown_area', 'crown_volume')]
    have = sum(s in ('VALID', 'REVIEW') for s in core)
    rec['tree_status'] = 'SUCCESS' if have == 4 else ('FAILED' if have == 0 else 'PARTIAL SUCCESS')
    rec['all_core_valid'] = all(s == 'VALID' for s in core)
    return rec


def stats(vals):
    vals = sorted(vals)
    if not vals:
        return dict(n=0)
    q = lambda p: vals[0] if len(vals) == 1 else statistics.quantiles(vals, n=100, method='inclusive')[p - 1]
    return dict(n=len(vals), mean=statistics.fmean(vals), median=statistics.median(vals),
                sd=statistics.stdev(vals) if len(vals) > 1 else None, min=vals[0], max=vals[-1], p25=q(25), p75=q(75))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--previous', default='', help='earlier all-163 output folder to compare against (optional)')
    args = ap.parse_args()
    out = Path(args.out)
    t0 = time.time()
    heights = {r['stable_tree_id']: r for r in C.rows(MP / 'results/all_tree_preliminary_heights.csv')}
    snap = {r['file']: r['sha256'] for r in C.rows(ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv')}
    man = C.rows(out / 'manifests/all163_manifest.csv')
    roi = json.loads((out / 'manifests/roi.json').read_text())
    timing = json.loads((out / 'logs/run_timing.json').read_text()) if (out / 'logs/run_timing.json').exists() else {}
    env = json.loads((out / 'logs/environment.json').read_text()) if (out / 'logs/environment.json').exists() else {}
    prep_log = json.loads((out / 'logs/prepare_log.json').read_text())
    recs, preps, results = [], {}, {}
    for m in man:
        tid = m['tree']
        prep = json.loads((out / 'per_tree' / tid / 'prep.json').read_text())
        rp = out / 'per_tree' / tid / 'result.json'
        res = json.loads(rp.read_text()) if rp.exists() else {'errors': {'worker': 'no result file (tree failed to run)'}}
        preps[tid], results[tid] = prep, res
        recs.append(assess(tid, heights[tid], prep, res))
    # Outliers (data request item 4): flag only.
    outliers = []
    areas = sorted(r['crown_area']['v'] for r in recs if r['crown_area']['v'])
    lo, hi = (statistics.quantiles(areas, n=20)[0], statistics.quantiles(areas, n=20)[-1]) if len(areas) > 20 else (None, None)
    for r in recs:
        tid, H, D = r['tree'], r['height']['v'], r['dbh']['v']
        if H and D:
            sl = H / (D / 100)
            if sl > 150 or sl < 20:
                outliers.append(dict(tree_id=tid, reason='implausible height-to-DBH ratio', values=f'H/D = {sl:.0f} (height {H:.2f} m, DBH {D:.2f} cm)'))
                r['dbh'] = metric(D, 'REVIEW', (r['dbh']['why'] + '; ' if r['dbh']['why'] else '') + f'height/DBH ratio {sl:.0f} outside 20-150')
        if r['dbh']['s'] == 'N/A':
            outliers.append(dict(tree_id=tid, reason='failed or missing DBH fit', values=r['dbh']['why']))
        a = r['crown_area']['v']
        if a and lo is not None and (a < lo or a > hi):
            outliers.append(dict(tree_id=tid, reason='very small crown' if a < lo else 'very large crown', values=f'crown area {a:.2f} m2 (5th-95th percentile {lo:.2f}-{hi:.2f})'))
            note = ('very small' if a < lo else 'very large') + ' crown (outside 5th-95th percentile of crown areas); check ownership/completeness'
            for k in ('crown_area', 'crown_volume'):
                if r[k]['s'] in ('VALID', 'REVIEW'):
                    r[k] = metric(r[k]['v'], 'REVIEW', (r[k]['why'] + '; ' if r[k]['why'] else '') + note)
            for k, src in (('crown_diameter', 'crown area'), ('point_density', 'crown volume')):
                if r[k]['s'] == 'VALID':
                    r[k] = metric(r[k]['v'], 'REVIEW', f'follows {src} status')
        sc = preps[tid].get('stem_completeness')
        if sc is not None and sc < 0.5:
            outliers.append(dict(tree_id=tid, reason='very low stem completeness', values=f'{sc:.2f}'))
        if preps[tid].get('flag_crown_touches_edge'):
            outliers.append(dict(tree_id=tid, reason='crown touching the ROI edge', values=f'min distance {preps[tid]["crown_min_dist_to_roi_edge_m"]:.2f} m'))
    # ---------------- Workbook ----------------
    def cell(m, fmt):
        if m['s'] in ('VALID', 'REVIEW') and m['v'] is not None:
            return (m['v'], dict(fill=COL[m['s']], fmt=fmt))
        return ('N/A' if m['s'] == 'N/A' else m['s'], dict(fill=COL[m['s']]))

    def st(m):
        return (m['s'], dict(fill=COL[m['s']]))

    head = ['Tree', 'Tree processing status', 'Original V2 file', 'Review file', 'ROI', 'Points', 'Segmentation status',
            'Inherited QC status', 'Human approval',
            'Height ITSMe (m)', 'Height status', 'Height note', 'Height supported top (m)', 'Height 99th percentile (m)',
            'DBH (cm)', 'DBH status', 'Estimated DBH (cm)', 'Unaccepted DBH fit (cm)', 'DBH note', 'DBH method',
            'Points in 6 cm DBH slice', 'DBH circle fit RMSE (cm)', 'DBH arc coverage', 'DBH fit OK', 'Stem lean (deg)',
            'Area-equivalent DBH (cm)',
            'Crown base height (m)', 'Crown base status', 'Crown base source', 'Crown projected area (m2)', 'Crown area status',
            'Crown envelope volume (m3)', 'Crown volume status', 'Crown note', 'Crown length (m)', 'Crown ratio',
            'Equivalent crown diameter (m)', 'Envelope / 1 m slab ratio', 'Crown point density (points/m3)', 'Crown method',
            'Stem X (m)', 'Stem Y (m)', 'Stem position source', 'CRS', 'Ground Z (m)', 'Ground source',
            'Distance to ROI edge (m)', 'Stem completeness (0-1)', 'Stem clusters at 1.3 m', 'Fork near DBH',
            'Leaning stem (>=10 deg)', 'Truncated top', 'Crown touches ROI edge', 'Neighbour contact (inherited)',
            'Stem axis source', 'Reference: automatic ITSMe crown area (m2)', 'Reference: automatic ITSMe crown envelope (m3)',
            'Reference: automatic crown start (m)', 'Source SHA-256']
    table = [[(h_, HEADER) for h_ in head]]
    attrs = []
    for r in recs:
        tid, h, p, res = r['tree'], heights[r['tree']], preps[r['tree']], results[r['tree']]
        tstat = r['tree_status']
        tfill = COL['VALID'] if tstat == 'SUCCESS' and r['all_core_valid'] else COL['REVIEW'] if tstat != 'FAILED' else COL['N/A']
        crown_note = '; '.join(x for x in [r['crown_area']['why'], r['crown_volume']['why'] if r['crown_volume']['why'] != r['crown_area']['why'] else ''] if x)
        lean = r['lean']
        table.append([
            tid, (tstat, dict(fill=tfill)), h['original_v2_filename'], h['review_ply_filename'], roi['roi_id'], p['point_count'],
            ('NA', dict(fill=COL['UNKNOWN'])), h['current_qc_status'], h['human_approval'],
            cell(r['height'], '0.000'), st(r['height']), r['height']['why'], (p['supported_height_m'], dict(fmt='0.000')), (p['height_p99_m'], dict(fmt='0.000')),
            cell(r['dbh'], '0.00'), st(r['dbh']), None,
            (r['dbh_unaccepted_cm'], dict(fill=COL['REVIEW'], fmt='0.00')) if r['dbh_unaccepted_cm'] is not None else None,
            r['dbh']['why'], r['dbh_method'], r['dbh_points'], (r['dbh_rmse_cm'], dict(fmt='0.00')), (r['dbh_arc'], dict(fmt='0.00')),
            r['dbh_fit_ok'], (lean, dict(fmt='0.0')) if lean is not None else ('UNKNOWN', dict(fill=COL['UNKNOWN'])),
            (r['area_eq_cm'], dict(fill=COL['VALID'], fmt='0.00')) if r['area_eq_cm'] else None,
            cell(r['crown_base'], '0.00'), st(r['crown_base']), p.get('crown_base_source') or (p.get('crown_base_failure') or p.get('rule_failure') or ''),
            cell(r['crown_area'], '0.00'), st(r['crown_area']), cell(r['crown_volume'], '0.0'), st(r['crown_volume']), crown_note,
            cell(r['crown_length'], '0.00'), cell(r['crown_ratio'], '0.00'), cell(r['crown_diameter'], '0.00'),
            (r['slab_ratio'], dict(fmt='0.00')), cell(r['point_density'], '0.0'), r['crown_method'],
            (p['stem_xy'][0], dict(fmt='0.000')), (p['stem_xy'][1], dict(fmt='0.000')), p['stem_xy_source'],
            'EPSG:32756 (project records; not re-verified)', (p['translation'][2], dict(fmt='0.000')), p['ground_source'],
            (p['dist_to_roi_edge_m'], dict(fmt='0.00')),
            (p['stem_completeness'], dict(fmt='0.00')) if p.get('stem_completeness') is not None else ('UNKNOWN', dict(fill=COL['UNKNOWN'])),
            p['n_stems_at_1_3m'], p['flag_fork_near_dbh'],
            r['flag_lean'] if r['flag_lean'] is not None else ('UNKNOWN', dict(fill=COL['UNKNOWN'])),
            r['flag_truncated_top'], p['flag_crown_touches_edge'] if p['flag_crown_touches_edge'] is not None else ('UNKNOWN', dict(fill=COL['UNKNOWN'])),
            h['possible_neighbouring_tree_contamination'], p.get('axis_source') or ('none: ' + (p.get('axis_failure') or '')),
            (r['auto'][0], dict(fmt='0.00')), (r['auto'][1], dict(fmt='0.0')), (r['auto'][2], dict(fmt='0.00')), p['review_sha256']])
        attrs.append(dict(
            tree_id=tid, roi_id=roi['roi_id'], source_file=h['review_ply_filename'], n_points=p['point_count'], status='NA',
            stem_x=p['stem_xy'][0], stem_y=p['stem_xy'][1], stem_xy_source=p['stem_xy_source'], crs='EPSG:32756',
            ground_z=p['translation'][2], ground_source=p['ground_source'],
            height_m=r['height']['v'] if r['height']['s'] != 'N/A' else 'NA', height_status=r['height']['s'],
            dbh_cm=r['dbh']['v'] if r['dbh']['v'] is not None else 'NA', dbh_status=r['dbh']['s'],
            dbh_n_points=r['dbh_points'] if r['dbh_points'] is not None else 'NA',
            dbh_fit_residual=r['dbh_rmse_cm'] if r['dbh_rmse_cm'] is not None else 'NA', dbh_fit_ok=str(r['dbh_fit_ok']).upper(),
            crown_volume_m3=r['crown_volume']['v'] if r['crown_volume']['v'] is not None else 'NA', crown_volume_status=r['crown_volume']['s'],
            crown_area_m2=r['crown_area']['v'] if r['crown_area']['v'] is not None else 'NA', crown_area_status=r['crown_area']['s'],
            crown_base_height_m=r['crown_base']['v'] if r['crown_base']['v'] is not None else 'NA',
            n_stems_at_1_3m=p['n_stems_at_1_3m'], flag_fork_near_dbh=str(p['flag_fork_near_dbh']).upper(),
            flag_lean='NA' if r['flag_lean'] is None else str(r['flag_lean']).upper(), flag_truncated_top=str(r['flag_truncated_top']).upper(),
            dist_to_roi_edge_m=p['dist_to_roi_edge_m'],
            flag_crown_touches_edge='NA' if p['flag_crown_touches_edge'] is None else str(p['flag_crown_touches_edge']).upper(),
            stem_completeness=p['stem_completeness'] if p.get('stem_completeness') is not None else 'NA',
            point_density=r['point_density']['v'] if r['point_density']['v'] is not None else 'NA',
            notes=' | '.join(x for x in [r['height']['why'], r['dbh']['why'], crown_note] if x)))
    # Summary statistics
    METRICS = [('Tree height (m)', 'height', '0.000'), ('DBH (cm)', 'dbh', '0.00'), ('Crown base height (m)', 'crown_base', '0.00'),
               ('Crown projected area (m2)', 'crown_area', '0.00'), ('Crown envelope volume (m3)', 'crown_volume', '0.0'),
               ('Crown length (m)', 'crown_length', '0.00'), ('Crown ratio', 'crown_ratio', '0.00'),
               ('Equivalent crown diameter (m)', 'crown_diameter', '0.00'), ('Crown point density (points/m3)', 'point_density', '0.0')]
    summ = [[('Summary statistics: all 163 trees', TITLE)],
            ['Primary statistics use VALID values only. REVIEW values are summarised separately below; N/A and UNKNOWN are never included. No estimates exist.'],
            [],
            [(x, HEADER) for x in ['Metric', 'VALID n', 'Mean', 'Median', 'SD', 'Min', 'Max', 'P25', 'P75', 'ESTIMATED n', 'N/A n', 'REVIEW n', 'UNKNOWN n', 'Total trees']]]
    summary_json = {}
    for label, k, fmt in METRICS:
        valid = [r[k]['v'] for r in recs if r[k]['s'] == 'VALID']
        s = stats(valid)
        counts = {c: sum(r[k]['s'] == c for r in recs) for c in COL}
        summary_json[k] = dict(valid=s, counts=counts)
        summ.append([label, (s['n'], dict(fill=COL['VALID']))] + [(s.get(x), dict(fmt=fmt)) for x in ('mean', 'median', 'sd', 'min', 'max', 'p25', 'p75')]
                    + [(counts['ESTIMATED'], dict(fill=COL['ESTIMATED'])), (counts['N/A'], dict(fill=COL['N/A'])),
                       (counts['REVIEW'], dict(fill=COL['REVIEW'])), (counts['UNKNOWN'], dict(fill=COL['UNKNOWN'])), len(recs)])
    summ += [[], [('VALID + REVIEW values together (all available values, for sensitivity only; not the primary result)', dict(bold=True))],
             [(x, HEADER) for x in ['Metric', 'n', 'Mean', 'Median', 'SD', 'Min', 'Max', 'P25', 'P75']]]
    for label, k, fmt in METRICS:
        s = stats([r[k]['v'] for r in recs if r[k]['s'] in ('VALID', 'REVIEW')])
        summary_json[k]['valid_plus_review'] = s
        summ.append([label, s['n']] + [(s.get(x), dict(fmt=fmt)) for x in ('mean', 'median', 'sd', 'min', 'max', 'p25', 'p75')])
    ts = {x: sum(r['tree_status'] == x for r in recs) for x in ('SUCCESS', 'PARTIAL SUCCESS', 'FAILED')}
    summ += [[], [('Tree processing status', dict(bold=True))], [(x, HEADER) for x in ['Status', 'Trees', 'Meaning']],
             ['SUCCESS', ts['SUCCESS'], 'height, DBH, crown area and crown volume all have a value (VALID or REVIEW)'],
             ['  of which all four VALID', sum(r['all_core_valid'] for r in recs), 'no open concern on any core metric'],
             ['PARTIAL SUCCESS', ts['PARTIAL SUCCESS'], 'at least one core metric is N/A'],
             ['FAILED', ts['FAILED'], 'no core metric could be obtained'], ['Total', len(recs), ''],
             [], [('Colour legend', dict(bold=True))]] + [[(k, dict(fill=v)), d] for (k, v), d in zip(COL.items(), [
                 'Successfully calculated and considered reliable', 'Approximate value from a documented method (none in this dataset)',
                 'Could not be obtained reliably (reason in the note columns)', 'Value exists but needs a human check (reason given)',
                 'Insufficient information to decide'])]
    # Quality control sheet
    qc = [[('Quality control: every non-VALID measurement and every outlier flag', TITLE)], [],
          [(x, HEADER) for x in ['Tree', 'Metric', 'Status', 'Value', 'Reason', 'Action needed']]]
    for r in recs:
        for label, k, fmt in METRICS[:5]:
            m = r[k]
            if m['s'] != 'VALID':
                qc.append([r['tree'], label, (m['s'], dict(fill=COL[m['s']])), (m['v'], dict(fmt=fmt)) if m['v'] is not None else None, m['why'],
                           'verify visually before use' if m['s'] == 'REVIEW' else 'none possible from current data; keep N/A'])
    for o in outliers:
        qc.append([o['tree_id'], 'outlier flag', ('REVIEW', dict(fill=COL['REVIEW'])), None, o['reason'] + ': ' + o['values'], 'check manually; nothing was removed'])
    # Earlier-results consistency (20 trees)
    earlier = json.loads((AGREED_20 / 'outputs/measurements_table.json').read_text())
    ecol = {hh: i for i, hh in enumerate(earlier['header'])}
    byid = {r['tree']: r for r in recs}
    cons = [[('Consistency with the earlier 20-tree results (CROWN_BASE_RERUN_20261023_191046)', TITLE)], [],
            [(x, HEADER) for x in ['Tree', 'Height earlier (m)', 'Height now (m)', 'Diff', 'Accepted DBH earlier (cm)', 'DBH now (cm)', 'Diff',
                                    'Crown area earlier (m2)', 'Crown area now (m2)', 'Diff', 'Envelope earlier (m3)', 'Envelope now (m3)', 'Diff', 'Explanation']]]
    max_diff = 0.0
    for er in earlier['rows']:
        tid = er[ecol['Tree']]
        if tid not in byid:   # subset test runs
            continue
        pairs = [(f(er[ecol['Height (m)']]), f(results[tid].get('itsme_height_m'))),
                 (f(er[ecol['Accepted DBH (cm)']]), 100 * f(results[tid]['dbh_m']) if f(results[tid].get('dbh_m')) else None),
                 (f(er[ecol['Crown area (m²)']]), f((results[tid].get('crown') or {}).get('area_m2'))),
                 (f(er[ecol['Crown envelope (m³)']]), f((results[tid].get('crown') or {}).get('volume_m3')))]
        row = [tid]
        for a_, b_ in pairs:
            d = (b_ - a_) if a_ is not None and b_ is not None else None
            if d is not None:
                max_diff = max(max_diff, abs(d))
            row += [a_, b_, (d, dict(fmt='0.000000'))]
        row.append('identical inputs and methods' if all((a_ is None) == (b_ is None) and (a_ is None or abs(b_ - a_) < 1e-6) for a_, b_ in pairs)
                   else 'differs: see values')
        cons.append(row)
    # Changes against a previous all-163 version (optional)
    changes, change_rows, unexpected = None, [], []
    if args.previous:
        prev = {r['tree']: r for r in json.loads((Path(args.previous) / 'logs/records.json').read_text())}
        choice_trees = {r['tree'] for r in C.rows(MP / 'results/CROWN_BASE_REVIEW_ALL163_20261023_194703/user_crown_choices.csv')}
        crown_keys = {'crown_base', 'crown_area', 'crown_volume', 'crown_length', 'crown_ratio', 'crown_diameter', 'point_density'}
        changes = [[('Changes against ' + Path(args.previous).name, TITLE)], [],
                   [(x, HEADER) for x in ['Tree', 'Metric', 'Previous value', 'Previous status', 'New value', 'New status', 'Type of change', 'New reason']]]
        for r in recs:
            p0 = prev.get(r['tree'])
            for k in ('height', 'dbh') + tuple(sorted(crown_keys)):
                a_, b_ = p0[k], r[k]
                same_v = (a_['v'] is None and b_['v'] is None) or (a_['v'] is not None and b_['v'] is not None and abs(a_['v'] - b_['v']) < 1e-9)
                if not same_v or a_['s'] != b_['s']:
                    # A measured value may change only for user-reviewed crowns; status-only changes (new QC rules) are listed.
                    ok = same_v or (r['tree'] in choice_trees and k in crown_keys)
                    change_rows.append(r['tree'])
                    if not ok:
                        unexpected.append((r['tree'], k))
                    changes.append([r['tree'], k, a_['v'], (a_['s'], dict(fill=COL[a_['s']])), b_['v'], (b_['s'], dict(fill=COL[b_['s']])),
                                    'status only (value identical)' if same_v else ('value changed: user-reviewed crown' if ok else 'NO - unexpected value change'),
                                    b_['why']])
    # Methodology & metadata
    meth = methods(out, env, timing, prep_log, roi)
    mrows = [[('Methodology & metadata', TITLE)], []]
    for sec, items in meth.items():
        mrows.append([(sec, dict(bold=True, fill='DDEBF7'))])
        for k, v in (items.items() if isinstance(items, dict) else enumerate(items)):
            mrows.append([str(k), json.dumps(v) if isinstance(v, (dict, list)) else v])
        mrows.append([])
    mrows += [[('Colour legend', dict(bold=True, fill='DDEBF7'))]] + [[(k, dict(fill=v)), '#' + v] for k, v in COL.items()]
    # DBH slices and run details
    sl = [[(x, HEADER) for x in ['tree', 'height_m', 'diameter_cm', 'fdiameter_cm', 'arc', 'rmse_mm', 'points', 'accepted']]]
    run = [[(x, HEADER) for x in ['Tree', 'Prepare seconds', 'Measure seconds', 'Peak R memory (MB)', 'Worker PID', 'Prep reused', 'Warnings', 'Stage errors', 'Local XYZ SHA-256']]]
    for m in man:
        tid, res = m['tree'], results[m['tree']]
        for s in res.get('slices') or []:
            sl.append([tid, s['height_m'], 100 * f(s['diameter_m']) if f(s['diameter_m']) else None, 100 * f(s['fdiameter_m']) if f(s['fdiameter_m']) else None,
                       s['arc'], 1000 * f(s['rmse_m']) if f(s['rmse_m']) else None, s['points'], s['accepted']])
        run.append([tid, round(preps[tid]['prep_seconds'], 2), round(f(res.get('seconds')) or 0, 2), f(res.get('r_peak_memory_mb')), res.get('pid'), m['reused'],
                    len(res.get('warnings') or []), json.dumps(res.get('errors') or {}), preps[tid]['local_xyz_sha256']])
    xlsx = out / 'ITSMe_all163_results.xlsx'
    if xlsx.exists():
        xlsx.rename(out / f'ITSMe_all163_results_previous_{time.strftime("%Y%m%d_%H%M%S")}.xlsx')
    widths_main = [10, 15, 30, 24, 20, 9, 11, 13, 10, 10, 9, 45, 10, 10, 9, 9, 10, 11, 60, 26, 9, 9, 9, 8, 9, 11, 10, 9, 30, 11, 9, 11, 9, 60,
                   9, 8, 10, 9, 10, 30, 13, 13, 22, 14, 10, 30, 10, 10, 9, 8, 9, 9, 9, 22, 34, 12, 12, 12, 18]
    write_xlsx(xlsx, [
        dict(name='All Tree Results', rows=table, freeze=(1, 1), widths=widths_main, filter_row=1),
        dict(name='Summary Statistics', rows=summ, freeze=None, widths=[34, 9, 10, 10, 10, 10, 10, 10, 10, 11, 8, 9, 10, 10]),
        dict(name='Quality Control', rows=qc, freeze=(0, 3), widths=[10, 26, 10, 10, 90, 34], filter_row=3),
        dict(name='Methodology & Metadata', rows=mrows, freeze=None, widths=[34, 140]),
        dict(name='Check vs 20-tree results', rows=cons, freeze=(0, 3), widths=[10] + [11] * 12 + [28]),
        dict(name='DBH lean-corrected slices', rows=sl, freeze=(0, 1), widths=[10, 9, 11, 11, 7, 9, 7, 9]),
        dict(name='Run details', rows=run, freeze=(1, 1), widths=[10, 10, 10, 11, 10, 9, 9, 60, 66])]
        + ([dict(name='Changes vs previous version', rows=changes, freeze=(0, 3), widths=[10, 16, 14, 12, 14, 12, 30, 90], filter_row=3)] if changes else []))
    # Data-request files
    res_dir = out / 'results'
    res_dir.mkdir(exist_ok=True)
    with (res_dir / 'tree_attributes.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(attrs[0]))
        w.writeheader()
        w.writerows(attrs)
    with (res_dir / 'outliers.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['tree_id', 'reason', 'values'])
        w.writeheader()
        w.writerows(outliers)
    (res_dir / 'methods.json').write_text(json.dumps(meth, indent=1), encoding='utf-8')
    counts_all = {k: {c: sum(r[k]['s'] == c for r in recs) for c in COL} for _, k, _ in METRICS}
    summary = dict(roi=dict(count=1, **roi), trees_refined=len(recs), segmentation_status_counts='NA (no accepted/uncertain/discarded records for CloudCompare_review_v2; all human approvals PENDING)',
                   tree_status=ts, trees_all_core_valid=sum(r['all_core_valid'] for r in recs),
                   dbh_fit_ok_false=sum(not r['dbh_fit_ok'] for r in recs),
                   edge_affected_trees=sum(bool(preps[r['tree']].get('flag_crown_touches_edge')) for r in recs),
                   metric_status_counts=counts_all, statistics=summary_json,
                   run_time=dict(prepare_seconds=timing.get('prep_seconds'), measure_seconds=timing.get('measure_seconds'),
                                 per_tree_measure_seconds=stats([f(results[t].get('seconds')) for t in results if f(results[t].get('seconds'))]),
                                 workers=timing.get('workers'), machine=env.get('python', {}), physical_cores=timing.get('physical_cores'),
                                 free_ram_gb_at_start=timing.get('free_ram_gb')),
                   points_before_after_downsampling='NA (not recorded)', rayextract_segments='NA (not recorded in this batch)')
    (res_dir / 'summary.json').write_text(json.dumps(summary, indent=1, default=str), encoding='utf-8')
    # ---------------- Validation ----------------
    v = validate(out, xlsx, recs, man, snap, heights, summary_json, max_diff)
    if args.previous:
        v['checks']['values_changed_only_for_user_reviewed_crowns'] = not unexpected
        v['changed_trees'] = sorted(set(change_rows))
        v['unexpected_changes'] = unexpected
        v['all_checks_passed'] = all(v['checks'].values())
    (out / 'logs/validation.json').write_text(json.dumps(v, indent=1, default=str), encoding='utf-8')
    (out / 'logs/records.json').write_text(json.dumps(recs, indent=0, default=str), encoding='utf-8')
    print(json.dumps(dict(trees=len(recs), tree_status=ts, metric_status_counts=counts_all, outliers=len(outliers),
                          max_diff_vs_20_tree=max_diff, all_checks_passed=v['all_checks_passed'], seconds=round(time.time() - t0, 1)), indent=1))


def methods(out, env, timing, prep_log, roi):
    return {
        'Input data': dict(source_clouds='CloudCompare_review_v2 (163 PLYs, read only); hashes verified against session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv',
                           stable_id_mapping='tree_NNN = original export NNN-1 (all_tree_preliminary_heights.csv)', roi=roi,
                           crs='EPSG:32756 according to project records; global coordinates unchanged (not re-verified here)',
                           downsampling='Source clouds are the 3 cm raycloud product (median lower-stem point spacing ~31 mm); no further resampling',
                           rayextract_parameters='NA: not found in this batch (see segmentation records)'),
        'Software': dict(R_and_packages=env.get('R'), ITSMe=env.get('ITSMe'), geometry=env.get('geometry'), python=env.get('python'),
                         scripts=['measurement_pipeline/scripts/prepare_all163.py', 'all163_common.py', 'all163_tree_worker.R',
                                  'crown_volume_metrics.R (unchanged)', 'all163_postprocess.py', 'xlsx_styled.py'],
                         git='NA: project is not a git repository',
                         script_sha256={p.name: C.sha(p) for p in sorted((MP / 'scripts').glob('*'))
                                        if p.is_file() and p.name.startswith(('all163_', 'prepare_all163', 'xlsx_', 'crown_volume_metrics', 'run_all163', 'build_all163', 'verify_all163'))}),
        'Height': dict(definition='ITSMe tree_height_pc: highest point of the full cloud minus the foot-ground reference (vertical, m)',
                       ground_reference='Actual terrain-mesh triangle at the stem foot (axis meets mesh); fallback trees use the lowest-observation XY; 103/108 use the user-agreed corrected base',
                       also_reported='locally supported top (prepare_crown_volume_top20 rule) and 99th-percentile height',
                       VALID='finite, ground LOCALLY_SUPPORTED, robust foot, top LOCALLY_SUPPORTED_OBSERVED_TIP, highest point within 0.5 m of supported top, no visual exclusion'),
        'DBH': dict(location='1.3 m along the fitted low-stem axis above the foot ground (lean-corrected: cloud rotated so the axis is vertical)',
                    slice='6 cm (ITSMe dbh_pc, thresholdR2 0.001, functional, concavity 4); crop = bark radius (mode of distances 1.0-1.6 m) + 10 cm',
                    fallback='median of accepted 6 cm slices at 1.1-1.5 m when the 1.3 m fit fails (labelled; REVIEW)',
                    quality_rule='diameter 3-200 cm, arc coverage >= 0.60, RMSE <= min(4 cm, max(1 cm, 10% of diameter)) (unchanged)',
                    residual='RMSE of the 1.3 m circle fit = sqrt(ITSMe R2 output), cm',
                    exceptions='067: outer-outline filter (points >3 cm inside the trunk outline set aside, in memory); 103: oval trunk, area-equivalent diameter sqrt(ellipse major x minor) also reported; 033 not released; 108 provisional only (user decisions 23 Oct 2026)',
                    axis='saved hash-matched checkpoint axis; trees without one get one attempt with the original low-stem helper; failure -> DBH N/A',
                    unaccepted='raw 1.3 m circle fits that fail the screen are kept in a separate column, never in the DBH column'),
        'Crown': dict(crown_base_rule='continuous-crown rule agreed 23 Oct 2026: 0.25 m layers, r95 spread smoothed over 0.75 m; crown layer if wider than max(3 x narrowest trunk spread between 1 m and 60% height, 0.3 x widest layer); base = lowest crown layer above 1 m from which >= 70% of layers to the top are crown',
                      user_choices_20_trees='048 8.25, 056 4.25, 151 3.00, 076 5.00, 146 8.50, 118 10.75 m; other 14 of the 20 trees use the rule (user-reviewed)',
                      crown_points='ITSMe classify_crown_pc (thresholdbranch 1.5) crown points with Z >= crown base; if ITSMe returns no crown: all tree points above the base (distinct label, REVIEW)',
                      area='ITSMe projected_area_pc, concave hull concavity 3, m2', volume='3D convex hull (geometry::convhulln) of the crown points, m3; includes internal air gaps; not wood volume or biomass',
                      gap_screen='envelope / sum of 1 m slab hulls; > 2 -> REVIEW',
                      derived='crown length = height - crown base; crown ratio = length / height; equivalent crown diameter = 2 sqrt(area / pi); point density = crown points / envelope volume'),
        'Structure indicators': dict(stem_clusters='connected components (link 0.10 m, >= 8 points) of points within 1 m of the stem axis in a 10 cm layer at 1.3 m; indicator of extra stems, branches or understorey',
                                     fork_near_dbh='more clusters at 1.6 m than at 1.0 m and at least 2 at 1.6 m', lean='stem axis lean >= 10 degrees',
                                     truncated_top='inherited tree_top_reliability REVIEW_REQUIRED or TOP_OR_BOUNDARY_REVIEW flag',
                                     roi_edge='distance from stem position to the ROI bounding box; crown touches edge if any point above the crown base is within 0.10 m of it',
                                     stem_completeness='fraction of 0.5 m slices from ground to crown base with any point within 0.5 m of the stem axis'),
        'Status rules': dict(VALID='calculated and reliable under the stated rule', REVIEW='value exists but a documented concern needs checking',
                             **{'N/A': 'no reliable value; reason given'}, UNKNOWN='insufficient information', ESTIMATED='not used (REPORT_DATA_REQUEST.md rule 1: never estimate)',
                             segmentation_status='NA for all trees: no accepted/uncertain/discarded records exist for the current 163 clouds',
                             not_checked='branch ownership between neighbouring trees is not verified for any tree; 140 trees carry the inherited proximity-contact flag'),
        'Parallel processing': dict(preparation=f"Python ProcessPoolExecutor, {prep_log.get('workers')} workers, largest clouds first",
                                    measurement=f"R PSOCK cluster, {timing.get('workers')} workers (physical cores {timing.get('physical_cores')}, free RAM {round(timing.get('free_ram_gb') or 0)} GB, {timing.get('ram_per_worker_gb')} GB per worker), load-balanced, largest clouds first, BLAS/OpenMP threads = 1",
                                    checkpoints='per_tree/tree_NNN/prep.json and result.json; reused only when source hash, preparation settings and worker code hash match',
                                    retries='failed trees retried once', seconds=dict(prepare=timing.get('prep_seconds'), measure=timing.get('measure_seconds'))),
        'Sensitivity (results/sensitivity.csv)': dict(trees='146, 151, 063, 093, 069, 118, 084, 103 (accepted DBH; small to large; simple and neighbour-contact crowns)',
                                                      dbh='ITSMe diameter_slice_pc at 1.3 m along the stem, slice 3/5/6/10 cm, circle diameter and functional hull fdiameter',
                                                      height='highest point vs 99th percentile of point heights', crown='single convex envelope vs sum of 1 m and 0.5 m slab envelopes',
                                                      note='direct slice fit can differ from the dbh_pc wrapper (tree_103: 69.1 vs 66.6 cm); the reported DBH uses the wrapper as in the 20-tree notebook'),
        'Not obtained': ['figures (separate task)', 'before_after.csv: unedited Rayextract output not kept (manual_seg_v2 is already a manually cleaned baseline)',
                         'Rayextract parameters: not recorded in any project file', 'field inventory: no inventory spreadsheet found on the drive',
                         'segmentation accuracy, field validation, biomass (need reference data / out of scope)'],
    }


def validate(out, xlsx, recs, man, snap, heights, summary_json, max_diff):
    from xlsx_writer import read_xlsx_rows
    ids = [r['tree'] for r in recs]
    expected = sorted(heights)
    wb = read_xlsx_rows(xlsx)
    main = wb['All Tree Results']
    head = main[0]
    ix = {h: i for i, h in enumerate(head)}
    checks = {}
    checks['163_ids_once'] = sorted(ids) == expected and len(set(ids)) == 163 and len(main) == 164
    checks['every_tree_has_status'] = all(r['tree_status'] in ('SUCCESS', 'PARTIAL SUCCESS', 'FAILED') for r in recs)
    preps = {m['tree']: json.loads((out / 'per_tree' / m['tree'] / 'prep.json').read_text()) for m in man}
    results_hash = {m['tree']: json.loads((out / 'per_tree' / m['tree'] / 'result.json').read_text()).get('review_sha256') for m in man}
    checks['source_hashes_match_snapshot'] = all(preps[t]['review_sha256'] == snap[heights[t]['review_ply_filename']] for t in ids)
    checks['results_computed_on_current_source'] = all(results_hash[t] == preps[t]['review_sha256'] for t in ids)
    checks['id_mapping_consistent'] = (all(heights[t]['review_ply_filename'].startswith(t + '_')
                                           and f'segmented_{int(t[5:]) - 1} - Cloud' in heights[t]['original_v2_filename'] for t in ids)
                                       and [row[0] for row in main[1:]] == expected
                                       and [row[ix['Source SHA-256']] for row in main[1:]] == [preps[t]['review_sha256'] for t in expected])
    rng = {'Height ITSMe (m)': (1, 60), 'DBH (cm)': (3, 200), 'Crown projected area (m2)': (0.01, 1000), 'Crown envelope volume (m3)': (0.01, 20000)}
    bad = []
    for row in main[1:]:
        for col, (lo, hi) in rng.items():
            val = row[ix[col]]
            if isinstance(val, float) and not lo <= val <= hi:
                bad.append((row[0], col, val))
            if val == 0:
                bad.append((row[0], col, 'zero'))
    checks['values_in_plausible_ranges_no_zero_for_missing'] = not bad
    checks['estimated_column_empty'] = all(row[ix['Estimated DBH (cm)']] in (None, '') for row in main[1:])
    checks['unaccepted_fits_not_in_dbh_column'] = all(not (isinstance(row[ix['Unaccepted DBH fit (cm)']], float) and isinstance(row[ix['DBH (cm)']], float)) for row in main[1:])
    na_ok = True
    for row in main[1:]:
        for vcol, scol in [('Height ITSMe (m)', 'Height status'), ('DBH (cm)', 'DBH status'), ('Crown projected area (m2)', 'Crown area status'), ('Crown envelope volume (m3)', 'Crown volume status')]:
            if (row[ix[scol]] in ('VALID', 'REVIEW')) != isinstance(row[ix[vcol]], float):
                na_ok = False
    checks['status_matches_value_presence'] = na_ok
    # Colours: every status cell carries its status colour
    fills_ok = colour_check(xlsx, ix, len(main))
    checks['colour_coding_consistent'] = fills_ok
    valid_heights = [row[ix['Height ITSMe (m)']] for row in main[1:] if row[ix['Height status']] == 'VALID']
    checks['summary_uses_valid_only'] = abs(statistics.fmean(valid_heights) - summary_json['height']['valid']['mean']) < 1e-9 if valid_heights else True
    checks['20_tree_results_reproduced'] = max_diff < 1e-6
    # Recompute primary statistics from the exported sheet (VALID cells only)
    col_for = {'height': ('Height ITSMe (m)', 'Height status'), 'dbh': ('DBH (cm)', 'DBH status'),
               'crown_base': ('Crown base height (m)', 'Crown base status'), 'crown_area': ('Crown projected area (m2)', 'Crown area status'),
               'crown_volume': ('Crown envelope volume (m3)', 'Crown volume status')}
    stat_ok = True
    for k, (vc, sc) in col_for.items():
        vals = [row[ix[vc]] for row in main[1:] if row[ix[sc]] == 'VALID']
        s_ = summary_json[k]['valid']
        if len(vals) != s_['n'] or (vals and (abs(statistics.median(vals) - s_['median']) > 1e-9 or abs(max(vals) - s_['max']) > 1e-9
                                              or abs(statistics.fmean(vals) - s_['mean']) > 1e-9)):
            stat_ok = False
    checks['summary_statistics_recomputed_from_sheet'] = stat_ok
    contra = []
    for row in main[1:]:
        hb, cb, cl, cr = row[ix['Height ITSMe (m)']], row[ix['Crown base height (m)']], row[ix['Crown length (m)']], row[ix['Crown ratio']]
        if isinstance(hb, float) and isinstance(cb, float) and cb >= hb:
            contra.append((row[0], 'crown base >= height'))
        if isinstance(cl, float) and cl <= 0:
            contra.append((row[0], 'crown length <= 0'))
        if isinstance(cr, float) and not 0 < cr < 1:
            contra.append((row[0], 'crown ratio outside 0-1'))
    checks['no_contradictory_values'] = not contra
    return dict(checks=checks, all_checks_passed=all(checks.values()), out_of_range=bad, contradictions=contra, max_diff_vs_20_tree=max_diff)


def colour_check(xlsx, ix, nrows):
    import re
    with zipfile.ZipFile(xlsx) as z:
        styles = z.read('xl/styles.xml').decode()
        sheet = z.read('xl/worksheets/sheet1.xml').decode()
    fills = re.findall(r'<fill>(.*?)</fill>', styles)
    fill_rgb = [re.search(r'rgb="FF([0-9A-F]{6})"', x).group(1) if 'rgb=' in x else None for x in fills]
    xfs = re.findall(r'<xf numFmtId="\d+" fontId="\d+" fillId="(\d+)"', styles.split('<cellXfs')[1])
    cells = dict(re.findall(r'<c r="([A-Z]+\d+)" s="(\d+)"', sheet))
    values = dict(re.findall(r'<c r="([A-Z]+\d+)"[^>]*t="inlineStr"><is><t xml:space="preserve">([^<]*)</t>', sheet))

    def col(n):
        s = ''
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s
    pairs = [('Height ITSMe (m)', 'Height status'), ('DBH (cm)', 'DBH status'), ('Crown projected area (m2)', 'Crown area status'),
             ('Crown envelope volume (m3)', 'Crown volume status'), ('Crown base height (m)', 'Crown base status')]
    for vname, sname in pairs:
        vc, sc = col(ix[vname] + 1), col(ix[sname] + 1)
        for r in range(2, nrows + 1):
            status = values.get(f'{sc}{r}')
            for c in (sc, vc):   # the status cell and its value cell both carry the status colour
                if fill_rgb[int(xfs[int(cells.get(f'{c}{r}', 0))])] != COL.get(status):
                    return False
    return True


if __name__ == '__main__':
    main()
