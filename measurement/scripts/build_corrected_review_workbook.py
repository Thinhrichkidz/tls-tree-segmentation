"""New versioned review workbook: 16 unchanged trees from the 20-tree batch + 4 cleaned trees from the corrected rerun.

Earlier workbooks are not opened for writing. Every value is read from saved result files; nothing is recomputed here.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx_writer import write_xlsx

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
args = parser.parse_args()
mp = Path(__file__).resolve().parents[1]
root = mp.parent
config = json.loads(Path(args.config).read_text())
batch = Path(config['batch'])
TOP20 = mp / 'results/CROWN_VOLUME_TOP20_20261023_164430'
DIAG = mp / 'results/CLEANED_TRUNK_DIAGNOSIS_20261023_185259'

def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def num(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None

old = {r['stable_tree_id']: r for r in rows(TOP20 / 'all_20_tree_results.csv')}
order = [r['stable_tree_id'] for r in rows(TOP20 / 'all_20_tree_results.csv')]
group = {r['stable_tree_id']: ('Tallest' if 'tallest' in r['selection_group'] else 'Shortest', int(r['group_rank']))
         for r in rows(TOP20 / 'all_20_tree_results.csv')}
bundle = json.loads((mp / 'results/DBH_remaining_band_review_20261023_172945/dbh_review_bundle.json').read_text(encoding='utf-8'))
prov = {s['tree']: s for s in bundle['summary'] if s.get('status') == 'Provisional wider-slice estimate'}
runs = json.loads((batch / 'all_runs.json').read_text())
changes = {r['tree']: r for r in json.loads((batch / 'reference_changes.json').read_text())}
manifest = {r['stable_tree_id']: r for r in rows(mp / 'environment' / config['manifest_name'])}

def quality(run_dir):
    q = Path(run_dir) / 'batch_quality_diagnostics.csv'
    return rows(q)[0] if q.exists() else {}

def crown_note(cmin):
    if cmin is not None and cmin < 1.0:
        return f' Crown: automatic classification starts at {cmin:.2f} m, so the trunk is counted as crown; envelope is not a biological crown volume.'
    return ''

head = ['Group', 'Rank (20-tree selection)', 'Tree', 'Data version', 'Height (m)', 'Accepted DBH (cm)',
        'Provisional / raw DBH (cm)', 'Area-equivalent DBH (cm)', 'DBH method', 'Why no accepted DBH / notes',
        'Crown area (m²)', 'Crown envelope (m³)', 'Crown starts at (m)', 'Envelope / 1 m slab ratio', 'Source SHA-256', 'Result folder', 'Human approval']
table = []
for tid in order:
    g, rank = group[tid]
    if tid in runs:
        s, run = runs[tid]['summary'], runs[tid]['run_dir']
        q = quality(run)
        mode = s['dbh_report_mode']
        circle, passes = num(s['dbh_circle_raw_cm']), s['dbh_circle_raw_passes_screen'] == 'TRUE'
        accepted = num(s['dbh_cm']) if mode in ('CIRCLE_AND_AREA_EQUIVALENT', 'OUTLINE_FILTERED_CIRCLE') else None
        area_eq = num(s['dbh_area_equivalent_cm']) if mode == 'CIRCLE_AND_AREA_EQUIVALENT' else None
        if mode == 'CIRCLE_AND_AREA_EQUIVALENT':
            raw = None if accepted is not None else circle
            note = (f"Oval trunk (ellipse {num(s['ellipse_minor_cm']):.0f} x {num(s['ellipse_major_cm']):.0f} cm): circle-fit and area-equivalent DBH reported together. "
                    + ('Circle passes the screen.' if accepted is not None else f"Circle at 1.3 m {'passes' if passes else 'fails'} the screen (RMSE {num(s['dbh_circle_raw_rmse_mm']):.1f} mm).")
                    + ' Base corrected +0.18 m.')
        elif mode == 'OUTLINE_FILTERED_CIRCLE':
            raw = None if accepted is not None else circle
            note = f"Outer-outline filter set aside {int(num(s['outline_filter_removed_points']) or 0)} non-bark points inside the outline (in memory only). Method change agreed by user."
        elif mode == 'PROVISIONAL_ONLY':
            raw = circle
            note = ('Provisional only: 3 cm point spacing is coarser than the screen allows for a ~9 cm stem '
                    f"(RMSE {num(s['dbh_circle_raw_rmse_mm']):.1f} mm, arc {num(s['dbh_circle_raw_arc']):.2f}). Base corrected +0.12 m. Old 38 cm estimate was off the stem.")
        else:
            raw = None
            note = ('Not released: poor source data (user); stem base missing below 0.45 m. Earlier near-vertical axis used. '
                    'Circle fits at 1.1-1.5 m ranged 15-26 cm and none passed, so no number is given.')
        if s['crown_classification_status'] not in ('CLASSIFICATION_AVAILABLE_REQUIRES_VISUAL_REVIEW',):
            note += f" Crown: {s['crown_classification_status']}."
        table.append([g, rank, tid, 'Cleaned trunk + corrected references (this rerun)', num(s['height_m']), accepted, raw, area_eq,
                      s['dbh_method'], note + crown_note(num(q.get('crown_min_z_m'))), num(s['crown_area_m2']), num(s['crown_volume_m3']),
                      num(q.get('crown_min_z_m')), num(q.get('full_envelope_to_1m_slab_ratio')), s['review_sha256'], Path(run).name, 'PENDING'])
    else:
        r = old[tid]
        p = prov.get(tid)
        note = 'Unchanged input since the 20-tree batch.'
        if p:
            note += f" Provisional {p['band_cm']} cm-band estimate from the earlier DBH band review; {p['note']}"
        elif num(r['dbh_cm']) is None:
            note += ' No accepted fit; not re-examined in this rerun.'
        if r['dbh_method'].startswith('median'):
            note += ' DBH is a median of accepted 1.1-1.5 m slices, not a direct 1.3 m fit.'
        cmin = num(r['crown_min_z_m']) if num(r['crown_volume_m3']) is not None else None
        table.append([g, rank, tid, '20-tree batch (unchanged input)', num(r['height_m']), num(r['dbh_cm']),
                      p['candidate_cm'] if p else None, None, r['dbh_method'], note + crown_note(cmin), num(r['crown_area_m2']), num(r['crown_volume_m3']),
                      cmin, num(r['full_envelope_to_1m_slab_ratio']), r['review_sha256'], Path(r['run_directory']).name, 'PENDING'])

n_acc = sum(1 for t in table if t[5] is not None)
measure = [['Tree measurements: 20-tree test, four cleaned trees refreshed'],
           [f'20 heights, {n_acc} accepted DBHs, {sum(1 for t in table if t[11] is not None)} crown envelopes. Everything is provisional; all human approvals are PENDING. Crown envelopes include air gaps.'],
           head] + table

compare = [['Four cleaned trees: previous batch vs this rerun'], [],
           ['Tree', 'Base shift X, Y, Z (m)', 'Axis lean used (deg)', 'Height before (m)', 'Height now (m)', 'Change (m)',
            'Accepted DBH before (cm)', 'DBH now (cm)', 'Crown area before (m²)', 'Crown area now (m²)',
            'Crown envelope before (m³)', 'Crown envelope now (m³)', 'What changed']]
why = {'tree_103': 'User removed bushes; base moved onto the trunk (+0.18 m ground); fresh axis.',
       'tree_108': 'User removed bushes; old axis followed a side branch; base moved onto the stem (+0.12 m ground).',
       'tree_067': 'User removed bushes; foot/axis unchanged; DBH outline filter.',
       'tree_033': 'User removed bushes; earlier near-vertical axis kept; source data poor.'}
for t in table:
    tid = t[2]
    if tid not in runs:
        continue
    r, s = old[tid], runs[tid]['summary']
    dbh_now = t[5] if t[5] is not None else t[6]
    compare.append([tid, ', '.join(f'{v:+.3f}' for v in changes[tid]['base_shift_xyz_m']), round(changes[tid]['axis_lean_deg'], 2),
                    num(r['height_m']), num(s['height_m']), num(s['height_m']) - num(r['height_m']),
                    num(r['dbh_cm']), dbh_now, num(r['crown_area_m2']), num(s['crown_area_m2']),
                    num(r['crown_volume_m3']), num(s['crown_volume_m3']), why[tid]])

detail = [['DBH tests for the four cleaned trees'], [],
          ['Tree', 'Source', 'Test', 'Height along stem (m)', 'Band (cm)', 'Points', 'Diameter (cm)', 'Arc', 'RMSE (mm)', 'Passes screen']]
for tid in runs:
    sl = Path(runs[tid]['run_dir']) / 'lean_dbh' / 'dbh_lean_corrected_slices.csv'
    for r in rows(sl) if sl.exists() else []:
        detail.append([tid, 'This rerun (notebook)', 'Slice fit' + (' after outline filter' if tid == 'tree_067' else ''),
                       num(r['height_m']), 6, num(r['points']), 100 * num(r['diameter_m']) if num(r['diameter_m']) else None,
                       num(r['arc']), 1000 * num(r['rmse_m']) if num(r['rmse_m']) else None, r['accepted']])
for f in ['itsme_sensitivity.csv', 'itsme_sensitivity_108_tight_crop.csv']:
    for r in rows(DIAG / 'itsme_sensitivity' / f):
        detail.append([r['tree'], 'Diagnosis (before rerun)', r['test'], num(r['slice_height_m']), num(r['band_cm']), num(r['points']),
                       num(r['diameter_cm']), num(r['arc']), num(r['rmse_mm']), r['passes_screen']])

readme = [['Read me'], [],
          ['This workbook is a NEW version. Earlier workbooks are unchanged and remain the record of earlier input versions.'],
          [f"Four trees (103, 108, 067, 033) were cleaned by the user and rerun in {batch.name} with these user decisions (23 Oct 2026):"],
          ['  103 and 108: the stem base was moved onto the trunk (inherited foot lay beside it); ground +0.18 m and +0.12 m.'],
          ['  033: earlier near-vertical stem axis kept; source data is poor, so DBH is not released.'],
          ['  067: DBH uses an outer-outline filter that sets aside non-bark points inside the trunk outline (in memory only).'],
          ['  103: the trunk is oval; circle-fit DBH and area-equivalent DBH (from an ellipse fitted to the 1.3 m slice) are both given.'],
          ['  108: DBH is provisional: the cloud has ~3 cm point spacing, too coarse for the fit screen on a ~9 cm stem.'],
          [],
          ['Accepted DBH = passes the unchanged screen: arc >= 60% and RMSE <= min(4 cm, max(1 cm, 10% of diameter)). A blank is not zero.'],
          ['Provisional / raw DBH = a fitted number that is not accepted (reason in the notes). Never mix it with accepted values in totals.'],
          ['Heights are vertical, above the stem-foot ground. Crown envelope = 3D convex hull of ITSMe-classified crown points, including air gaps; not wood volume or biomass.'],
          ['Crown starts at (m): lowest point ITSMe classified as crown. Below ~1 m the automatic crown includes the trunk, which inflates crown area and volume. This affected earlier results too; crown base review is still pending.'],
          ['Ratios above 2 in "Envelope / 1 m slab ratio" flag a gap-sensitive envelope; this is a review flag, not an error estimate.'],
          ['Nothing is field-validated and no tree is human-approved. Source clouds in CloudCompare_review_v2 were only read.'],
          [], ['Diagnosis report: measurement_pipeline/results/CLEANED_TRUNK_DIAGNOSIS_20261023_185259/DIAGNOSIS_REPORT.md'],
          [f'Rerun batch: measurement_pipeline/results/{batch.name}']]

out_dir = batch / 'outputs'
out_dir.mkdir(exist_ok=True)
path = out_dir / f'Tree_measurements_{batch.name}.xlsx'
write_xlsx(path, [
    dict(name='Measurements', rows=measure, header_row=3, widths=[10, 10, 11, 26, 11, 12, 14, 14, 26, 70, 12, 13, 12, 12, 18, 40, 12]),
    dict(name='Four trees old vs new', rows=compare, header_row=3, widths=[11, 24, 12, 12, 12, 10, 14, 12, 14, 14, 16, 16, 60]),
    dict(name='DBH detail (4 trees)', rows=detail, header_row=3, widths=[11, 24, 52, 12, 9, 9, 12, 8, 10, 10]),
    dict(name='Read me', rows=readme, header_row=None, widths=[140])])
(out_dir / 'measurements_table.json').write_text(json.dumps(dict(header=head, rows=table), indent=1), encoding='utf-8')
print(path)
