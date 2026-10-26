"""Execute the corrected four-tree notebook once per tree and record each run. Source clouds are only read."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--kernel', default=os.environ.get('ITSME_KERNEL', 'info6003-ir'))
args = parser.parse_args()
mp = Path(__file__).resolve().parents[1]
root = mp.parent
config = json.loads(Path(args.config).read_text())
batch = Path(config['batch'])
source = mp / 'notebooks' / f'ITSMe_HEIGHT_DBH_CROWN_VOLUME_{batch.name}.ipynb'
(batch / 'executed_notebooks').mkdir(exist_ok=True)
os.environ['INFO6003_PROJECT_ROOT'] = str(root)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

runs = {}
for tree in config['trees']:
    nb = nbformat.read(source, as_version=4)
    cell, = [c for c in nb.cells if c.cell_type == 'code' and 'TREE_ID <- "tree_103"' in c.source]
    cell.source = cell.source.replace('TREE_ID <- "tree_103"', 'TREE_ID <- ' + json.dumps(tree))
    before = set((mp / 'results').glob(f'ITSMe_metrics_{tree}_*'))
    error = None
    try:
        NotebookClient(nb, kernel_name=args.kernel, timeout=1800,
                       resources={'metadata': {'path': str(source.parent)}}).execute()
    except Exception as exc:
        error = repr(exc)
    nbformat.write(nb, batch / 'executed_notebooks' / f'{tree}_EXECUTED.ipynb')
    created = set((mp / 'results').glob(f'ITSMe_metrics_{tree}_*')) - before
    run = created.pop() if len(created) == 1 else None
    summary = None
    if run and (run / 'tree_metrics.csv').exists():
        with (run / 'tree_metrics.csv').open(encoding='utf-8-sig', newline='') as f:
            summary, = csv.DictReader(f)
    runs[tree] = dict(error=error, run_dir=str(run) if run else None, notebook_sha256=sha(source), summary=summary)
    print(tree, 'error' if error else 'ok', run, flush=True)
(batch / 'all_runs.json').write_text(json.dumps(runs, indent=2), encoding='utf-8')
assert not any(r['error'] for r in runs.values()), {t: r['error'] for t, r in runs.items() if r['error']}
