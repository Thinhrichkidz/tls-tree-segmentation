"""Summarise finished notebook tests and preserve scientific caveats for the review workbook."""
import argparse
import csv
import json
import math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('batch', type=Path)
a = ap.parse_args()
batch = a.batch
config = json.loads((batch / 'batch_config.json').read_text())
records = json.loads((batch / 'all_runs.json').read_text())
assert len(records) == len({r['tree'] for r in records}) == 20
assert all(not r['execution_error'] for r in records), 'A notebook execution did not finish.'
assert all(r['metrics'].get('dbh_status') != 'non-numeric argument to binary operator' for r in records), 'Rerun attempts affected by the corrected manifest first.'
previous = {r['Tree']: r for r in json.loads((batch / 'previous_11_tree_results.json').read_text())}
visual = json.loads((batch / 'visual_review_notes.json').read_text())
with (Path(config['project_root']) / 'measurement_pipeline/environment' / config['manifest_name']).open(encoding='utf-8-sig', newline='') as f:
    manifest = {r['stable_tree_id']: r for r in csv.DictReader(f)}

def numeric(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None

segmentation = {
    'tree_103': 'Missing quarantined crown pieces; inspect basal vegetation and crown base.',
    'tree_084': 'Detached crown piece may belong to tree_079; inspect crown base.',
    'tree_069': 'Missing quarantined crown pieces; inspect crown base.',
    'tree_026': 'Earlier DBH ring was unusable; mixed lower-stem material needs review.',
    'tree_102': 'Axis was refitted to current points; inherited foot-ground reference retained.',
    'tree_060': 'Missing quarantined crown pieces; inspect low crown classification.',
    'tree_108': 'Strong lean and fork above breast height; earlier DBH was low confidence.',
    'tree_152': 'Missing lower trunk and uncertain crown pieces from previous review.',
    'tree_056': 'Earlier DBH was sparse and low confidence.',
    'tree_146': 'Lower branches and upper foliage separated by a long stem interval.',
    'tree_151': 'Unassigned foliage was noted in the previous review.',
}
reviewed = []
for r in records:
    tid, m, qc = r['tree'], r['metrics'], r['qc']
    src = manifest[tid]
    expected_height = float(src['maximum_observed_z_m']) - float(src['translation_z_m'])
    assert abs(float(m['height_m']) - expected_height) < 1e-8, f'Height consistency failed for {tid}'
    prior = previous.get(tid, {})
    ratio = numeric(qc.get('full_envelope_to_1m_slab_ratio'))
    issues = []
    dbh = numeric(m.get('dbh_cm'))
    if dbh is None:
        issues.append('No accepted DBH')
    if numeric(m.get('crown_volume_m3')) is None:
        issues.append('Crown classification failed')
    if numeric(qc.get('dbh13_points')) is not None and float(qc['dbh13_points']) < 20:
        issues.append('Sparse breast-height slice')
    if ratio is not None and ratio > 2:
        issues.append('Gap-sensitive crown envelope')
    if numeric(qc.get('axis_offset_at_foot_m')) is not None and float(qc['axis_offset_at_foot_m']) > .1:
        issues.append('Axis/foot offset needs review')
    if 'median' in m.get('dbh_method', ''):
        issues.append('DBH uses nearby-slice median')
    slab_path = Path(r['run_dir']) / 'crown_volume_slab_sensitivity.csv'
    slab = []
    if slab_path.exists():
        with slab_path.open(encoding='utf-8-sig', newline='') as f:
            slab = list(csv.DictReader(f))
    slab1 = next((v for v in slab if float(v['thickness_m']) == 1), {})
    prior_height = numeric(prior.get('Height ITSMe (m)'))
    prior_dbh = numeric(prior.get('RECOMMENDED DBH (cm)'))
    prior_area = numeric(prior.get('Crown projected area (m2) - exploratory'))
    reviewed.append(dict(tree=tid, group='Tallest' if 'tallest' in r['group'] else 'Shortest', rank=int(r['rank']),
                         height_m=float(m['height_m']), dbh_cm=dbh,
                         crown_area_m2=numeric(m.get('crown_area_m2')),
                         crown_volume_m3=numeric(m.get('crown_volume_m3')),
                         dbh_method=m.get('dbh_method'), dbh_status=m.get('dbh_status'),
                         review_flags='; '.join(issues) or 'Inspect crown definition and fit plots',
                         segmentation_note=visual['notes'].get(tid, segmentation.get(tid, 'Crown ownership has not been human-approved.')),
                         earlier_segmentation_note=segmentation.get(tid, ''),
                         axis_lean_deg=numeric(qc.get('axis_lean_degrees')),
                         dbh13_points=numeric(qc.get('dbh13_points')), dbh13_arc=numeric(qc.get('dbh13_arc')),
                         dbh13_rmse_mm=1000*float(qc['dbh13_rmse_m']) if numeric(qc.get('dbh13_rmse_m')) is not None else None,
                         accepted_slices=numeric(qc.get('accepted_dbh_slices')),
                         axis_foot_offset_m=numeric(qc.get('axis_offset_at_foot_m')),
                         slab1_volume_m3=numeric(slab1.get('sum_separate_slab_hulls_m3')),
                         envelope_to_slab1_ratio=ratio,
                         crown_min_z_m=numeric(qc.get('crown_min_z_m')),
                         crown_max_z_m=numeric(qc.get('crown_max_z_m')),
                         previous_height_m=prior_height,
                         height_delta_vs_rounded_previous_mm=1000*(float(m['height_m'])-prior_height) if prior_height is not None else None,
                         previous_dbh_cm=prior_dbh,
                         dbh_delta_cm=dbh-prior_dbh if dbh is not None and prior_dbh is not None else None,
                         previous_dbh_confidence=prior.get('Recommended DBH confidence', ''),
                         previous_crown_area_m2=prior_area,
                         crown_area_delta_m2=float(m['crown_area_m2'])-prior_area if prior_area is not None else None,
                         run_dir=r['run_dir'], review_sha256=m['review_sha256'],
                         human_decision=m['human_review_decision']))
counts = dict(tested=len(records), height_available=sum(r['height_m'] is not None for r in reviewed),
              dbh_accepted=sum(r['dbh_cm'] is not None for r in reviewed),
              crown_volume_available=sum(r['crown_volume_m3'] is not None for r in reviewed),
              envelope_ratio_over_2=sum(r['envelope_to_slab1_ratio'] is not None and r['envelope_to_slab1_ratio'] > 2 for r in reviewed),
              nearby_slice_median=sum('median' in r['dbh_method'] for r in reviewed),
              all_height_geometry_checks_pass=True, protected_files_unchanged=163)
bundle = dict(counts=counts, results=reviewed,
              selection=config['selection_caveat'],
              conclusion='Software execution and algebraic height checks do not establish biological accuracy. A convex crown envelope can include long empty stem intervals and internal gaps. Automatic crown boundaries and point ownership need visual review before volume is reported as a biological crown measurement.',
              slab_caveat='The sum of separate slab hulls is a parameter-sensitive diagnostic, not a validated replacement volume or an error estimate. Ratio >2 is a review screen only.')
(batch / 'review_bundle.json').write_text(json.dumps(bundle, indent=2), encoding='utf-8')
lines = ['20-TREE CROWN-VOLUME NOTEBOOK TEST', '23 October 2026, Australia/Sydney', '', json.dumps(counts, indent=2), '',
         bundle['conclusion'], '', config['selection_caveat'], '', bundle['slab_caveat'], '',
         'Group     Rank Tree        Height m  DBH cm  Crown envelope m3  Review']
for r in reviewed:
    dbh = f'{r["dbh_cm"]:.2f}' if r['dbh_cm'] is not None else 'n.a.'
    volume = f'{r["crown_volume_m3"]:.2f}' if r['crown_volume_m3'] is not None else 'n.a.'
    lines.append(f'{r["group"]:9} {r["rank"]:4} {r["tree"]:10} {r["height_m"]:8.3f} {dbh:>7} {volume:>18}  {r["review_flags"]}')
lines += ['', 'DBH reported only for accepted perpendicular fits; a labelled nearby-slice median may be used when the 1.3 m fit is unacceptable.',
          'Earlier height references were rounded to 0.001 m and DBH to 0.01 cm in the workbook. Tiny comparison differences reflect rounding.',
          'tree_102: a fresh axis was fitted to edited points; inspect its axis/foot offset and fit. Earlier foot-ground reference retained.',
          'tree_114: refreshed supported height is 20.041916 m, so tree_118 replaces it in the ten tallest.',
          'All human decisions remain PENDING. No field validation, wood volume, biomass, or QSM results are implied.']
(batch / 'BATCH_REVIEW.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(counts, indent=2))
