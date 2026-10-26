"""New workbook version: previous corrected-rerun workbook + crown values above the user-agreed crown base.

The previous workbook is only read. Height and DBH columns are carried over unchanged; crown columns come from
CROWN_BASE_RERUN_*/crown_results.csv, with the earlier automatic-crown values kept alongside for comparison.
"""
import argparse
import csv
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx_writer import read_xlsx_rows, write_xlsx

parser = argparse.ArgumentParser()
parser.add_argument('--batch', required=True)
args = parser.parse_args()
mp = Path(__file__).resolve().parents[1]
batch = Path(args.batch).resolve()
PREV = mp / 'results/CORRECTED_FOUR_TREE_RERUN_20261023_190059/outputs/Tree_measurements_CORRECTED_FOUR_TREE_RERUN_20261023_190059.xlsx'

def rows(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def num(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None

prev = read_xlsx_rows(PREV)
crown = {r['tree']: r for r in rows(batch / 'crown_results.csv')}
bases = {r['tree']: r for r in rows(batch / 'agreed_crown_bases.csv')}
m = prev['Measurements']
head = m[2]
col = {h: i for i, h in enumerate(head)}
for h in ['Tree', 'Why no accepted DBH / notes', 'Crown area (m²)', 'Crown envelope (m³)', 'Crown starts at (m)', 'Envelope / 1 m slab ratio']:
    assert h in col, h
new_head = (head[:col['Crown area (m²)']] +
            ['Crown base (m)', 'Crown base source', 'Crown area (m²)', 'Crown envelope (m³)', 'Envelope / 1 m slab ratio',
             'Previous automatic crown area (m²)', 'Previous automatic envelope (m³)', 'Previous automatic crown start (m)'] +
            head[col['Envelope / 1 m slab ratio'] + 1:])
table, change = [], []
for r in m[3:]:
    tid = r[col['Tree']]
    c, b = crown[tid], bases[tid]
    note = re.sub(r' Crown: automatic classification starts at [^.]*\.[^.]*\.', '', r[col['Why no accepted DBH / notes']] or '')
    if tid == 'tree_033':
        note += ' Crown: source data poor; crown values remain flagged.'
    if (num(c['full_envelope_to_1m_slab_ratio']) or 0) > 2:
        note += ' Crown envelope still bridges large gaps (slab ratio > 2).'
    out = (r[:col['Crown area (m²)']] +
           [num(c['crown_base_m']), c['base_source'], num(c['crown_area_m2']), num(c['crown_volume_m3']),
            num(c['full_envelope_to_1m_slab_ratio']), r[col['Crown area (m²)']], r[col['Crown envelope (m³)']],
            r[col['Crown starts at (m)']]] + r[col['Envelope / 1 m slab ratio'] + 1:])
    out[col['Why no accepted DBH / notes']] = note.strip()
    table.append(out)
    old_v, new_v = r[col['Crown envelope (m³)']], num(c['crown_volume_m3'])
    change.append([tid, r[col['Crown starts at (m)']], num(c['crown_base_m']), c['base_source'],
                   int(c['crown_points_before']), int(c['crown_points_kept']), r[col['Crown area (m²)']], num(c['crown_area_m2']),
                   old_v, new_v, None if not old_v or new_v is None else round(100 * (new_v - old_v) / old_v, 1),
                   r[col['Envelope / 1 m slab ratio']], num(c['full_envelope_to_1m_slab_ratio'])])

measure = [['Tree measurements: 20-tree test, crown measured above the agreed crown base'],
           [m[1][0].split('. Everything')[0] + '. Crown area and envelope now start at the agreed crown base. Everything is provisional; all human approvals are PENDING. Crown envelopes include air gaps.'],
           new_head] + table
crown_sheet = [['Crown base change: automatic ITSMe crown vs crown above the agreed base'], [],
               ['Tree', 'Automatic crown start (m)', 'Agreed crown base (m)', 'Base source', 'Crown points before', 'Crown points kept',
                'Crown area before (m²)', 'Crown area now (m²)', 'Envelope before (m³)', 'Envelope now (m³)', 'Envelope change (%)',
                'Slab ratio before', 'Slab ratio now']] + change
readme = prev['Read me'] + [[], ['CROWN BASE VERSION (this workbook):'],
    [f'Crown values come from {batch.name}. Rule agreed by the user on 23 Oct 2026: crown base = base of the continuous crown '
     '(lowest 0.25 m layer above 1 m that is much wider than the trunk and from which >= 70% of layers up to the top are crown).'],
    ['User choices for uncertain trees: 048 = 8.25 m, 056 = 4.25 m, 151 = 3.00 m, 076 = 5.00 m, 146 = 8.50 m, 118 = 10.75 m.'],
    ["Crown points are ITSMe's own crown classification from each tree's current run; only points below the base were dropped. "
     'Projected area (concave hull, concavity 3) and the convex envelope were recomputed with the same settings.'],
    ['Height and DBH are unchanged from the previous version. Proposal and views: measurement_pipeline/results/CROWN_BASE_PROPOSAL_20261023_190901.']]
readme = [r for r in readme if not (r and isinstance(r[0], str) and r[0].startswith('Crown starts at (m):'))]
out_dir = batch / 'outputs'
out_dir.mkdir(exist_ok=True)
path = out_dir / f'Tree_measurements_{batch.name}.xlsx'
write_xlsx(path, [
    dict(name='Measurements', rows=measure, header_row=3,
         widths=[10, 10, 11, 26, 11, 12, 14, 14, 26, 70, 10, 24, 12, 13, 12, 14, 14, 14, 18, 40, 12]),
    dict(name='Crown base change', rows=crown_sheet, header_row=3, widths=[11, 14, 14, 30, 12, 12, 13, 13, 13, 13, 12, 11, 11]),
    dict(name='Four trees old vs new', rows=prev['Four trees old vs new'], header_row=3, widths=[11, 24, 12, 12, 12, 10, 14, 12, 14, 14, 16, 16, 60]),
    dict(name='DBH detail (4 trees)', rows=prev['DBH detail (4 trees)'], header_row=3, widths=[11, 24, 52, 12, 9, 9, 12, 8, 10, 10]),
    dict(name='Read me', rows=readme, header_row=None, widths=[140])])
(out_dir / 'measurements_table.json').write_text(json.dumps(dict(header=new_head, rows=table), indent=1), encoding='utf-8')
print(path)
