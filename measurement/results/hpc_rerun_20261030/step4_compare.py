"""Step 4 (read only): compare the tree_065 smoke run with v6 FINAL, field by field.

Run: python -I -B hpc_run_20261030_1715/step4_compare.py
Writes step4_comparison.json into this script's own folder.
"""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
V6 = R / 'measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028'
NEW = HERE / 'step4_smoke_tree_065'
TID = 'tree_065'
# fields that legitimately differ between runs (paths, timings, process ids)
VOLATILE = {'local_xyz_path', 'prep_seconds', 'seconds', 'pid', 'started', 'finished', 'elapsed', 'time', 'measure_seconds'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def flat(d, prefix=''):
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            out.update(flat(v, f'{prefix}{k}.'))
        return out
    return {prefix[:-1]: d}


def cmp_values(a, b):
    if a == b:
        return 'same'
    try:
        fa, fb = float(a), float(b)
        return f'numeric diff {fb - fa:+.3g}'
    except (TypeError, ValueError):
        return 'differs'


def cmp_json(rel):
    a, b = V6 / rel, NEW / rel
    if not (a.exists() and b.exists()):
        return {'missing': [str(p) for p in (a, b) if not p.exists()]}
    fa, fb = flat(json.loads(a.read_text(encoding='utf-8'))), flat(json.loads(b.read_text(encoding='utf-8')))
    diffs = {}
    for k in sorted(set(fa) | set(fb)):
        if k.split('.')[-1] in VOLATILE:
            continue
        r = cmp_values(fa.get(k, '<absent>'), fb.get(k, '<absent>'))
        if r != 'same':
            diffs[k] = [fa.get(k, '<absent>'), fb.get(k, '<absent>'), r]
    return {'keys_compared': len(set(fa) | set(fb)), 'n_diffs': len(diffs), 'diffs': diffs}


def row(p):
    return next(r for r in csv.DictReader(open(p, encoding='utf-8-sig')) if r['tree_id'] == TID)


out = {}
a, b = row(V6 / 'results/tree_attributes.csv'), row(NEW / 'results/tree_attributes.csv')
cols = list(a)
out['tree_attributes'] = {'columns': len(cols), 'same_header': list(b) == cols,
                          'diffs': {c: [a[c], b.get(c), cmp_values(a[c], b.get(c))] for c in cols if a[c] != b.get(c)}}
for rel in [f'per_tree/{TID}/result.json', f'per_tree/{TID}/prep.json', f'per_tree/{TID}/height_refine.json',
            f'per_tree/{TID}/coordinate_transform.json', 'manifests/roi.json']:
    out[rel] = cmp_json(rel)
xyz = f'per_tree/{TID}/{TID}_local_xyz.txt'
out[xyz] = {'v6': sha(V6 / xyz), 'new': sha(NEW / xyz)}
out[xyz]['identical'] = out[xyz]['v6'] == out[xyz]['new']
v = json.loads((NEW / 'logs/validation.json').read_text(encoding='utf-8'))
out['validation_failed_checks'] = [k for k, x in v.get('checks', {}).items() if x is not True]
(HERE / 'step4_comparison.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
print(json.dumps(out, indent=1, default=str))
