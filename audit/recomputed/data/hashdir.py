"""SHA-256 every file in given dirs (non-recursive) or files. Usage: python -I hashdir.py OUT.csv PATH [...]"""
import sys, os, hashlib, csv, datetime
from concurrent.futures import ThreadPoolExecutor

def h(p):
    s = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): s.update(b)
    st = os.stat(p)
    return dict(path=p.replace('\\', '/'), size_bytes=st.st_size,
                mtime=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'), sha256=s.hexdigest())

ps = []
for a in sys.argv[2:]:
    ps += [os.path.join(a, f) for f in sorted(os.listdir(a)) if os.path.isfile(os.path.join(a, f))] if os.path.isdir(a) else [a]
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(h, ps))
with open(sys.argv[1], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), 'hashed ->', sys.argv[1])
