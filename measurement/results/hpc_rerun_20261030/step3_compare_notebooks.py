"""Step 3 (read only): compare code cells of the v5 template notebook with the executed v6 FINAL notebook."""
import difflib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
A = R / 'measurement_pipeline/notebooks/ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb'
B = R / 'measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/ITSMe_all163_processing.ipynb'


def code(p):
    nb = json.loads(p.read_text(encoding='utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']


a, b = code(A), code(B)
print('code cells: template', len(a), '| executed v6', len(b))
same = a == b
print('identical code:', same)
if not same:
    for line in difflib.unified_diff('\n'.join(a).splitlines(), '\n'.join(b).splitlines(), 'v5_template', 'v6_executed', lineterm='', n=1):
        print(line)
