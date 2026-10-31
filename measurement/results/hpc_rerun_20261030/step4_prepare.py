"""Step 4 preparation (read only): list all-core-VALID trees in v6 FINAL, and compare the script hashes v6 FINAL
recorded in results/methods.json with the scripts on disk now.

Run: python -I -B hpc_run_20261030_1715/step4_prepare.py
"""
import csv
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
MP = R / 'measurement_pipeline'
V6 = MP / 'results/ITSMe_all163_output_v6_FINAL_20261028'
EDITED_28OCT = {'tree_023', 'tree_027', 'tree_035', 'tree_039', 'tree_045', 'tree_055', 'tree_082', 'tree_083', 'tree_094',
                'tree_099', 'tree_100', 'tree_120', 'tree_121', 'tree_124', 'tree_136', 'tree_137', 'tree_139', 'tree_147'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


rows = list(csv.DictReader(open(V6 / 'results/tree_attributes.csv', encoding='utf-8-sig')))
core = ['height_status', 'dbh_status', 'crown_area_status']
for vol in ('crown_volume_status', 'crown_volume_slab_status'):
    n = sum(all(r[c] == 'VALID' for c in core + [vol]) for r in rows)
    print(f'all VALID with {vol}: {n}')
summ = json.loads((V6 / 'results/summary.json').read_text(encoding='utf-8'))
print('summary.json keys mentioning valid:', {k: v for k, v in summ.items() if 'valid' in k.lower() and not isinstance(v, (dict, list))})

print('\ncandidates (height, DBH, area, slab volume all VALID):')
for r in rows:
    if all(r[c] == 'VALID' for c in core + ['crown_volume_slab_status']):
        print(f"  {r['tree_id']}  pts {int(r['n_points']):>8}  env_vol {r['crown_volume_status']:6}  stem_src {r['stem_xy_source'][:22]:22}"
              f"  edited28Oct {r['tree_id'] in EDITED_28OCT}  H {float(r['height_m']):6.2f}  DBH {r['dbh_cm']}")

meth = json.loads((V6 / 'results/methods.json').read_text(encoding='utf-8'))


def find(d):
    if isinstance(d, dict):
        if 'script_sha256' in d:
            return d['script_sha256']
        for v in d.values():
            x = find(v)
            if x:
                return x


rec = find(meth) or {}
print(f'\nscript hashes recorded by v6 FINAL: {len(rec)}')
for name, h in sorted(rec.items()):
    p = MP / 'scripts' / name
    now = sha(p) if p.exists() else 'MISSING'
    print(f"  {'SAME' if now == h else 'DIFF'}  {name}")
