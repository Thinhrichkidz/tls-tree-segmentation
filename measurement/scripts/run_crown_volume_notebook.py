"""Execute one tree in the new notebook, save its executed copy, and check reference results when available."""
import argparse
import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path

import nbformat
from nbclient import NotebookClient

parser = argparse.ArgumentParser()
parser.add_argument('--tree', default='tree_146')
parser.add_argument('--kernel', default=os.environ.get('ITSME_KERNEL', 'info6003-ir'))
args = parser.parse_args()
mp = Path(__file__).resolve().parents[1]
root = mp.parent
source = mp / 'notebooks' / 'ITSMe_HEIGHT_DBH_CROWN_VOLUME.ipynb'
nb = nbformat.read(source, as_version=4)
matches = 0
for cell in nb.cells:
    if cell.cell_type == 'code' and 'TREE_ID <- "tree_146"' in cell.source:
        cell.source = cell.source.replace('TREE_ID <- "tree_146"', 'TREE_ID <- ' + json.dumps(args.tree))
        matches += 1
assert matches == 1
batch = mp / 'results' / f'CROWN_VOLUME_notebook_test_{args.tree}_{datetime.now():%Y%m%d_%H%M%S}'
batch.mkdir(exist_ok=False)
os.environ['INFO6003_PROJECT_ROOT'] = str(root)
before = set((mp / 'results').glob(f'ITSMe_metrics_{args.tree}_*'))

def started(cell, cell_index):
    print(f'Executing cell {cell_index + 1}/{len(nb.cells)}', flush=True)

error = None
try:
    NotebookClient(nb, kernel_name=args.kernel, timeout=1200,
                   on_cell_start=started,
                   resources={'metadata': {'path': str(source.parent)}}).execute()
except Exception as exc:
    error = repr(exc)
    raise
finally:
    nbformat.write(nb, batch / f'{args.tree}_EXECUTED.ipynb')
    (batch / 'execution_status.json').write_text(json.dumps({'tree': args.tree, 'error': error}, indent=2), encoding='utf-8')
created = set((mp / 'results').glob(f'ITSMe_metrics_{args.tree}_*')) - before
assert len(created) == 1, created
run = created.pop()
with (run / 'tree_metrics.csv').open(encoding='utf-8-sig', newline='') as stream:
    row, = csv.DictReader(stream)
def number(name):
    try:
        return float(row[name])
    except (ValueError, TypeError):
        return math.nan
checks = {'no_notebook_errors': not any(o.output_type == 'error' for c in nb.cells if c.cell_type == 'code' for o in c.outputs),
          'positive_crown_volume': number('crown_volume_m3') > 0,
          'positive_crown_area': number('crown_area_m2') > 0,
          'human_decision_preserved': row['human_review_decision'] == 'PENDING'}
if args.tree == 'tree_146':
    checks.update(height_reference=abs(float(row['height_m']) - 12.067056599187) < 1e-6,
                  horizontal_dbh_reference=abs(float(row['dbh_horizontal_diagnostic_cm']) - 10.6592312595371) < 0.01,
                  crown_area_reference=abs(float(row['crown_area_m2']) - 2.783742185) < 1e-6,
                  accepted_lean_dbh=10.5 < number('dbh_cm') < 10.8)
report = {'tree': args.tree, 'run_dir': str(run), 'executed_notebook': str(batch / f'{args.tree}_EXECUTED.ipynb'),
          'checks': checks, 'summary': row}
(batch / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
assert all(checks.values()), checks
