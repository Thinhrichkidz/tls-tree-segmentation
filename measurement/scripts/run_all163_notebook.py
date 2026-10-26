"""Execute ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME.ipynb (R kernel) and save the executed copy into the output folder.

Usage: python run_all163_notebook.py --out <output folder> [--trees tree_001,tree_002] [--kernel info6003-ir]
The template notebook is not modified. Rerunning with the same --out resumes from the per-tree checkpoints.
"""
import argparse
import os
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--trees', default='')
ap.add_argument('--kernel', default='info6003-ir')
ap.add_argument('--notebook', default='ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME.ipynb')
ap.add_argument('--previous', default='')
a = ap.parse_args()
mp = Path(__file__).resolve().parents[1]
src = mp / 'notebooks' / a.notebook
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
nb = nbformat.read(src, as_version=4)
if a.trees:
    cell, = [c for c in nb.cells if c.cell_type == 'code' and 'TREE_IDS <- NULL' in c.source]
    cell.source = cell.source.replace('TREE_IDS <- NULL', 'TREE_IDS <- c(' + ', '.join(f'"{t}"' for t in a.trees.split(',')) + ')')
os.environ['ALL163_OUT'] = str(out)
os.environ['ALL163_PREVIOUS'] = a.previous
os.environ['INFO6003_PROJECT_ROOT'] = str(mp.parent)
t0 = time.time()
try:
    NotebookClient(nb, kernel_name=a.kernel, timeout=None, resources={'metadata': {'path': str(src.parent)}}).execute()
finally:
    nbformat.write(nb, out / 'ITSMe_all163_processing.ipynb')
    (out / 'logs').mkdir(exist_ok=True)
    (out / 'logs' / 'notebook_wall_seconds.txt').write_text(f'{time.time() - t0:.1f}\n')
print('executed in', round(time.time() - t0, 1), 's ->', out / 'ITSMe_all163_processing.ipynb')
