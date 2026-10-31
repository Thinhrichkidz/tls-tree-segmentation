"""SHA-256 / size / mtime inventory of key report, script and result files (not point clouds; see agent_data/inventory_data.csv).
Usage: python -I make_inventory.py <out_csv> <path> [<path> ...]   (directories are walked, venv/R-library skipped)"""
import csv, hashlib, os, sys, datetime
SKIP = ('.venv', '.home-venv', 'R-library', '__pycache__', '_deps', 'per_tree', 'individual_trees', '.git')
rows = []
for root in sys.argv[2:]:
    paths = [root] if os.path.isfile(root) else [os.path.join(d, f) for d, ds, fs in os.walk(root) if not any(s in d for s in SKIP) for f in fs]
    for p in sorted(paths):
        if p.lower().endswith(('.ply', '.las', '.laz')):
            continue
        h = hashlib.sha256()
        with open(p, 'rb') as fh:
            for b in iter(lambda: fh.read(1 << 20), b''):
                h.update(b)
        st = os.stat(p)
        rows.append(dict(path=os.path.abspath(p), size_bytes=st.st_size, mtime=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'), sha256=h.hexdigest()))
with open(sys.argv[1], 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]) + ['notes']); w.writeheader(); w.writerows(rows)
print(len(rows), 'files')
