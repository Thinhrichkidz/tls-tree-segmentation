"""Write RUN_MANIFEST.csv (path, bytes, sha256) for every file in this hpc_run folder, plus a per-folder size summary.
Run: python -I -B hpc_run_20261030_1715/make_manifest.py
"""
import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows, sizes = [], {}
for p in sorted(HERE.rglob('*')):
    if not p.is_file() or p.name == 'RUN_MANIFEST.csv':
        continue
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    rel = p.relative_to(HERE).as_posix()
    rows.append([rel, p.stat().st_size, h.hexdigest()])
    top = '/'.join(rel.split('/')[:2]) if '/' in rel else '(top level)'
    s = sizes.setdefault(top, [0, 0]); s[0] += 1; s[1] += p.stat().st_size
with open(HERE / 'RUN_MANIFEST.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['path', 'bytes', 'sha256']); w.writerows(rows)
print('files', len(rows), 'total MB', round(sum(r[1] for r in rows) / 2**20, 1))
for k, (n, b) in sorted(sizes.items()):
    print(f'  {k:45s} {n:6d} files {b / 2**20:9.1f} MB')
