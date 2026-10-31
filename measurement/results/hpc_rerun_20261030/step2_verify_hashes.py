"""Step 2 (read only): compare SHA-256 of CloudCompare_review_v2/*.ply with the session4 baseline
(session3 differences reported for information), and re-hash every file in HANDOVER/FILE_MANIFEST.csv.

Run: python -I -B hpc_run_20261030_1715/step2_verify_hashes.py
Writes only into this script's own folder.
"""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
PLY_DIR = R / 'CloudCompare_review_v2'
BASELINES = {'session4': R / 'session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv',
             'session3': R / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def compare(current, baseline):
    rows = {r['file']: r for r in csv.DictReader(open(baseline, encoding='utf-8-sig'))}
    diff = [[f, 'hash differs', rows[f]['sha256'], current[f]] for f in sorted(current) if f in rows and rows[f]['sha256'] != current[f]]
    diff += [[f, 'not in baseline', '', current[f]] for f in sorted(set(current) - set(rows))]
    diff += [[f, 'missing on disk', rows[f]['sha256'], ''] for f in sorted(set(rows) - set(current))]
    return len(rows), diff


current = {p.name: sha256(p) for p in sorted(PLY_DIR.glob('*.ply'))}
with open(HERE / 'step2_ply_hashes_now.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['file', 'sha256', 'bytes'])
    for n, h in current.items():
        w.writerow([n, h, (PLY_DIR / n).stat().st_size])

out = {'ply_count': len(current)}
for name, base in BASELINES.items():
    n, diff = compare(current, base)
    out[name] = {'baseline_rows': n, 'n_differences': len(diff), 'differences': diff}

manifest = list(csv.DictReader(open(R / 'HANDOVER/FILE_MANIFEST.csv', encoding='utf-8-sig')))
mres = []
for row in manifest:
    p = R / row['path']
    if not p.exists():
        mres.append([row['path'], 'MISSING'])
    elif p.is_dir() or not row.get('sha256'):
        mres.append([row['path'], 'dir or no hash: exists'])
    elif sha256(p) != row['sha256']:
        mres.append([row['path'], 'HASH DIFFERS', row['sha256'], sha256(p), row['size_bytes'], p.stat().st_size])
    else:
        mres.append([row['path'], 'OK'])
out['manifest'] = {'rows': len(manifest),
                   'counts': {k: sum(1 for m in mres if m[1] == k) for k in sorted({m[1] for m in mres})},
                   'not_ok': [m for m in mres if m[1] != 'OK']}
(HERE / 'step2_hash_report.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
