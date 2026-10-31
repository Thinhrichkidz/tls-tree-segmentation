"""Summarise header CSVs from hdr.py: file count, PLY count, vertex sum, zero/empty, mtime range, header comment variants.
Usage: python -I summ.py csv [csv...]"""
import sys, pandas as pd, os, re, collections
for c in sys.argv[1:]:
    d = pd.read_csv(c)
    p = d[d.ext.isin(['.ply', '.las', '.laz'])].copy()
    p['n'] = pd.to_numeric(p.n_points, errors='coerce')
    print(f'== {os.path.basename(c)}: files={len(d)} clouds={len(p)} non-cloud={sorted(set(d.path.map(os.path.basename)) - set(p.path.map(os.path.basename)))}')
    print(f'   sum_points={int(p.n.sum())} min={int(p.n.min())} max={int(p.n.max())} zero={int((p.n==0).sum())} nan={int(p.n.isna().sum())}')
    print(f'   mtime {p.mtime.min()} .. {p.mtime.max()}; size sum={p["size"].sum()}')
    comm = collections.Counter(re.sub(r'\d', '#', ' | '.join(s for s in str(m).split(' | ') if s.startswith(('comment', 'obj_info'))))[:200] for m in p.meta)
    for k, v in comm.most_common(4): print(f'   [{v}] {k}')
