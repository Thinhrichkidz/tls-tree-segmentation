"""Cross-directory comparisons using hdr_*.csv and hash_trees.csv in agent_data. Usage: python -I compare.py AGENT_DATA_DIR"""
import sys, os, re, pandas as pd
A = sys.argv[1]
H = pd.read_csv(os.path.join(A, 'hash_trees.csv'))
H['dir'] = H.path.map(lambda p: p.split('/3cm/')[1].rsplit('/', 1)[0]); H['name'] = H.path.map(os.path.basename)
def hdr(f):
    d = pd.read_csv(os.path.join(A, f)); d['name'] = d.path.map(lambda p: os.path.basename(p.replace('\\', '/')))
    return d[d.ext == '.ply'].assign(n=lambda x: x.n_points.astype(int))
num = lambda s, pat: int(re.search(pat, s).group(1))

print('### per-dir hash duplicates and empties')
for d, g in H.groupby('dir'):
    dup = g[g.sha256.duplicated(keep=False)]
    print(f'{d}: files={len(g)} zero_bytes={(g.size_bytes==0).sum()} dup_hash_files={len(dup)} {list(dup.name)[:6]}')

print('### identical-content directory pairs (set of sha256)')
S = {d: set(g.sha256) for d, g in H.groupby('dir')}
ds = sorted(S)
for i, a in enumerate(ds):
    for b in ds[i+1:]:
        inter = len(S[a] & S[b])
        if inter: print(f'{a} vs {b}: shared={inter} |a|={len(S[a])} |b|={len(S[b])}')

print('### final set: CloudCompare_review_v2 vs snapshot & manifest')
snap = pd.read_csv('D:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help/session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv', encoding='utf-8-sig')
man = pd.read_csv('D:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results/ITSMe_all163_output_v3_FINAL_20261023_201144/manifests/all163_manifest.csv')
f = H[H.dir == 'Codex_help/CloudCompare_review_v2'].merge(snap, left_on='name', right_on='file', how='outer', indicator=True)
print('snapshot merge:', f._merge.value_counts().to_dict(), 'sha_match=', (f.sha256_x == f.sha256_y).sum(), 'bytes_match=', (f.size_bytes == f.bytes).sum())
f['tree'] = f.name.str.extract(r'(tree_\d{3})')
m = f.merge(man, on='tree', how='outer', indicator='m2')
print('manifest merge:', m.m2.value_counts().to_dict(), 'review_sha256 match=', (m.sha256_x == m.review_sha256).sum())
cv2 = hdr('hdr_ccr_v2.csv'); cv2['tree'] = cv2.name.str.extract(r'(tree_\d{3})')
mm = cv2.merge(man, on='tree')
print('manifest point_count == header vertex:', (mm.n == mm.point_count).sum(), 'of', len(mm), 'manifest sum=', man.point_count.sum())
print('final label counts:', cv2.name.str.extract(r'tree_\d{3}_(.*?)(?: - Cloud)?\.ply')[0].value_counts().to_dict())
nums = sorted(cv2.name.str.extract(r'tree_(\d{3})')[0].astype(int)); print('final numbering', nums[0], '..', nums[-1], 'gaps=', sorted(set(range(1, 164)) - set(nums)))

print('### which CloudCompare_review_v2 files are byte-identical to manual_seg_v2')
v2 = H[H.dir == 'Codex_help/manual_seg_v2'].set_index('sha256').name.to_dict()
ccr = H[H.dir == 'Codex_help/CloudCompare_review_v2']
ident = ccr.sha256.isin(v2); print('identical:', ident.sum(), 'differ:', list(ccr[~ident].name))

print('### point-count pairing: automated trees/clouds vs final 163')
auto = hdr('hdr_clouds.csv'); auto['k'] = auto.name.map(lambda s: num(s, r'segmented_(\d+)\.ply')); A_ = auto.set_index('k').n
print('automated numbers', A_.index.min(), '..', A_.index.max(), 'count', len(A_), 'gaps', sorted(set(range(A_.index.max()+1)) - set(A_.index)))
ms2 = hdr('hdr_manual_seg_v2.csv'); ms2['k'] = ms2.name.map(lambda s: num(s, r'segmented_(\d+) - Cloud')); M_ = ms2.set_index('k').n
print('manual_seg_v2 numbers', M_.index.min(), '..', M_.index.max(), 'count', len(M_), 'beyond 161:', sorted(k for k in M_.index if k > 161))
cv2['k'] = cv2.tree.str[5:].astype(int); F_ = cv2.set_index('k').n
for label, fin, off in [('final tree_NNN vs auto NNN (same number)', F_, 0), ('final tree_NNN vs auto NNN-1', F_, -1),
                        ('manual_seg_v2 segmented_N vs auto N', M_, 0)]:
    diff = same = noauto = 0
    for k, n in fin.items():
        a = A_.get(k + off)
        if a is None: noauto += 1
        elif a == n: same += 1
        else: diff += 1
    print(f'{label}: differ={diff} same={same} no_automated_counterpart={noauto}')
# check stable mapping: tree_NNN <-> manual_seg_v2 segmented_(NNN-1)
eq = sum(F_.get(k + 1) == n for k, n in M_.items()); print('manual_seg_v2 N count == final tree_(N+1) count:', eq, 'of', len(M_))
print('sums: auto', A_.sum(), 'manual_seg_v2', M_.sum(), 'final', F_.sum())
